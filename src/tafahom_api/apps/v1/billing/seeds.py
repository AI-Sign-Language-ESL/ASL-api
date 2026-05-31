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
        {"name": "Free Plan", "plan_type": "free", "weekly_tokens_limit": 50, "price": 0.00, "currency": "EGP"},
        {"name": "Basic Plan", "plan_type": "basic", "weekly_tokens_limit": 250, "price": 100.00, "currency": "EGP"},
        {"name": "GO Plan", "plan_type": "go", "weekly_tokens_limit": 500, "price": 175.00, "currency": "EGP"},
        {"name": "Enterprise Plan", "plan_type": "enterprise", "weekly_tokens_limit": 2000, "price": 750.00, "currency": "EGP"},
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