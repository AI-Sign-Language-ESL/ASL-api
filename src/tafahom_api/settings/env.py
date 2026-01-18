import os
from pathlib import Path
from dotenv import load_dotenv

# =============================================================================
# BASE DIR
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# ENVIRONMENT
# =============================================================================
# Allowed values: DEV | PROD
ENVIRONMENT = os.getenv("ENVIRONMENT", "DEV").upper()

if ENVIRONMENT not in ("DEV", "PROD"):
    raise RuntimeError("ENVIRONMENT must be DEV or PROD")

# =============================================================================
# LOAD ENV FILE
# =============================================================================
env_file = ".env.prod" if ENVIRONMENT == "PROD" else ".env.dev"
load_dotenv(BASE_DIR / env_file)

# =============================================================================
# CORE SECURITY
# =============================================================================
SECRET_KEY = os.getenv("SECRET_KEY")

if ENVIRONMENT == "PROD" and not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is required in PROD")

# Allow pytest / DEV
if ENVIRONMENT != "PROD" and not SECRET_KEY:
    SECRET_KEY = "test-secret-key"

DEBUG = ENVIRONMENT != "PROD"

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()
]

if ENVIRONMENT == "PROD" and not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS must be set in PROD")

# =============================================================================
# DATABASE (PostgreSQL)
# =============================================================================
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

if ENVIRONMENT == "PROD":
    for name, value in {
        "POSTGRES_DB": POSTGRES_DB,
        "POSTGRES_USER": POSTGRES_USER,
        "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
        "POSTGRES_HOST": POSTGRES_HOST,
    }.items():
        if not value:
            raise RuntimeError(f"{name} is required in PROD")

# =============================================================================
# REDIS (CHANNELS)
# =============================================================================
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# =============================================================================
# AI SERVICES (ENV-DRIVEN, NO HARDCODE)
# =============================================================================
AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", 30))

AI_STT_BASE_URL = os.getenv("AI_STT_BASE_URL")
AI_TTS_BASE_URL = os.getenv("AI_TTS_BASE_URL")
AI_GLOSS_TO_TEXT_BASE_URL = os.getenv("AI_GLOSS_TO_TEXT_BASE_URL")
AI_TEXT_TO_GLOSS_BASE_URL = os.getenv("AI_TEXT_TO_GLOSS_BASE_URL")
AI_CV_BASE_URL = os.getenv("AI_CV_BASE_URL")

if ENVIRONMENT == "PROD":
    for name, value in {
        "AI_STT_BASE_URL": AI_STT_BASE_URL,
        "AI_TTS_BASE_URL": AI_TTS_BASE_URL,
        "AI_GLOSS_TO_TEXT_BASE_URL": AI_GLOSS_TO_TEXT_BASE_URL,
        "AI_TEXT_TO_GLOSS_BASE_URL": AI_TEXT_TO_GLOSS_BASE_URL,
        "AI_CV_BASE_URL": AI_CV_BASE_URL,
    }.items():
        if not value:
            raise RuntimeError(f"{name} is required in PROD")

# =============================================================================
# WEBSOCKET LIMITS
# =============================================================================
WS_MAX_MESSAGES_PER_SECOND = int(os.getenv("WS_MAX_MESSAGES_PER_SECOND", 30))

WS_MAX_CONNECTION_TIME = int(os.getenv("WS_MAX_CONNECTION_TIME", 60 * 15))

# =============================================================================
# CORS / CSRF
# =============================================================================
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]

# =============================================================================
# OPTIONAL
# =============================================================================
SENTRY_DSN = os.getenv("SENTRY_DSN")
# =============================================================================
# GOOGLE AUTH
# =============================================================================
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

if ENVIRONMENT == "PROD" and not GOOGLE_CLIENT_ID:
    raise RuntimeError("GOOGLE_CLIENT_ID is required in PROD")
