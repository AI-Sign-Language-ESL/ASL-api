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
    },
    {
        "name": "Basic Plan",
        "plan_type": "basic",
        "weekly_tokens_limit": 200,
        "price": 9.99,
    },
    {
        "name": "GO Plan",
        "plan_type": "go",
        "weekly_tokens_limit": 400,
        "price": 19.99,
    },
    {
        "name": "Premium Plan",
        "plan_type": "premium",
        "weekly_tokens_limit": 600,
        "price": 29.99,
    }
]

for plan in plans:
    SubscriptionPlan.objects.update_or_create(
        plan_type=plan["plan_type"],
        defaults=plan
    )

print("Created subscription plans.")
