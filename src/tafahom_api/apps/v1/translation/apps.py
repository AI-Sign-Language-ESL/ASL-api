from django.apps import AppConfig


class TranslationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tafahom_api.apps.v1.translation"
    label = "translation"  # ✅ IMPORTANT
