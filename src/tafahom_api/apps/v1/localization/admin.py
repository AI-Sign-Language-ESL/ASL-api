from django.contrib import admin
from django.utils.html import format_html
from .models import TranslationKey
from .services.translationkey_service import TranslationKeyService
from django.http import JsonResponse


@admin.register(TranslationKey)
class TranslationKeyAdmin(admin.ModelAdmin):
    list_display = [
        "key",
        "context",
        "text_en_preview",
        "text_ar_preview",
        "updated_at",
    ]
    list_filter = ["context", "created_at", "updated_at"]
    search_fields = ["key", "text_en", "text_ar", "description"]
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 50

    fieldsets = (
        ("Key Information", {"fields": ("key", "context", "description")}),
        (
            "Translations",
            {
                "fields": ("text_en", "text_ar"),
                "description": "Enter translations for both languages",
            },
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def text_en_preview(self, obj):
        text = obj.text_en[:50] + "..." if len(obj.text_en) > 50 else obj.text_en
        return format_html('<span style="direction: ltr;">{}</span>', text)

    text_en_preview.short_description = "English Text"

    def text_ar_preview(self, obj):
        text = obj.text_ar[:50] + "..." if len(obj.text_ar) > 50 else obj.text_ar
        return format_html('<span style="direction: rtl;">{}</span>', text)

    text_ar_preview.short_description = "Arabic Text"

    def save_model(self, request, obj, form, change):
        """Clear cache when saving"""
        super().save_model(request, obj, form, change)
        # FIX: Correct method name is clear_translation_cache
        TranslationKeyService.clear_translation_cache(obj.key)

    actions = ["export_as_json", "clear_cache_action"]

    def export_as_json(self, request, queryset):
        data = []
        for obj in queryset:
            data.append(
                {
                    "key": obj.key,
                    "context": obj.context,
                    "text_en": obj.text_en,
                    "text_ar": obj.text_ar,
                }
            )
        return JsonResponse(data, safe=False)

    export_as_json.short_description = "Export selected as JSON"

    def clear_cache_action(self, request, queryset):
        """Clear cache for selected translations"""
        for obj in queryset:
            # FIX: Correct method name is clear_translation_cache
            TranslationKeyService.clear_translation_cache(obj.key)

        self.message_user(request, f"Cache cleared for {queryset.count()} translations")

    clear_cache_action.short_description = "Clear cache for selected"
