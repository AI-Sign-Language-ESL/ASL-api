

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from tafahom_api.apps.v1.translation.routing import websocket_urlpatterns
from tafahom_api.apps.v1.authentication.middleware import JWTAuthMiddlewareStack

# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.base"
)

# IMPORTANT: initialize Django explicitly
django.setup()


application = ProtocolTypeRouter(
    {
        # HTTP requests
        "http": get_asgi_application(),

        # WebSocket connections
        "websocket": JWTAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    }
)
