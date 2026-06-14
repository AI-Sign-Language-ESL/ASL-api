from .base import *

# Production specific settings overrides
# Note: production is currently mostly handled within base.py using the ENVIRONMENT="PROD" flag.
# These explicit files allow future divergence.
DEBUG = False

# Add any additional production-only settings here
