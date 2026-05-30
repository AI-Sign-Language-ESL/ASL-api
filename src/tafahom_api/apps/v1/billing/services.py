"""
Billing services for token consumption
"""
from django.db import transaction
from .models import Subscription
from tafahom_api.common.enums import SUBSCRIPTION_STATUS


def consume_tokens(subscription, amount=1, token_type="translation"):
    """
    Consume tokens from a subscription.
    Delegates to Subscription.consume() which uses SELECT FOR UPDATE
    to prevent the double-spend race condition.
    Returns True if successful, raises ValueError if insufficient tokens.
    """
    try:
        subscription.consume(amount)
        return True
    except ValueError:
        return False

    subscription.consume(amount)
    return True


def consume_meeting_token(subscription, amount=50):
    """
    Consume 50 tokens for joining a meeting.
    Returns True if successful, False if insufficient tokens.
    """
    return consume_tokens(subscription, amount=amount, token_type="meeting")


def consume_translation_token(subscription, amount=10):
    return consume_tokens(subscription, amount=amount, token_type="translation")


def consume_generation_token(subscription, amount=10):
    return consume_tokens(subscription, amount=amount, token_type="generation")

def reward_dataset_contribution(subscription, tokens=10):
    """
    Reward a user with bonus tokens for contributing to the dataset.
    Bonus tokens are added on top of the weekly limit.
    Uses F() for an atomic DB-level increment to avoid read-modify-write races.
    """
    from django.db.models import F
    from .models import TokenTransaction

    with transaction.atomic():
        # Atomic increment — never races with concurrent reward calls
        Subscription.objects.filter(pk=subscription.pk).update(
            bonus_tokens=F("bonus_tokens") + tokens
        )
        subscription.refresh_from_db(fields=["bonus_tokens"])

        TokenTransaction.objects.create(
            user=subscription.user,
            subscription=subscription,
            amount=tokens,
            transaction_type="earned",
            reason="Dataset contribution reward"
        )
    return True
