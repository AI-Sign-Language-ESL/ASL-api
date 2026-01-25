import logging
from urllib.parse import parse_qs
from typing import Any, cast, Union

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, AbstractBaseUser
from django.conf import settings

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

# Set up logging to track connection rejections
logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user(validated_token: Any) -> Union[AbstractBaseUser, AnonymousUser]:
    """
    Fetch the user based on the token payload.
    """
    try:
        user_id_claim = settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id")
        user_id = validated_token.get(user_id_claim)

        if not user_id:
            return AnonymousUser()

        return User.objects.get(id=user_id)
    except (User.DoesNotExist, Exception):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware for Django Channels.
    Resolved ALL Pylance Issues:
    1. scope parameter typed as Any to satisfy _ChannelScope requirement.
    2. token encoded to bytes for get_validated_token.
    3. User/AnonymousUser cast to Any to satisfy scope['user'] TypedDict.
    """

    async def __call__(self, scope: Any, receive: Any, send: Any):
        # 1. Default to Anonymous (Casting to Any satisfies the internal TypedDict)
        scope["user"] = cast(Any, AnonymousUser())
        token_str: str | None = None

        # --------------------------------------------------
        # 2. Try Authorization header
        # --------------------------------------------------
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")

        if auth_header:
            try:
                parts = auth_header.decode().split()
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    token_str = parts[1]
            except Exception:
                pass

        # --------------------------------------------------
        # 3. Try Query string
        # --------------------------------------------------
        if not token_str:
            query_string = scope.get("query_string", b"").decode()
            token_str = parse_qs(query_string).get("token", [None])[0]

        # --------------------------------------------------
        # 4. Validate & Authenticate
        # --------------------------------------------------
        if token_str:
            try:
                jwt_auth = JWTAuthentication()

                # Convert str to bytes to satisfy 'raw_token' parameter type
                raw_token = token_str.encode("utf-8")
                validated_token = jwt_auth.get_validated_token(raw_token)

                # Fetch user
                user = await get_user(validated_token)

                # Assign to scope (Casting to Any solves the UserLazyObject issue)
                scope["user"] = cast(Any, user)

            except (InvalidToken, TokenError) as e:
                logger.warning(f"WebSocket JWT Validation Failed: {e}")
                scope["user"] = cast(Any, AnonymousUser())

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
