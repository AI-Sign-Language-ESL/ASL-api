from django.contrib import admin
from .models import TranslationRequest, SignLanguageConfig


@admin.register(TranslationRequest)
class TranslationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "direction",
        "input_type",
        "output_type",
        "status",
        "created_at",
    )
    list_filter = ("status", "direction", "input_type", "created_at")
    search_fields = ("user__username", "user__email", "input_text")
    readonly_fields = ("created_at", "started_at", "completed_at")


@admin.register(SignLanguageConfig)
class SignLanguageConfigAdmin(admin.ModelAdmin):
    list_display = ("name_en", "code", "region", "is_active")
    list_filter = ("is_active", "has_avatar_support", "has_video_support")
    search_fields = ("name_en", "name_ar", "code", "country_code")
