"""
streaming/urls.py

URL patterns for the streaming app.
Include this in core/urls.py with:
    path("api/", include("streaming.urls"))
"""

from django.urls import path

from streaming import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", views.refresh_token_view, name="auth-refresh"),
    path("auth/logout/", views.logout_view, name="auth-logout"),
    path("auth/me/", views.me_view, name="auth-me"),

    # ── Rooms ─────────────────────────────────────────────────────────────────
    path("streaming/rooms/", views.RoomListCreateView.as_view(), name="room-list-create"),

    # ── LiveKit Token ─────────────────────────────────────────────────────────
    path("streaming/token/", views.get_livekit_token, name="livekit-token"),
]
