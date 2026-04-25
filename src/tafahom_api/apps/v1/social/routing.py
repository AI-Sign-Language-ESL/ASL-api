from django.urls import re_path
from .consumers import MeetingConsumer

websocket_urlpatterns = [
    re_path(r"ws/meeting/(?P<room_name>\w+)/$", MeetingConsumer.as_asgi()),
]
