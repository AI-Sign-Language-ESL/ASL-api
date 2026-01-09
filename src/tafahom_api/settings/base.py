from datetime import timedelta
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from ..apps import v1
from .env import (
    BASE_DIR,
    ENVIRONMENT,
    DEBUG,
    SECRET_KEY,
    ALLOWED_HOSTS,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_HOST,
    POSTGRES_PORT,
    REDIS_HOST,
    REDIS_PORT,
    AI_BASE_URL,
    AI_API_KEY,
    AI_TIMEOUT,
    CSRF_TRUSTED_ORIGINS,
    CORS_ALLOWED_ORIGINS,
    SENTRY_DSN,
    WS_MAX_MESSAGES_PER_SECOND,
    WS_MAX_CONNECTION_TIME,
)

# =============================================================================
# CORE
# =============================================================================
SECRET_KEY = SECRET_KEY
DEBUG = ENVIRONMENT != "PROD"
ALLOWED_HOSTS = ALLOWED_HOSTS

ROOT_URLCONF = "tafahom_api.urls"
ASGI_APPLICATION = "tafahom_api.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# SECURITY (PROD SAFE)
# =============================================================================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = ENVIRONMENT == "PROD"
CSRF_COOKIE_SECURE = ENVIRONMENT == "PROD"

SECURE_HSTS_SECONDS = 3600 if ENVIRONMENT == "PROD" else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = ENVIRONMENT == "PROD"
SECURE_HSTS_PRELOAD = ENVIRONMENT == "PROD"

SECURE_SSL_REDIRECT = ENVIRONMENT == "PROD"

# =============================================================================
# APPLICATIONS
# =============================================================================
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    "channels",
    *v1.APPS,
]

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# =============================================================================
# DATABASE
# =============================================================================
DATABASES = {
    "default": (
        {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": POSTGRES_DB,
            "USER": POSTGRES_USER,
            "PASSWORD": POSTGRES_PASSWORD,
            "HOST": POSTGRES_HOST,
            "PORT": POSTGRES_PORT,
        }
        if ENVIRONMENT == "PROD"
        else {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    )
}

# =============================================================================
# TEMPLATES
# =============================================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =============================================================================
# AUTH / JWT
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

SIMPLE_JWT = {
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

AUTH_USER_MODEL = "users.User"

# =============================================================================
# CHANNELS
# =============================================================================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": (
            "channels_redis.core.RedisChannelLayer"
            if ENVIRONMENT == "PROD"
            else "channels.layers.InMemoryChannelLayer"
        ),
        "CONFIG": (
            {
                "hosts": [(REDIS_HOST, REDIS_PORT)],
                "capacity": 300,
                "expiry": 30,
            }
            if ENVIRONMENT == "PROD"
            else {}
        ),
    }
}

# =============================================================================
# WEBSOCKET LIMITS
# =============================================================================
WS_MAX_MESSAGES_PER_SECOND = WS_MAX_MESSAGES_PER_SECOND
WS_MAX_CONNECTION_TIME = WS_MAX_CONNECTION_TIME

# =============================================================================
# STATIC FILES
# =============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# =============================================================================
# CORS / CSRF
# =============================================================================
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS

# =============================================================================
# AI CONFIG
# =============================================================================
AI_BASE_URL = AI_BASE_URL
AI_API_KEY = AI_API_KEY
AI_TIMEOUT = AI_TIMEOUT
PIPELINE_TIMEOUT_SECONDS = AI_TIMEOUT

# =============================================================================
# LOGGING
# =============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "[%(asctime)s] %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "channels": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "translation": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# =============================================================================
# SENTRY
# =============================================================================
if ENVIRONMENT == "PROD" and SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,
    )
