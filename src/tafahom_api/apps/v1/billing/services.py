"""
Billing services for token consumption
"""
from django.db import transaction
from .models import Subscription
from tafahom_api.common.enums import SUBSCRIPTION_STATUS


def consume_tokens(subscription, amount=1, token_type="translation"):
    """
    Consume tokens from a subscription.
    Returns True if successful, False if insufficient tokens.
    """
    if not subscription.can_consume(amount):
        return False

    with transaction.atomic():
        subscription.tokens_used += amount
        subscription.save(update_fields=["tokens_used"])
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
    Reward a user with tokens for contributing to the dataset.
    """
    from django.db import transaction
    with transaction.atomic():
        subscription.tokens_used = max(0, subscription.tokens_used - tokens)
        subscription.save(update_fields=["tokens_used"])
    return True
