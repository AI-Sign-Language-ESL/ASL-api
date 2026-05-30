import secrets
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from tafahom_api.apps.v1.users.models import User


@transaction.atomic
def authenticate_with_google(token: str):
    if not token:
        raise ValueError("Google token is required")

    idinfo = id_token.verify_oauth2_token(
        token,
        requests.Request(),
        settings.GOOGLE_CLIENT_ID,
    )

    if not idinfo.get("email_verified"):
        raise ValueError("Google account email is not verified.")

    google_id = idinfo["sub"]
    email = idinfo["email"]

    # Generate unique username to prevent IntegrityError
    base_username = email.split("@")[0]
    unique_suffix = secrets.token_hex(3)
    username = f"{base_username}_{unique_suffix}"

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": username,
            "google_id": google_id,
            "role": "basic_user",  # ✅ Force basic_user for Google sign-ups
            "first_name": idinfo.get("given_name", ""),
            "last_name": idinfo.get("family_name", ""),
        },
    )

    if not user.is_active:
        raise ValueError("This account has been deactivated.")

    # 🔒 Secure linking (first Google login)
    if not created and user.google_id is None:
        user.google_id = google_id
        user.save(update_fields=["google_id"])

    # ❌ Prevent hijacking
    if not created and user.google_id != google_id:
        raise ValueError("This account is not linked to this Google account")

    # ✅ RESTRICT: Only allow basic_user role
    if user.role != "basic_user":
        raise ValueError("Google Sign-In is only available for Basic Users")

    return user
