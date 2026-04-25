from django.urls import path
from .consumers import MeetingConsumer

websocket_urlpatterns = [
    path("ws/meeting/<str:code>/", MeetingConsumer.as_asgi()),
]