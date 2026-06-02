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
    CSRF_TRUSTED_ORIGINS,
    CORS_ALLOWED_ORIGINS,
    SENTRY_DSN,
    WS_MAX_MESSAGES_PER_SECOND,
    WS_MAX_CONNECTION_TIME,
    AI_TIMEOUT,
    AI_BASE_URL,
    AI_STT_BASE_URL,
    AI_TTS_BASE_URL,
    AI_GLOSS_TO_TEXT_BASE_URL,
    AI_TEXT_TO_GLOSS_BASE_URL,
    AI_CV_BASE_URL,
    CV_MODEL_WS_URL,
    GOOGLE_CLIENT_ID,
    UNITY_SIGN_MATCHER_URL,
    EMAIL_HOST as ENV_EMAIL_HOST,
    EMAIL_PORT as ENV_EMAIL_PORT,
    EMAIL_HOST_USER,
    EMAIL_HOST_PASSWORD,
    EMAIL_USE_TLS,
    DEFAULT_FROM_EMAIL as ENV_DEFAULT_FROM_EMAIL,
    FEHM_MAX_CONVERSATIONS_PER_USER,
    FEHM_MESSAGE_RATE_LIMIT,
)

# =============================================================================
# CORE
# =============================================================================
SECRET_KEY = SECRET_KEY
DEBUG = DEBUG
ALLOWED_HOSTS = ALLOWED_HOSTS

ROOT_URLCONF = "tafahom_api.urls"
ASGI_APPLICATION = "tafahom_api.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
GOOGLE_CLIENT_ID = GOOGLE_CLIENT_ID

# =============================================================================
# SECURITY HEADERS (additional)
# =============================================================================
SECURE_CONTENT_TYPE_NOSNIFF = ENVIRONMENT == "PROD"
SECURE_BROWSER_XSS_FILTER = True
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Rate limiting
RATELIMIT_USE_CACHE = "default" if ENVIRONMENT == "PROD" else "locmem"
RATELIMIT_ENABLED = ENVIRONMENT == "PROD"

# =============================================================================
# SECURITY
# =============================================================================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = ENVIRONMENT == "PROD"
CSRF_COOKIE_SECURE = ENVIRONMENT == "PROD"

SECURE_HSTS_SECONDS = 3600 if ENVIRONMENT == "PROD" else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = ENVIRONMENT == "PROD"
SECURE_HSTS_PRELOAD = ENVIRONMENT == "PROD"
SECURE_SSL_REDIRECT = ENVIRONMENT == "PROD"
CHANNELS_ALLOWED_HOSTS = ALLOWED_HOSTS

# =============================================================================
# CACHING
# =============================================================================
CACHES = {
    "default": (
        {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
            "KEY_PREFIX": "tafahom",
            "TIMEOUT": 300,
        }
        if ENVIRONMENT == "PROD"
        else {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    )
}
CACHE_TIMEOUT = 86400  # 24 hours
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
    "rest_framework_simplejwt.token_blacklist",
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
SIMPLE_JWT = {
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
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
# HYBRID TRANSLATION PIPELINE
# =============================================================================
AI_TIMEOUT_SECONDS = 1.5

# =============================================================================
# SIGN TRANSLATION PIPELINE (CV + NLP)
# =============================================================================
CV_MODEL_WS_URL = CV_MODEL_WS_URL
CV_WS_TIMEOUT = 30
NLP_REQUEST_TIMEOUT = 30
MAX_CV_RETRIES = 3
NLP_RETRIES = 3


# =============================================================================
# STATIC FILES
# =============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = "/app/staticfiles"

# =============================================================================
# MEDIA FILES
# =============================================================================
MEDIA_URL = "/media/"
MEDIA_ROOT = "/app/media"


# =============================================================================
# CORS / CSRF
# =============================================================================
# SECURITY: Never allow all origins in production — use explicit whitelist via CORS_ALLOWED_ORIGINS.
# CORS_ALLOW_ALL_ORIGINS = True would override CORS_ALLOWED_ORIGINS and allow any domain.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ["X-Total-Count", "X-Page-Count"]
CORS_PREFLOW_MAX_AGE = 3600
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS

# =============================================================================
# DRF ENHANCED SETTINGS
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/minute",
        "user": "200/minute",
        "ws_msg": WS_MAX_MESSAGES_PER_SECOND,
        # Auth-specific strict limits (prevent brute-force / OTP guessing)
        "login": "5/minute",
        "password_reset": "3/minute",
        "verify_email": "10/minute",
        # Fehm chatbot
        "chat_message": FEHM_MESSAGE_RATE_LIMIT,
    },
    "EXCEPTION_HANDLER": "tafahom_api.common.exception_handler.custom_exception_handler",
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

# =============================================================================
# EMAILS
# =============================================================================
if ENV_EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = ENV_EMAIL_HOST
    EMAIL_PORT = ENV_EMAIL_PORT
    EMAIL_HOST_USER = EMAIL_HOST_USER
    EMAIL_HOST_PASSWORD = EMAIL_HOST_PASSWORD
    EMAIL_USE_TLS = EMAIL_USE_TLS
    DEFAULT_FROM_EMAIL = ENV_DEFAULT_FROM_EMAIL
else:
    # Print emails to the console in development
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "webmaster@localhost"

# =============================================================================
# LOGGING  — show INFO+ from our own code in Docker/console
# =============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname:<8} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        # Our app code → INFO so all logger.info() calls appear
        "tafahom_api": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # httpx / httpcore (AI HTTP calls) → INFO so we see request logs
        "httpx": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =============================================================================
# FEHM (CHATBOT) CONFIG
# =============================================================================
FEHM_MAX_CONVERSATIONS_PER_USER = FEHM_MAX_CONVERSATIONS_PER_USER
FEHM_MESSAGE_RATE_LIMIT = FEHM_MESSAGE_RATE_LIMIT
