from django.db import migrations
from decimal import Decimal


def update_plan_data(apps, schema_editor):
    SubscriptionPlan = apps.get_model("billing", "SubscriptionPlan")

    # Rename "premium" to "enterprise" and update all plans
    updates = {
        "free": {
            "name": "Free Plan",
            "weekly_tokens_limit": 50,
            "price": Decimal("0.00"),
            "currency": "EGP",
        },
        "basic": {
            "name": "Basic Plan",
            "weekly_tokens_limit": 250,
            "price": Decimal("100.00"),
            "currency": "EGP",
        },
        "go": {
            "name": "GO Plan",
            "weekly_tokens_limit": 500,
            "price": Decimal("175.00"),
            "currency": "EGP",
        },
        "enterprise": {
            "name": "Enterprise Plan",
            "weekly_tokens_limit": 2000,
            "price": Decimal("750.00"),
            "currency": "EGP",
        },
    }

    # Update existing "premium" plan_type to "enterprise"
    SubscriptionPlan.objects.filter(plan_type="premium").update(plan_type="enterprise")

    for plan_type, data in updates.items():
        SubscriptionPlan.objects.update_or_create(
            plan_type=plan_type,
            defaults=data,
        )


def reverse_plan_data(apps, schema_editor):
    SubscriptionPlan = apps.get_model("billing", "SubscriptionPlan")

    # Revert enterprise back to premium
    SubscriptionPlan.objects.filter(plan_type="enterprise").update(plan_type="premium")

    revert = {
        "free": {"name": "Free Plan", "weekly_tokens_limit": 50, "price": Decimal("0.00"), "currency": "USD"},
        "basic": {"name": "Basic Plan", "weekly_tokens_limit": 200, "price": Decimal("9.99"), "currency": "USD"},
        "go": {"name": "GO Plan", "weekly_tokens_limit": 400, "price": Decimal("19.99"), "currency": "USD"},
        "premium": {"name": "Premium Plan", "weekly_tokens_limit": 600, "price": Decimal("29.99"), "currency": "USD"},
    }

    for plan_type, data in revert.items():
        SubscriptionPlan.objects.update_or_create(
            plan_type=plan_type,
            defaults=data,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0005_subscriptionplan_currency_and_more"),
    ]

    operations = [
        migrations.RunPython(update_plan_data, reverse_plan_data),
    ]
