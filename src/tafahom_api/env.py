import os
from pathlib import Path
from dotenv import load_dotenv

# ==================================================
# BASE DIR
# ==================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ==================================================
# ENVIRONMENT
# ==================================================
# Allowed values: DEV | PROD
ENVIRONMENT = os.getenv("ENVIRONMENT", "DEV")

# ==================================================
# LOAD ENV FILE
# ==================================================
# You still keep different .env files,
# but ONE settings file (base.py)
if ENVIRONMENT == "PROD":
    load_dotenv(BASE_DIR / ".env.prod")
else:
    load_dotenv(BASE_DIR / ".env.dev")

# ==================================================
# CORE DJANGO SETTINGS
# ==================================================
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-dev-key")
DEBUG = ENVIRONMENT != "PROD"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# ==================================================
# DATABASE
# ==================================================
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# ==================================================
# REDIS (CHANNELS)
# ==================================================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


# ==================================================
# SECURITY
# ==================================================
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")

# ==================================================
# OPTIONAL FLAGS (SAFE DEFAULTS)
# ==================================================
USE_REDIS = ENVIRONMENT == "PROD"
