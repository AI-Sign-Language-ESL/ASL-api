from django.apps import apps
from django.db.utils import OperationalError
import logging

logger = logging.getLogger(__name__)


def seed_subscription_plans():
    try:
        SubscriptionPlan = apps.get_model("billing", "SubscriptionPlan")
    except LookupError:
        return

    plans = [
        {"name": "Free Plan", "plan_type": "free", "weekly_tokens_limit": 50, "price": 0.00},
        {"name": "Basic Plan", "plan_type": "basic", "weekly_tokens_limit": 200, "price": 9.99},
        {"name": "GO Plan", "plan_type": "go", "weekly_tokens_limit": 400, "price": 19.99},
        {"name": "Premium Plan", "plan_type": "premium", "weekly_tokens_limit": 600, "price": 29.99},
    ]

    try:
        for plan in plans:
            SubscriptionPlan.objects.update_or_create(
                plan_type=plan["plan_type"],
                defaults=plan
            )
        logger.info("Subscription plans seeded successfully")
    except OperationalError:
        pass