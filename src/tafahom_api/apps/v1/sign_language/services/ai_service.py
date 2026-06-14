from django.conf import settings
from .local_provider import LocalModelProvider

# Use LocalModelProvider directly
PROVIDER_CLASS = LocalModelProvider

def predict_sign(video_path: str) -> dict:
    """
    Main entry point for sign language prediction.
    Views must call this function only.
    """
    provider = PROVIDER_CLASS()
    return provider.predict_sign(video_path)
