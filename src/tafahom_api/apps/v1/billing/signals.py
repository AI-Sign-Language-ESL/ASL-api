import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Subscription, SubscriptionPlan, TokenTransaction

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def create_welcome_subscription(sender, instance, created, **kwargs):
    """
    Signal to automatically grant a free subscription and 30 bonus tokens
    to every newly registered user.
    """
    # Only act on new user creation
    if not created:
        return

    try:
        with transaction.atomic():
            # 1. Check if user already has a subscription to avoid duplicates
            if hasattr(instance, 'subscription'):
                return

            # 2. Fetch the default "free" plan natively
            free_plan = SubscriptionPlan.objects.filter(plan_type="free").first()
            if not free_plan:
                logger.error("Failed to assign welcome bonus: No 'free' SubscriptionPlan found in database.")
                # We do not raise an exception here because it would abort the entire user creation flow.
                return

            # 3. Create the subscription and assign bonus tokens
            subscription = Subscription.objects.create(
                user=instance,
                plan=free_plan,
                status="active",
                bonus_tokens=30,
            )

            # 4. Log the token transaction for billing history
            TokenTransaction.objects.create(
                user=instance,
                subscription=subscription,
                amount=30,
                transaction_type="bonus",
                reason="welcome_bonus"
            )
            logger.info(f"Successfully granted welcome bonus (+30 tokens) to new user: {instance.username}")

    except Exception as e:
        logger.error(f"Error creating subscription for new user {instance.username}: {e}")
