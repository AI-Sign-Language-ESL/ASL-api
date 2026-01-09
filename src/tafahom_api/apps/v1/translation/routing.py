from django.urls import re_path
from .consumers import SignTranslationConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/v1/translation/from-sign/$",
        SignTranslationConsumer.as_asgi(),
    ),
]
