import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tafahom_api.settings.base")
django.setup()

from tafahom_api.apps.v1.billing.models import SubscriptionPlan

plans = [
    {
        "name": "Free Plan",
        "plan_type": "free",
        "weekly_tokens_limit": 50,
        "price": 0.00,
        "currency": "EGP",
    },
    {
        "name": "Basic Plan",
        "plan_type": "basic",
        "weekly_tokens_limit": 250,
        "price": 100.00,
        "currency": "EGP",
    },
    {
        "name": "GO Plan",
        "plan_type": "go",
        "weekly_tokens_limit": 500,
        "price": 175.00,
        "currency": "EGP",
    },
    {
        "name": "Enterprise Plan",
        "plan_type": "enterprise",
        "weekly_tokens_limit": 2000,
        "price": 750.00,
        "currency": "EGP",
    }
]

for plan in plans:
    SubscriptionPlan.objects.update_or_create(
        plan_type=plan["plan_type"],
        defaults=plan
    )

print("Created subscription plans.")
