from django.urls import path

from . import views

app_name = "ai"

urlpatterns = [
    # Welcome
    path("welcome/", views.welcome_view, name="fehm-welcome"),
    # Conversations
    path(
        "conversations/",
        views.ConversationListCreateView.as_view(),
        name="conversation-list-create",
    ),
    path(
        "conversations/<uuid:pk>/",
        views.ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path(
        "conversations/<uuid:pk>/archive/",
        views.ConversationArchiveView.as_view(),
        name="conversation-archive",
    ),
    # Messages
    path(
        "conversations/<uuid:conversation_pk>/messages/",
        views.MessageListView.as_view(),
        name="message-list",
    ),
    path(
        "conversations/<uuid:conversation_pk>/messages/send/",
        views.MessageCreateView.as_view(),
        name="message-send",
    ),
]
