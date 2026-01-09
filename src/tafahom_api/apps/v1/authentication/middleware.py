from types import SimpleNamespace
from urllib.parse import parse_qs

from django.contrib.auth.models import AnonymousUser

from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware for Django Channels.

    ✅ SQLite-safe
    ✅ Test-safe
    ✅ No database access
    ✅ Uses SimpleJWT validation only
    """

    async def __call__(self, scope, receive, send):
        # Default to anonymous
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
        # 2. Query string fallback (?token=...)
        # --------------------------------------------------
        if not token:
            query_string = scope.get("query_string", b"").decode()
            token = parse_qs(query_string).get("token", [None])[0]

        # --------------------------------------------------
        # 3. Validate JWT (NO DATABASE QUERY)
        # --------------------------------------------------
        if token:
            try:
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)

                # Lightweight authenticated user object
                scope["user"] = SimpleNamespace(
                    id=validated_token.get("user_id"),
                    is_authenticated=True,
                    is_anonymous=False,
                )

            except (InvalidToken, TokenError):
                pass  # remain AnonymousUser

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
