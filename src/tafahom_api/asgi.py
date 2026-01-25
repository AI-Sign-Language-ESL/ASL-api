# ruff: noqa: E402
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings")

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator

from tafahom_api.apps.v1.translation.routing import websocket_urlpatterns
from tafahom_api.apps.v1.authentication.middleware import JWTAuthMiddlewareStack


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": OriginValidator(
            JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
            allowed_origins=[
                "https://tafahom.io",
                "https://www.tafahom.io",
            ],
        ),
    }
)
