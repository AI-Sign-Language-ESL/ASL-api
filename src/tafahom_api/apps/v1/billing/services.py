from django.db import transaction
from django.db.models import F
from .models import TokenTransaction
from tafahom_api.common.decorators import TOKEN_COSTS


def consume_translation_token(subscription, amount=None):
    """
    Consumes tokens from the subscription and logs the transaction.
    Uses TOKEN_COSTS if amount not specified.
    """
    actual_amount = amount if amount is not None else TOKEN_COSTS.get("translation", 5)
    with transaction.atomic():
        subscription.consume(actual_amount)

        TokenTransaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=-actual_amount,
            transaction_type="used",
            reason="Translation request",
        )


def consume_generation_token(subscription, amount=None):
    actual_amount = amount if amount is not None else TOKEN_COSTS.get("generation", 10)
    with transaction.atomic():
        subscription.consume(actual_amount)

        TokenTransaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=-actual_amount,
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
