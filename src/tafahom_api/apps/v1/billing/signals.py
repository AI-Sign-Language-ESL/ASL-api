import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Subscription, SubscriptionPlan

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def create_welcome_subscription(sender, instance, created, **kwargs):
    """
    Signal to automatically grant a free subscription to every newly registered user.
    Users start with the plan's 50 weekly tokens — no bonus.
    """
    if not created:
        return

    try:
        with transaction.atomic():
            if hasattr(instance, 'subscription'):
                return

            free_plan = SubscriptionPlan.objects.filter(plan_type="free").first()
            if not free_plan:
                logger.error("Failed to assign free plan: No 'free' SubscriptionPlan found in database.")
                return

            Subscription.objects.create(
                user=instance,
                plan=free_plan,
                status="active",
                bonus_tokens=0,
            )
            logger.info(f"Free subscription created for new user: {instance.username}")

    except Exception as e:
        logger.error(f"Error creating subscription for new user {instance.username}: {e}")
