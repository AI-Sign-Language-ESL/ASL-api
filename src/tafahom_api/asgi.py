# ruff: noqa: E402
import os

from django.core.asgi import get_asgi_application

# 🔹 1. Set settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings")

# 🔹 2. Initialize Django ASGI app FIRST
django_asgi_app = get_asgi_application()

# 🔹 3. Import AFTER Django setup
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator

# 🔹 Your custom middleware
from tafahom_api.apps.v1.authentication.middleware import JWTAuthMiddlewareStack

# 🔹 Import ALL websocket routes (important)
from tafahom_api.apps.v1.translation.routing import websocket_urlpatterns as translation_ws
from tafahom_api.apps.v1.meetings.routing import websocket_urlpatterns as meetings_ws

# 🔹 Combine all websocket routes
websocket_urlpatterns = translation_ws + meetings_ws


# ✅ FINAL APPLICATION
application = ProtocolTypeRouter({
    # 🌐 HTTP (Django)
    "http": django_asgi_app,

    # 🔌 WebSocket
    "websocket": OriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
        allowed_origins=[
            # 🌍 Production domains
            "https://tafahom.io",
            "https://www.tafahom.io",

            # 🧪 Local development (IMPORTANT)
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
    ),
})