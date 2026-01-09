from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from tafahom_api.apps.v1.users.models import User


@database_sync_to_async
def get_user(validated_token):
    try:
        user_id = validated_token.get("user_id")
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware for Django Channels (SimpleJWT).
    """

    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()

        token = None

        # --------------------------------------------------
        # 1. Authorization header
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
        # 2. Query string fallback (?token=...)
        # --------------------------------------------------
        if not token:
            query_string = scope.get("query_string", b"").decode()
            token = parse_qs(query_string).get("token", [None])[0]

        # --------------------------------------------------
        # 3. Validate token (if present)
        # --------------------------------------------------
        if token:
            jwt_auth = JWTAuthentication()
            try:
                validated_token = jwt_auth.get_validated_token(token)
                scope["user"] = await get_user(validated_token)
                scope["auth"] = validated_token
            except (InvalidToken, TokenError):
                pass  # keep AnonymousUser

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
