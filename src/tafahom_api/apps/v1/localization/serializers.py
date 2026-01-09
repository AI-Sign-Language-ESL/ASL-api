from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import TranslationKey
from tafahom_api.common.enums import LANGUAGE_CODES, TEXT_DIRECTIONS


# ---------------- LANGUAGES ----------------


class LanguageSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=LANGUAGE_CODES)
    name = serializers.CharField(max_length=50)
    native_name = serializers.CharField(max_length=50)
    direction = serializers.ChoiceField(choices=TEXT_DIRECTIONS)
    flag = serializers.CharField(max_length=10, required=False)
    is_default = serializers.BooleanField(default=False)


class LanguageListResponseSerializer(serializers.Serializer):
    languages = LanguageSerializer(many=True)
    current_language = serializers.ChoiceField(choices=LANGUAGE_CODES)


class SetLanguageSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=LANGUAGE_CODES)


class CurrentLanguageResponseSerializer(serializers.Serializer):
    language_code = serializers.ChoiceField(choices=LANGUAGE_CODES)
    direction = serializers.ChoiceField(choices=TEXT_DIRECTIONS)
    is_rtl = serializers.BooleanField()


# ---------------- TRANSLATIONS ----------------


class TranslationResponseSerializer(serializers.Serializer):
    translations = serializers.DictField(
        child=serializers.CharField(),
        help_text=_("Dictionary of translation keys and values."),
    )
    language = serializers.ChoiceField(choices=LANGUAGE_CODES)


class BulkTranslationKeySerializer(serializers.Serializer):
    keys = serializers.ListField(
        child=serializers.CharField(max_length=200),
        help_text=_("List of translation keys."),
    )
    language = serializers.ChoiceField(
        choices=LANGUAGE_CODES,
        default="en",
    )

    def validate_keys(self, value):
        if not value:
            raise serializers.ValidationError(_("Keys list cannot be empty."))
        if len(value) > 100:
            raise serializers.ValidationError(_("Maximum 100 keys per request."))
        return value


# ---------------- ADMIN KEYS ----------------


class TranslationKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslationKey
        fields = [
            "id",
            "key",
            "description",
            "context",
            "text_en",
            "text_ar",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_key(self, value):
        value = value.strip().lower()
        if not value.replace("_", "").isalnum():
            raise serializers.ValidationError(
                _("Key must contain only letters, numbers, and underscores.")
            )
        return value


class TranslationKeyListSerializer(serializers.ModelSerializer):
    preview_en = serializers.SerializerMethodField()
    preview_ar = serializers.SerializerMethodField()

    class Meta:
        model = TranslationKey
        fields = [
            "id",
            "key",
            "context",
            "preview_en",
            "preview_ar",
            "updated_at",
        ]

    def get_preview_en(self, obj) -> str:
        return obj.text_en[:50] + "..." if len(obj.text_en) > 50 else obj.text_en

    def get_preview_ar(self, obj) -> str:
        return obj.text_ar[:50] + "..." if len(obj.text_ar) > 50 else obj.text_ar
