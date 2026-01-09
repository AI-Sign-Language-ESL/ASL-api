from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from tafahom_api.apps.v1.billing.models import Subscription, SubscriptionPlan

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    if created:
        # 1. Get the "Free" plan from the database
        # You must ensure you have created a Plan in the DB with plan_type='free'
        free_plan = SubscriptionPlan.objects.filter(plan_type="free").first()

        # Fallback: If no free plan exists yet, try to get ANY plan or handle gracefully
        if not free_plan:
            # Optional: Log an error here because this shouldn't happen in production
            return

        # 2. Create the "Wallet" (Subscription) for the new user
        Subscription.objects.create(
            user=instance,
            plan=free_plan,
            status="active",
            billing_period="monthly",
            credits_used=0,
            bonus_credits=0,  # They start with 0 bonus, but 50 from the plan
        )
