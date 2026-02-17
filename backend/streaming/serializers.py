"""
streaming/serializers.py

Serializers for auth and streaming endpoints.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from streaming.models import Room, User


# ─── AUTH ─────────────────────────────────────────────────────────────────────

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the default SimpleJWT login serializer to embed the user's
    role into the JWT *payload* (not a secret — just a convenience claim).

    IMPORTANT: The frontend should NEVER use this claim to unlock features.
    The backend always re-reads the role from the database on every request.
    This claim is only for UI hints (e.g. showing/hiding a "Go Live" button).
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims — readable in the JWT payload
        token["role"] = user.role
        token["username"] = user.username
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Also return role in the login response body for convenience
        data["role"] = self.user.role
        data["username"] = self.user.username
        return data


# ─── ROOM ─────────────────────────────────────────────────────────────────────

class RoomSerializer(serializers.ModelSerializer):
    host_username = serializers.CharField(source="host.username", read_only=True)

    class Meta:
        model = Room
        fields = ["id", "name", "display_name", "host_username", "is_active", "created_at"]
        read_only_fields = ["id", "host_username", "created_at"]


# ─── TOKEN REQUEST ────────────────────────────────────────────────────────────

class TokenRequestSerializer(serializers.Serializer):
    """Validates the body of POST /api/streaming/token/"""

    room = serializers.SlugField(
        max_length=100,
        help_text="The slug name of the LiveKit room to join (e.g. 'math-101')",
    )

    def validate_room(self, value: str) -> str:
        """
        Optionally: ensure the room exists in our database.
        Comment out the raise if you want to allow ad-hoc room names.
        """
        if not Room.objects.filter(name=value, is_active=True).exists():
            raise serializers.ValidationError(
                f"Room '{value}' does not exist or is not currently active."
            )
        return value


class TokenResponseSerializer(serializers.Serializer):
    """Documents the shape of the token endpoint response."""

    livekit_url = serializers.URLField()
    token = serializers.CharField()
    room = serializers.CharField()
    is_teacher = serializers.BooleanField()


# ─── USER (for admin / profile use) ───────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "is_teacher", "is_student"]
        read_only_fields = ["id", "is_teacher", "is_student"]
