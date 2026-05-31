from rest_framework import serializers
from .models import ChatMessage, ChatConversation


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "role",
            "type",
            "content",
            "audio_url",
            "audio_duration",
            "created_at",
        ]


class ChatMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class VoiceMessageCreateSerializer(serializers.Serializer):
    audio = serializers.FileField(required=True)
    duration = serializers.FloatField(required=False)
    transcription = serializers.CharField(required=False, allow_blank=True)
    history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class QuickActionSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    icon = serializers.CharField()
    action_type = serializers.CharField()
    payload = serializers.CharField(required=False, allow_null=True)


class ActionButtonSerializer(serializers.Serializer):
    label = serializers.CharField()
    action_type = serializers.CharField()
    payload = serializers.CharField(required=False, allow_null=True)


class ActionCardSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    icon = serializers.CharField()
    buttons = ActionButtonSerializer(many=True)


class WelcomeDataSerializer(serializers.Serializer):
    welcome_message = serializers.CharField()
    quick_actions = QuickActionSerializer(many=True)
    action_cards = ActionCardSerializer(many=True)
