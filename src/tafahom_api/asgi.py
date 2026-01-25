import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings")

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

# Import AFTER Django setup
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from tafahom_api.apps.v1.translation.routing import websocket_urlpatterns  # noqa: E402
from tafahom_api.middleware.jwt_auth import JWTAuthMiddlewareStack  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
