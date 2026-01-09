from django.urls import re_path
from .consumers import SignTranslationConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/translation/stream/$",
        SignTranslationConsumer.as_asgi(),
    ),
]
