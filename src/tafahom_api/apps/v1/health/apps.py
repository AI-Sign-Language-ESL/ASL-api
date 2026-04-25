default_app_config = "tafahom_api.apps.v1.health.apps.HealthConfig"

from django.apps import AppConfig


class HealthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tafahom_api.apps.v1.health"
    verbose_name = "Health"