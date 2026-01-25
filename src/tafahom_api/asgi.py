# ruff: noqa: E402
import os

# --------------------------------------------------
# DJANGO MUST BE INITIALIZED FIRST
# --------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings")

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

# --------------------------------------------------
# IMPORT PROJECT CODE *AFTER* DJANGO INIT
# --------------------------------------------------
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from tafahom_api.apps.v1.translation.routing import websocket_urlpatterns
from tafahom_api.apps.v1.authentication.middleware import JWTAuthMiddlewareStack

# --------------------------------------------------
# ASGI APPLICATION
# --------------------------------------------------
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
