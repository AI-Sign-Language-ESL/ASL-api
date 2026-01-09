from rest_framework import serializers
from .models import TranslationRequest


class TranslationRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslationRequest
        fields = [
            "id",
            "direction",
            "input_type",
            "output_type",
            "input_text",
            "input_audio",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        direction = data.get("direction")
        input_type = data.get("input_type")

        if direction == "to_sign" and input_type not in ("text", "voice"):
            raise serializers.ValidationError(
                "Text/Voice → Sign only accepts text or voice input."
            )

        if direction == "from_sign":
            raise serializers.ValidationError(
                "Sign → Text must use WebSocket, not HTTP."
            )

        return data


class TranslationRequestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslationRequest
        fields = [
            "id",
            "status",
            "output_text",
            "output_audio",
            "output_video",
            "error_message",
        ]
