"""
streaming/views.py

Secure API endpoints for authentication and LiveKit token generation.

Endpoint summary:
    POST   /api/auth/login/         → Obtain Django JWT (access + refresh)
    POST   /api/auth/refresh/       → Rotate refresh token
    POST   /api/auth/logout/        → Blacklist refresh token (server-side logout)
    GET    /api/auth/me/            → Current user profile
    GET    /api/streaming/rooms/    → List active rooms (authenticated)
    POST   /api/streaming/rooms/    → Create room (teachers only)
    POST   /api/streaming/token/    → Get LiveKit JWT (authenticated, room must exist)

Security guarantees:
    - All streaming endpoints require a valid Django JWT in Authorization header
    - LiveKit token grants are resolved from the DB role, never from request data
    - LIVEKIT_API_KEY and LIVEKIT_API_SECRET never leave the backend
    - Refresh tokens are blacklisted on logout and on rotation
"""

import logging

from django.conf import settings
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from streaming.models import Room
from streaming.permissions import IsTeacher, IsTeacherOrReadOnly
from streaming.serializers import (
    CustomTokenObtainPairSerializer,
    RoomSerializer,
    TokenRequestSerializer,
    UserSerializer,
)
from streaming.tokens import generate_livekit_token

logger = logging.getLogger(__name__)


# ─── Custom throttle for the LiveKit token endpoint ───────────────────────────

class LiveKitTokenThrottle(UserRateThrottle):
    """
    Tighter rate limit specifically for the LiveKit token endpoint.
    Prevents brute-force room enumeration or token farming.
    """
    scope = "token_obtain"


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Accepts { username, password }.
    Returns { access, refresh, role, username } on success.
    Uses our custom serializer to embed `role` in the JWT payload.

    Rate-limited to 20/min for anonymous users (see settings.py).
    Permission: AllowAny (this is the login gate itself)
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """
    POST /api/auth/refresh/

    Accepts { refresh }.
    Returns a new { access } token (and a new { refresh } if ROTATE_REFRESH_TOKENS=True).
    Old refresh token is blacklisted automatically by SimpleJWT.
    """
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response(
            {"detail": "Refresh token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        token = RefreshToken(refresh_token)
        data = {"access": str(token.access_token)}
        if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
            token.blacklist()
            new_refresh = RefreshToken.for_user(
                token.payload  # type: ignore[arg-type]
            )
            data["refresh"] = str(new_refresh)
        return Response(data, status=status.HTTP_200_OK)
    except Exception as exc:
        logger.warning("Token refresh failed: %s", exc)
        return Response(
            {"detail": "Invalid or expired refresh token."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    POST /api/auth/logout/

    Accepts { refresh }.
    Blacklists the refresh token server-side — the user cannot silently
    obtain new access tokens after this, even if they hold an old refresh token.

    The short-lived access token will expire on its own (60 min by default).
    For immediate access revocation, reduce ACCESS_TOKEN_LIFETIME in settings.
    """
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response(
            {"detail": "Refresh token is required to logout."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        logger.info("User %s logged out — refresh token blacklisted.", request.user.id)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
    except Exception as exc:
        logger.warning("Logout failed for user %s: %s", request.user.id, exc)
        return Response(
            {"detail": "Invalid refresh token."},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    GET /api/auth/me/

    Returns the current authenticated user's profile.
    Useful for the frontend to know the user's role after login.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# ══════════════════════════════════════════════════════════════════════════════
# ROOM ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class RoomListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/streaming/rooms/  → List all active rooms (any authenticated user)
    POST /api/streaming/rooms/  → Create a new room (teachers only)
    """

    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]

    def get_queryset(self):
        return Room.objects.filter(is_active=True).select_related("host")

    def perform_create(self, serializer):
        # The host is always the requesting teacher — never from the request body
        serializer.save(host=self.request.user)
        logger.info("Room '%s' created by teacher %s", serializer.data["name"], self.request.user.id)


# ══════════════════════════════════════════════════════════════════════════════
# LIVEKIT TOKEN ENDPOINT  ←  The core secure endpoint
# ══════════════════════════════════════════════════════════════════════════════

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([LiveKitTokenThrottle])
def get_livekit_token(request):
    """
    POST /api/streaming/token/

    Request body:  { "room": "math-101" }
    Response:      { "livekit_url": "...", "token": "<JWT>", "room": "...", "is_teacher": bool }

    Security guarantees:
      ✓ Requires a valid Django JWT (IsAuthenticated)
      ✓ Rate-limited to 5 requests/min per user
      ✓ Room must exist and be active in our database
      ✓ Role (teacher vs student) is read from the DB — never from this request
      ✓ LIVEKIT_API_KEY / LIVEKIT_API_SECRET stay on the backend
      ✓ The returned LiveKit JWT encodes only the permissions the DB role allows
    """
    serializer = TokenRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    room_name = serializer.validated_data["room"]

    try:
        jwt_string, is_teacher = generate_livekit_token(
            room_name=room_name,
            user=request.user,
        )
    except EnvironmentError as exc:
        # Missing .env config — server misconfiguration, not a client error
        logger.error("LiveKit config error: %s", exc)
        return Response(
            {"detail": "Streaming service is not configured. Contact an administrator."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as exc:
        logger.exception("Unexpected error generating LiveKit token: %s", exc)
        return Response(
            {"detail": "Could not generate streaming token. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "livekit_url": settings.LIVEKIT_URL,
            "token": jwt_string,
            "room": room_name,
            "is_teacher": is_teacher,
        },
        status=status.HTTP_200_OK,
    )
