import os

# Check for the explicit DJANGO_ENV variable requested for environment routing
django_env = os.environ.get('DJANGO_ENV')

if django_env == 'development':
    from .development import *
elif django_env == 'production':
    from .production import *
else:
    # Safe fallback to the existing behavior. This ensures the current production 
    # deployment (which doesn't set DJANGO_ENV and relies on ENVIRONMENT="PROD" 
    # directly mapped in base.py) continues to work perfectly unchanged.
    from .base import *
