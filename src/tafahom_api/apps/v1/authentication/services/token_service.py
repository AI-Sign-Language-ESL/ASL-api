import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from ..utils.jwt import generate_access_token

User = get_user_model()


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
