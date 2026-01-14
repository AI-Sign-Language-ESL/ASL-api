import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings")

# Initialize Django (must happen before importing project code)
django_asgi_app = get_asgi_application()

# Import project code (Linter will complain, so we silence it)
from tafahom_api.apps.v1.translation.routing import websocket_urlpatterns  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.auth import AuthMiddlewareStack  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
