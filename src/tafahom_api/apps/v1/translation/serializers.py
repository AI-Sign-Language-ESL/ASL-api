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
            "input_video",
            "source_language",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        direction = data.get("direction")
        input_type = data.get("input_type")

        if direction == "to_sign" and input_type not in ("text", "voice"):
            raise serializers.ValidationError(
                "Text/Voice → Sign only accepts text or voice input."
            )

        if direction == "from_sign" and input_type != "video":
            raise serializers.ValidationError(
                "Sign → Text via HTTP requires video input."
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


# 🔥 DEDICATED TEXT → SIGN SERIALIZER


class TextToSignSerializer(serializers.Serializer):
    text = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
