from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tafahom_api.apps.v1.billing"
    label = "billing"

    def ready(self):
        import tafahom_api.apps.v1.billing.signals