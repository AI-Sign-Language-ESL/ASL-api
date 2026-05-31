import logging

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Message
from .permissions import IsConversationOwner
from .serializers import (
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from .services import ChatService, ConversationService, FehmResponseService
from .throttles import ChatMessageRateThrottle

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def welcome_view(request):
    response = FehmResponseService.welcome(request.user if request.user.is_authenticated else None)
    return Response(response)


class ConversationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ConversationCreateSerializer
        return ConversationListSerializer

    def get_queryset(self):
        return ConversationService.get_user_conversations(self.request.user)

    def perform_create(self, serializer):
        if not ConversationService.can_create_conversation(self.request.user):
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Maximum conversations reached.")
        ConversationService.create_conversation(
            user=self.request.user,
            title=serializer.validated_data.get("title", ""),
        )


class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsConversationOwner]
    serializer_class = ConversationDetailSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        ConversationService.soft_delete_conversation(instance)


class ConversationArchiveView(APIView):
    permission_classes = [IsAuthenticated, IsConversationOwner]

    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk, user=request.user)
        except Conversation.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ConversationService.archive_conversation(conversation)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsConversationOwner]
    serializer_class = MessageSerializer

    def get_queryset(self):
        return Message.objects.filter(
            conversation_id=self.kwargs["conversation_pk"],
            conversation__user=self.request.user,
        ).order_by("created_at")


class MessageCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatMessageRateThrottle]

    def post(self, request, conversation_pk):
        try:
            conversation = Conversation.objects.get(
                pk=conversation_pk, user=request.user, status="active"
            )
        except Conversation.DoesNotExist:
            return Response(
                {"detail": "Active conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ChatService(conversation)
        try:
            response = service.process_message(serializer.validated_data["content"])
        except Exception as e:
            logger.exception("Fehm chat error")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(response, status=status.HTTP_200_OK)
