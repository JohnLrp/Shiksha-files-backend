"""
streaming/tokens.py

LiveKit JWT token generation — backend-only service.
This module is the ONLY place where LIVEKIT_API_KEY and LIVEKIT_API_SECRET
are used. They are loaded from Django settings (which read from .env),
and are never passed to or from the frontend.

Flow:
    1. User authenticates with Django (gets a Django JWT)
    2. Authenticated view calls `generate_livekit_token(room_name, user)`
    3. This module builds a scoped LiveKit AccessToken
    4. The signed JWT string is returned to the frontend
    5. Frontend uses ONLY that JWT string to connect to LiveKit Cloud
"""

import datetime
import logging

from django.conf import settings
from livekit import api

logger = logging.getLogger(__name__)


def _validate_livekit_config() -> None:
    """Raise clearly if LiveKit credentials are missing from .env"""
    missing = [
        key
        for key in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
        if not getattr(settings, key, None)
    ]
    if missing:
        raise EnvironmentError(
            f"Missing required LiveKit environment variables: {', '.join(missing)}. "
            "Check your .env file."
        )


def generate_livekit_token(room_name: str, user) -> tuple[str, bool]:
    """
    Generate a scoped LiveKit JWT for the given user and room.

    Args:
        room_name: The LiveKit room slug (e.g. "math-101")
        user:      The authenticated Django User instance

    Returns:
        (token_string, is_teacher) — the signed JWT and whether the user
        is a teacher (host), so the frontend knows what UI to render.

    Raises:
        EnvironmentError: if LiveKit credentials are not configured
        Exception:        propagated from livekit-api on signing failure
    """
    _validate_livekit_config()

    # ── Build the access token ────────────────────────────────────────────────
    token = api.AccessToken(
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )

    # Identity is the stable, unique user ID from our DB — never an email or
    # username that could be spoofed across accounts
    token.with_identity(str(user.id))

    # Display name shown in the LiveKit room UI
    token.with_name(user.get_full_name() or user.username)

    # TTL: token expires server-side regardless of frontend behaviour
    token.with_ttl(datetime.timedelta(seconds=settings.LIVEKIT_TOKEN_TTL_SECONDS))

    # ── Role-based grants (resolved from DB, never from request payload) ──────
    is_teacher = user.is_teacher

    grants = api.VideoGrants(
        room_join=True,
        room=room_name,
        # Teachers (hosts): can publish their own camera/mic
        can_publish=is_teacher,
        # Teachers: can publish their screen share data tracks
        can_publish_data=is_teacher,
        # Everyone can receive other participants' streams
        can_subscribe=True,
        # Only teachers can mute others or manage the room
        can_publish_sources=["camera", "microphone", "screen_share"] if is_teacher else [],
        # Room admin grants — teachers only
        room_admin=is_teacher,
        room_record=is_teacher,
    )

    token.with_grants(grants)

    jwt_string = token.to_jwt()

    logger.info(
        "LiveKit token issued | user_id=%s role=%s room=%s ttl=%ss",
        user.id,
        user.role,
        room_name,
        settings.LIVEKIT_TOKEN_TTL_SECONDS,
    )

    return jwt_string, is_teacher
