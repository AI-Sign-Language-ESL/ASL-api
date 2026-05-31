from django.urls import path
from . import views

app_name = "chat"
urlpatterns = [
    path("", views.ChatSendView.as_view(), name="chat-send"),
    path("voice/", views.ChatVoiceView.as_view(), name="chat-voice"),
    path("history/", views.ChatHistoryView.as_view(), name="chat-history"),
    path("welcome/", views.ChatWelcomeView.as_view(), name="chat-welcome"),
]
