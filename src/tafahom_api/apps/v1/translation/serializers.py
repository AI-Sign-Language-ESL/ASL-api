from rest_framework import serializers
from .models import TranslationRequest, SignLanguageConfig


class SignLanguageConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignLanguageConfig
        fields = [
            "code",
            "name_en",
            "name_ar",
            "region",
            "country_code",
            "has_avatar_support",
            "has_video_support",
        ]


class TranslationRequestCreateSerializer(serializers.ModelSerializer):
    source_language = serializers.SlugRelatedField(
        slug_field="code",
        queryset=SignLanguageConfig.objects.all(),
    )

    class Meta:
        model = TranslationRequest
        fields = [
            "id",
            "direction",
            "input_type",
            "output_type",
            "input_text",
            "input_audio",
            "input_video",  # ✅ Required for video uploads
            "source_language",  # ✅ Required for the test
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        direction = data.get("direction")
        input_type = data.get("input_type")

        # Validation 1: Text/Voice -> Sign
        if direction == "to_sign" and input_type not in ("text", "voice"):
            raise serializers.ValidationError(
                "Text/Voice → Sign only accepts text or voice input."
            )

        # Validation 2: Sign -> Text (Video Upload vs WebSocket)
        # We allow HTTP requests for 'from_sign' ONLY if it's a video file (Batch mode).
        # Real-time streaming should still use WebSockets, but we don't block the API here.
        if direction == "from_sign" and input_type != "video":
            raise serializers.ValidationError(
                "Sign translation via HTTP requires a video file input."
            )

        return data


class TranslationRequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslationRequest
        fields = [
            "id",
            "direction",
            "status",
            "created_at",
            "input_type",
            "output_type",
        ]


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
