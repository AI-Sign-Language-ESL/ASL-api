# ruff: noqa: E402
import os
from django.core.asgi import get_asgi_application

# 1. Initialize Django ASGI application early to ensure models are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings")
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator

# Import your custom routing and middleware
from tafahom_api.apps.v1.translation.routing import websocket_urlpatterns as translation_ws
from tafahom_api.apps.v1.social.routing import websocket_urlpatterns as social_ws
from tafahom_api.apps.v1.authentication.middleware import JWTAuthMiddlewareStack

combined_urlpatterns = translation_ws + social_ws

application = ProtocolTypeRouter(
    {
        # Standard HTTP requests
        "http": django_asgi_app,
        # WebSocket requests flow:
        # OriginValidator -> JWT Middleware -> URL Router
        "websocket": OriginValidator(
            JWTAuthMiddlewareStack(URLRouter(combined_urlpatterns)),
            allowed_origins=[
                "https://tafahom.io",
                "https://www.tafahom.io",
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ],
        ),
    }
)
