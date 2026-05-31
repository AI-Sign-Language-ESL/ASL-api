import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatConversation, ChatMessage
from .serializers import (
    ChatMessageSerializer,
    ChatMessageCreateSerializer,
    VoiceMessageCreateSerializer,
    WelcomeDataSerializer,
)
from .services import get_ai_chat_response

logger = logging.getLogger(__name__)

WELCOME_DATA = {
    "welcome_message": "Hello! I'm Tafahom AI assistant. How can I help you with sign language today?",
    "quick_actions": [
        {"id": "translate", "title": "Translate Text", "icon": "translate", "action_type": "navigate", "payload": "/text-to-sign"},
        {"id": "sign-to-text", "title": "Sign to Text", "icon": "hand_gesture", "action_type": "navigate", "payload": "/sign-to-text"},
        {"id": "info", "title": "Help & Info", "icon": "info", "action_type": "send_message", "payload": "What features do you have?"},
        {"id": "premium", "title": "Upgrade Plan", "icon": "workspace_premium", "action_type": "navigate", "payload": "/subscription"},
    ],
    "action_cards": [
        {
            "id": "text-to-sign",
            "title": "Text to Sign",
            "description": "Convert your text into sign language animations instantly",
            "icon": "translate",
            "buttons": [
                {"label": "Try Now", "action_type": "navigate", "payload": "/text-to-sign"},
            ],
        },
        {
            "id": "sign-to-text",
            "title": "Sign to Text",
            "description": "Upload a video of sign language and get text translation",
            "icon": "hand_gesture",
            "buttons": [
                {"label": "Try Now", "action_type": "navigate", "payload": "/sign-to-text"},
            ],
        },
        {
            "id": "upgrade",
            "title": "Unlock Premium",
            "description": "Get unlimited translations, priority processing, and more",
            "icon": "workspace_premium",
            "buttons": [
                {"label": "Upgrade", "action_type": "navigate", "payload": "/subscription"},
                {"label": "Learn More", "action_type": "send_message", "payload": "Tell me about premium plans"},
            ],
        },
    ],
}


class ChatSendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        message = serializer.validated_data["message"]
        history_data = serializer.validated_data.get("history", [])

        conversation, _ = ChatConversation.objects.get_or_create(
            user=request.user,
            defaults={"title": message[:50]},
        )

        ChatMessage.objects.create(
            conversation=conversation,
            role="user",
            type="text",
            content=message,
        )

        ai_response = get_ai_chat_response(message, history_data)

        assistant_msg = ChatMessage.objects.create(
            conversation=conversation,
            role="assistant",
            type="text",
            content=ai_response,
        )

        return Response(
            ChatMessageSerializer(assistant_msg).data,
            status=status.HTTP_201_CREATED,
        )


class ChatVoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VoiceMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        audio_file = serializer.validated_data["audio"]
        duration = serializer.validated_data.get("duration", 0.0)
        transcription = serializer.validated_data.get("transcription", "")
        history_data = serializer.validated_data.get("history", [])

        conversation, _ = ChatConversation.objects.get_or_create(
            user=request.user,
            defaults={"title": f"Voice message - {audio_file.name}"},
        )

        user_msg = ChatMessage.objects.create(
            conversation=conversation,
            role="user",
            type="voice",
            content=transcription or "Voice message",
            audio_duration=duration,
        )

        text_content = transcription or "Voice message"
        ai_response = get_ai_chat_response(text_content, history_data)

        assistant_msg = ChatMessage.objects.create(
            conversation=conversation,
            role="assistant",
            type="text",
            content=ai_response,
        )

        return Response(
            ChatMessageSerializer(assistant_msg).data,
            status=status.HTTP_201_CREATED,
        )


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversation = ChatConversation.objects.filter(
            user=request.user
        ).first()

        if not conversation:
            return Response([], status=status.HTTP_200_OK)

        messages = conversation.messages.all()
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        ChatConversation.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatWelcomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = WelcomeDataSerializer(data=WELCOME_DATA)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
