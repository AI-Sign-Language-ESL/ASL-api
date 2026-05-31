from django.db import models
from django.db.models import F
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


from tafahom_api.common.enums import (
    PLAN_TYPES,
    SUBSCRIPTION_STATUS,
    TOKEN_TRANSACTION_TYPES,
)


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)

    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPES,
        unique=True,
    )

    weekly_tokens_limit = models.PositiveIntegerField(default=50)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, choices=[("EGP", "EGP"), ("USD", "USD")], default="EGP")
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
        default="pending",  # Changed default to pending (waiting for payment)
    )
    billing_period = models.CharField(
        max_length=20,
        choices=[("monthly", "Monthly"), ("yearly", "Yearly")],
        default="monthly",
    )
    auto_renewal = models.BooleanField(default=True)

    end_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    last_reset = models.DateTimeField(default=timezone.now)

    tokens_used = models.PositiveIntegerField(default=0)
    bonus_tokens = models.IntegerField(default=0)

    # Payment tracking
    payment_id = models.CharField(max_length=255, blank=True, null=True)
    payment_provider = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "subscriptions"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "end_date"]),
        ]

    def reset_if_needed(self):
        """Reset weekly token usage if 7+ days have elapsed since last reset.
        Uses F() to avoid a race condition on the reset itself.
        """
        if timezone.now() - self.last_reset >= timedelta(days=7):
            # Atomic reset — no read-modify-write
            Subscription.objects.filter(pk=self.pk).update(
                tokens_used=0,
                last_reset=timezone.now(),
            )
            # Refresh instance so callers see current values
            self.refresh_from_db(fields=["tokens_used", "last_reset"])

    def total_tokens(self):
        return self.plan.weekly_tokens_limit + self.bonus_tokens

    def remaining_tokens(self):
        self.reset_if_needed()
        return max(0, self.plan.weekly_tokens_limit - self.tokens_used) + self.bonus_tokens

    def can_consume(self, amount=1):
        return self.remaining_tokens() >= amount

    def consume(self, amount=1):
        """
        Atomically consume `amount` tokens using a DB-level SELECT FOR UPDATE +
        conditional F() update.  This eliminates the TOCTOU race condition where
        two concurrent requests both pass can_consume(), both proceed, and both
        decrement the balance — resulting in negative / over-consumed tokens.

        Algorithm:
          1. Re-fetch this row with a row-level lock (SELECT FOR UPDATE).
          2. Recalculate balance inside the lock.
          3. Raise ValueError immediately if balance is insufficient.
          4. Deduct from bonus_tokens first, then tokens_used, using F() so the
             arithmetic happens in a single atomic SQL UPDATE statement.
        """
        from django.db import transaction

        with transaction.atomic():
            # Lock the row for the duration of this transaction
            locked = Subscription.objects.select_for_update().get(pk=self.pk)
            locked.reset_if_needed()

            remaining = max(0, locked.plan.weekly_tokens_limit - locked.tokens_used) + locked.bonus_tokens
            if remaining < amount:
                raise ValueError("Not enough tokens")

            # Deduct from bonus_tokens first, then from the weekly allowance
            if locked.bonus_tokens >= amount:
                Subscription.objects.filter(pk=self.pk).update(
                    bonus_tokens=F("bonus_tokens") - amount
                )
            else:
                remainder = amount - locked.bonus_tokens
                Subscription.objects.filter(pk=self.pk).update(
                    bonus_tokens=0,
                    tokens_used=F("tokens_used") + remainder,
                )

            # Mark cycle start on first spend from weekly allowance
            if locked.tokens_used == 0 and locked.bonus_tokens < amount:
                Subscription.objects.filter(pk=self.pk).update(
                    last_reset=timezone.now()
                )

            # Sync the in-memory instance so callers get correct values
            self.refresh_from_db(fields=["tokens_used", "bonus_tokens", "last_reset"])


class PaymentTransaction(models.Model):
    """Track Visa/Payment provider transactions"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    # Payment provider data
    transaction_id = models.CharField(max_length=255, unique=True)
    provider = models.CharField(max_length=50, default="visa")  # visa, stripe, etc.

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        default="pending",
    )

    payment_method = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Webhook data (store raw response for debugging)
    webhook_data = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = "payment_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["transaction_id"]),
        ]


class TokenTransaction(models.Model):
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
        choices=TOKEN_TRANSACTION_TYPES,
    )

    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "token_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["subscription", "-created_at"]),
        ]
