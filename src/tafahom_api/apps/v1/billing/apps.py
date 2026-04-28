from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tafahom_api.apps.v1.billing"
    label = "billing"

    def ready(self):
        import tafahom_api.apps.v1.billing.signals
        
        from django.db.models.signals import post_migrate
        from tafahom_api.apps.v1.billing.seeds import seed_subscription_plans
        
        post_migrate.connect(lambda sender, **kwargs: seed_subscription_plans(), sender=self)
    