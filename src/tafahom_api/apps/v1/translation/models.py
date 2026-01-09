from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from tafahom_api.common.enums import (
    TRANSLATION_DIRECTIONS,
    TRANSLATION_STATUS,
    PROCESSING_MODES,
    INPUT_TYPES,
    OUTPUT_TYPES,
    SPOKEN_LANGUAGES,
    SIGN_LANGUAGES,
)


# =========================
# TRANSLATION REQUEST
# =========================


class TranslationRequest(models.Model):
    """
    Represents a single translation request made by a user.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="translation_requests",
    )

    # 🔁 Direction & mode
    direction = models.CharField(
        max_length=20,
        choices=TRANSLATION_DIRECTIONS,
    )
    processing_mode = models.CharField(
        max_length=20,
        choices=PROCESSING_MODES,
        default="standard",
    )

    # 🌍 Languages
    source_language = models.CharField(
        max_length=10,
        choices=SPOKEN_LANGUAGES,
        default="ar-EG",
    )
    target_sign_language = models.CharField(
        max_length=10,
        choices=SIGN_LANGUAGES,
        blank=True,
        null=True,
    )
    output_spoken_language = models.CharField(
        max_length=10,
        choices=SPOKEN_LANGUAGES,
        blank=True,
        null=True,
    )

    # 📥 Input
    input_type = models.CharField(
        max_length=10,
        choices=INPUT_TYPES,
    )
    input_text = models.TextField(blank=True, null=True)
    input_audio = models.FileField(
        upload_to="translation/input/audio/%Y/%m/%d/",
        blank=True,
        null=True,
    )
    input_video = models.FileField(
        upload_to="translation/input/video/%Y/%m/%d/",
        blank=True,
        null=True,
    )

    # 📤 Output
    output_type = models.CharField(
        max_length=10,
        choices=OUTPUT_TYPES,
    )
    output_text = models.TextField(blank=True, null=True)
    output_audio = models.FileField(
        upload_to="translation/output/audio/%Y/%m/%d/",
        blank=True,
        null=True,
    )
    output_video = models.FileField(
        upload_to="translation/output/video/%Y/%m/%d/",
        blank=True,
        null=True,
    )

    # ⚙️ Status
    status = models.CharField(
        max_length=20,
        choices=TRANSLATION_STATUS,
        default="pending",
    )
    error_message = models.TextField(blank=True, null=True)

    # 📊 Metrics
    tokens_used = models.PositiveIntegerField(default=0)
    processing_time = models.FloatField(blank=True, null=True)

    # 🕒 Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "translation_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["direction"]),
            models.Index(fields=["target_sign_language"]),
        ]

    def __str__(self):
        return f"{self.user} | {self.direction} | {self.status}"


# =========================
# SIGN LANGUAGE CONFIG
# =========================


class SignLanguageConfig(models.Model):
    """
    Configuration and capabilities of supported sign languages.
    """

    code = models.CharField(
        max_length=10,
        choices=SIGN_LANGUAGES,
        unique=True,
    )
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    region = models.CharField(max_length=100)
    country_code = models.CharField(max_length=5)

    supported_spoken_languages = models.JSONField(default=list)

    has_avatar_support = models.BooleanField(default=False)
    has_video_support = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        db_table = "sign_language_configs"
        verbose_name = _("Sign Language Configuration")
        verbose_name_plural = _("Sign Language Configurations")

    def __str__(self):
        return f"{self.name_en} ({self.code})"
