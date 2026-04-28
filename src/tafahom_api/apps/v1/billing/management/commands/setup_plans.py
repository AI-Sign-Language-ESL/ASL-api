from django.core.management.base import BaseCommand
from tafahom_api.apps.v1.billing.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Creates default subscription plans"

    def handle(self, *args, **kwargs):
        plans = [
            {"name": "Free Plan", "plan_type": "free", "weekly_tokens_limit": 50, "price": 0.00},
            {"name": "Basic Plan", "plan_type": "basic", "weekly_tokens_limit": 200, "price": 9.99},
            {"name": "GO Plan", "plan_type": "go", "weekly_tokens_limit": 400, "price": 19.99},
            {"name": "Premium Plan", "plan_type": "premium", "weekly_tokens_limit": 600, "price": 29.99},
        ]
        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                plan_type=plan_data["plan_type"],
                defaults=plan_data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ {plan_data['name']} created successfully"))
            else:
                self.stdout.write(self.style.WARNING(f"ℹ️ {plan_data['name']} already exists"))

        if created:
            self.stdout.write(self.style.SUCCESS("✅ Free plan created successfully"))
        else:
            self.stdout.write(self.style.WARNING("ℹ️ Free plan already exists"))
