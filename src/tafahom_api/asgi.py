# ruff: noqa: E402
import os
from django.core.asgi import get_asgi_application

# 1. Initialize Django ASGI application early to ensure models are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings")
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator

# Import your custom routing and middleware
from tafahom_api.apps.v1.translation.routing import websocket_urlpatterns
from tafahom_api.apps.v1.authentication.middleware import JWTAuthMiddlewareStack

application = ProtocolTypeRouter(
    {
        # Standard HTTP requests
        "http": django_asgi_app,
        # WebSocket requests flow:
        # OriginValidator -> JWT Middleware -> URL Router
        "websocket": OriginValidator(
            JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
            allowed_origins=[
                "https://tafahom.io",
                "https://www.tafahom.io",
                # Note: Add "http://localhost:port" here if testing locally without Nginx
            ],
        ),
    }
)
