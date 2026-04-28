from django.core.management.base import BaseCommand
from django.utils import timezone
from tafahom_api.apps.v1.billing.models import Subscription


class Command(BaseCommand):
    help = "Award 50 weekly tokens to all active free plan subscribers"

    def handle(self, *args, **options):
        weekly_tokens = 50
        subscriptions = Subscription.objects.filter(
            status="active",
            plan__plan_type="free"
        ).select_related("plan")

        count = 0
        for sub in subscriptions:
            sub.bonus_tokens += weekly_tokens
            sub.save(update_fields=["bonus_tokens"])
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Awarded {weekly_tokens} weekly tokens to {count} users")
        )