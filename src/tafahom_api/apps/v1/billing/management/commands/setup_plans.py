from django.core.management.base import BaseCommand
from tafahom_api.apps.v1.billing.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Creates default subscription plans"

    def handle(self, *args, **kwargs):
        # Create Free Plan
        plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type="free",
            defaults={
                "name": "Free Tier",
                "credits_per_month": 50,
                "price": 0.00,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS("✅ Free plan created successfully"))
        else:
            self.stdout.write(self.style.WARNING("ℹ️ Free plan already exists"))
