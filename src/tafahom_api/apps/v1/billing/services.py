from django.db import transaction
from django.db.models import F
from .models import TokenTransaction


def consume_translation_token(subscription, amount=7):
    """
    Consumes tokens from the subscription and logs the transaction.
    """
    with transaction.atomic():
        subscription.consume(amount)

        TokenTransaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=-amount,
            transaction_type="used",
            reason="Translation request",
        )


def consume_generation_token(subscription, amount=10):
    with transaction.atomic():
        subscription.consume(amount)

        TokenTransaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=-amount,
            transaction_type="used",
            reason="Generation request",
        )


def reward_dataset_contribution(subscription, tokens=10):
    """
    Adds bonus tokens safely avoiding race conditions.
    """
    with transaction.atomic():
        subscription.bonus_tokens = F("bonus_tokens") + tokens
        subscription.save(update_fields=["bonus_tokens"])

        subscription.refresh_from_db()

        TokenTransaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=tokens,
            transaction_type="earned",
            reason="Dataset contribution approved",
        )
