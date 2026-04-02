from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from tafahom_api.apps.v1.billing.models import Subscription

class Command(BaseCommand):
    help = "Resets weekly tokens for all active subscriptions if 7 days have passed since their last reset."

    def handle(self, *args, **options):
        now = timezone.now()
        threshold = now - timedelta(days=7)
        
        subscriptions = Subscription.objects.filter(
            status="active",
            last_reset__lte=threshold
        )
        
        count = subscriptions.count()
        
        # We can use the reset_if_needed method but doing it in bulk is more efficient for large datasets.
        # However, since reset_if_needed saves, we'll iterate for now to ensure consistency with the model logic.
        for sub in subscriptions:
            sub.reset_if_needed()
            
        self.stdout.write(self.style.SUCCESS(f"Successfully reset tokens for {count} subscriptions."))
