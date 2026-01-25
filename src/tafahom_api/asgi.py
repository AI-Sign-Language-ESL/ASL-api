import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
from tafahom_api.apps.v1.translation.routing import websocket_urlpatterns  # noqa: E402
from tafahom_api.apps.v1.authentication.middleware import (
    JWTAuthMiddlewareStack,
)  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings")

django_asgi_app = get_asgi_application()


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
