from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from urllib.parse import parse_qs

User = get_user_model()


@database_sync_to_async
def get_user(validated_token):
    """
    Fetch user instance from validated SimpleJWT token.
    """
    try:
        user_id = validated_token.get("user_id")
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Production-grade JWT authentication middleware for WebSockets.
    Uses SimpleJWT (same as REST APIs).
    """

    async def __call__(self, scope, receive, send):
        token = None

        # --------------------------------------------------
        # 1. Try Authorization header
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
        # 2. Fallback to query string (?token=...)
        # --------------------------------------------------
        if not token:
            query_string = scope.get("query_string", b"").decode()
            query_params = parse_qs(query_string)
            token = query_params.get("token", [None])[0]

        # --------------------------------------------------
        # 3. Reject unauthenticated connections
        # --------------------------------------------------
        if not token:
            await send(
                {
                    "type": "websocket.close",
                    "code": 4401,  # Unauthorized
                }
            )
            return

        # --------------------------------------------------
        # 4. Validate token using SimpleJWT
        # --------------------------------------------------
        jwt_auth = JWTAuthentication()

        try:
            validated_token = jwt_auth.get_validated_token(token)
            scope["user"] = await get_user(validated_token)
            scope["auth"] = validated_token
        except (InvalidToken, TokenError):
            await send(
                {
                    "type": "websocket.close",
                    "code": 4401,
                }
            )
            return

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
