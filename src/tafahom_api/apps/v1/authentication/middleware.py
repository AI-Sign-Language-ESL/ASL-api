from urllib.parse import parse_qs

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


@database_sync_to_async
def get_user(validated_token):
    """
    Fetch the real Django user.
    This is required for Channels to treat the user as authenticated.
    """
    try:
        return User.objects.get(id=validated_token["user_id"])
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware for Django Channels.

    ✅ Supports Authorization header
    ✅ Supports ?token= query param
    ✅ Proper Django User object
    """

    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()
        token = None

        # --------------------------------------------------
        # 1. Authorization header (Bearer <token>)
        # --------------------------------------------------
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")

        if auth_header:
            try:
                prefix, token = auth_header.decode().split()
                if prefix.lower() != "bearer":
                    token = None
            except ValueError:
                token = None

        # --------------------------------------------------
        # 2. Query string (?token=...)
        # --------------------------------------------------
        if not token:
            query_string = scope.get("query_string", b"").decode()
            token = parse_qs(query_string).get("token", [None])[0]

        # --------------------------------------------------
        # 3. Validate JWT & attach real user
        # --------------------------------------------------
        if token:
            try:
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)
                scope["user"] = await get_user(validated_token)

            except (InvalidToken, TokenError):
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
