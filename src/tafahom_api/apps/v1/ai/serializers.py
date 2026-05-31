from rest_framework import serializers
from .models import Conversation, Message


class ConversationListSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "status",
            "message_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["title"]


class ConversationDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "status",
            "meta_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "role",
            "content",
            "tokens_used",
            "model_used",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "conversation",
            "tokens_used",
            "model_used",
            "created_at",
        ]


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(allow_blank=False, trim_whitespace=True)
