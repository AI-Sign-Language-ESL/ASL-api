"""
DEPRECATED: Use simplejwt's TokenRefreshView instead.

This module manually decodes refresh tokens WITHOUT checking the
token blacklist. It exists only as legacy code and MUST NOT be
wired to any URL endpoint. Use /authentication/token/refresh/
(or /auth/refresh/) which properly validates via
rest_framework_simplejwt including blacklist enforcement.
"""

import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from ..utils.jwt import generate_access_token
from tafahom_api.apps.v1.users.models import User


def refresh_access_token(refresh_token):
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Refresh token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise AuthenticationFailed("Invalid token type")

    user = User.objects.filter(id=payload["user_id"]).first()
    if not user or not user.is_active:
        raise AuthenticationFailed("User not found")

    return generate_access_token(user)
