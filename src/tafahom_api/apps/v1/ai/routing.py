from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/fehm/(?P<conversation_id>[0-9a-f-]+)/$",
        consumers.FehmChatConsumer.as_asgi(),
        name="fehm-chat-ws",
    ),
]
