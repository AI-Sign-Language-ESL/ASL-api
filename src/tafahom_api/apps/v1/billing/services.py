from django.db import transaction
from django.db.models import F
from .models import CreditTransaction


def consume_translation_credit(subscription):
    """
    Consumes 1 credit from the subscription and logs the transaction.
    Atomic ensures both happen or neither happens.
    """
    with transaction.atomic():
        subscription.consume(1)

        CreditTransaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=-1,
            transaction_type="used",
            reason="Translation request",
        )


def reward_dataset_contribution(subscription, credits=10):
    """
    Adds bonus credits safely avoiding race conditions.
    """
    with transaction.atomic():
        subscription.bonus_credits = F("bonus_credits") + credits
        subscription.save(update_fields=["bonus_credits"])

        subscription.refresh_from_db()

        CreditTransaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=credits,
            transaction_type="earned",
            reason="Dataset contribution approved",
        )
