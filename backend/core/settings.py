"""
Django settings for core project.
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── SECURITY ────────────────────────────────────────────────────────────────
# Load from .env — never hardcode in production
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ─── APPS ────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # enables logout/token revocation
    "corsheaders",
    # Local
    "streaming",
]

# ─── MIDDLEWARE ───────────────────────────────────────────────────────────────
# CorsMiddleware MUST be first
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Only allow your frontend origin — not all origins
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",  # Vite default dev port
).split(",")
CORS_ALLOW_CREDENTIALS = True  # Required for Authorization header to pass through

# ─── DJANGO REST FRAMEWORK ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    # All endpoints require authentication by default
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",       # Unauthenticated: 20 requests/min (login endpoint)
        "user": "60/min",       # Authenticated: 60 requests/min
        "token_obtain": "5/min", # Custom throttle for token endpoint
    },
}

# ─── JWT (SimpleJWT) ──────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),    # Short-lived access token
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),       # Longer-lived refresh token
    "ROTATE_REFRESH_TOKENS": True,                     # Issue new refresh on each use
    "BLACKLIST_AFTER_ROTATION": True,                  # Revoke old refresh tokens
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),                  # Authorization: Bearer <token>
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "streaming.serializers.CustomTokenObtainPairSerializer",
}

# ─── LIVEKIT ──────────────────────────────────────────────────────────────────
# These are NEVER exposed to the frontend — backend use only
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_TOKEN_TTL_SECONDS = int(os.getenv("LIVEKIT_TOKEN_TTL_SECONDS", 3600))  # 1 hour

# ─── URLS / WSGI ──────────────────────────────────────────────────────────────
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"

# ─── TEMPLATES ────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ─── DATABASE ─────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ─── AUTH / PASSWORD ──────────────────────────────────────────────────────────
AUTH_USER_MODEL = "streaming.User"   # Our custom user with role support

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── I18N ─────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ─── STATIC ───────────────────────────────────────────────────────────────────
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
