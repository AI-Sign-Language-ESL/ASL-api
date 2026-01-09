from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from tafahom_api.common.enums import (
    PLAN_TYPES,
    SUBSCRIPTION_STATUS,
    CREDIT_TRANSACTION_TYPES,
)


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)

    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPES,
        unique=True,
    )

    credits_per_month = models.PositiveIntegerField(default=50)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscription_plans"

    def __str__(self):
        return f"{self.name} ({self.plan_type})"


class Subscription(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
    )

    status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS,
        default="active",
    )
    billing_period = models.CharField(
        max_length=20,
        choices=[("monthly", "Monthly"), ("yearly", "Yearly")],
        default="monthly",
    )

    end_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    last_reset = models.DateTimeField(default=timezone.now)

    credits_used = models.PositiveIntegerField(default=0)
    bonus_credits = models.IntegerField(default=0)

    class Meta:
        db_table = "subscriptions"

    def reset_if_needed(self):
        if timezone.now() - self.last_reset >= timedelta(days=30):
            self.credits_used = 0
            self.last_reset = timezone.now()
            self.save(update_fields=["credits_used", "last_reset"])

    def total_credits(self):
        return self.plan.credits_per_month + self.bonus_credits

    def remaining_credits(self):
        self.reset_if_needed()
        return max(0, self.total_credits() - self.credits_used)

    def can_consume(self, amount=1):
        return self.remaining_credits() >= amount

    def consume(self, amount=1):
        if not self.can_consume(amount):
            raise ValueError("Not enough credits")
        self.credits_used += amount
        self.save(update_fields=["credits_used"])


class CreditTransaction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
    )

    amount = models.IntegerField()

    transaction_type = models.CharField(
        max_length=20,
        choices=CREDIT_TRANSACTION_TYPES,
    )

    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "credit_transactions"
        ordering = ["-created_at"]
