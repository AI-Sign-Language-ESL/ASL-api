from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from tafahom_api.apps.v1.users.models import User


def authenticate_with_google(token: str):
    if not token:
        raise ValueError("Google token is required")

    idinfo = id_token.verify_oauth2_token(
        token,
        requests.Request(),
        settings.GOOGLE_CLIENT_ID,
    )

    google_id = idinfo["sub"]
    email = idinfo["email"]

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": email.split("@")[0],
            "google_id": google_id,
        },
    )

    # 🔒 Secure linking (first Google login)
    if not created and user.google_id is None:
        user.google_id = google_id
        user.save(update_fields=["google_id"])

    # ❌ Prevent hijacking
    if not created and user.google_id != google_id:
        raise ValueError("This account is not linked to this Google account")

    return user
