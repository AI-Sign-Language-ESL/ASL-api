import pytest
from rest_framework_simplejwt.tokens import AccessToken

from src.tafahom_api.apps.v1.users.models import User
from src.tafahom_api.apps.v1.billing.models import (
    SubscriptionPlan,
    Subscription,
)


# =====================================================
# PLANS
# =====================================================

@pytest.fixture
def free_plan(db) -> SubscriptionPlan:
    return SubscriptionPlan.objects.create(
        name="Free",
        plan_type="free",
        credits_per_month=50,
        price=0,
        is_active=True,
    )


@pytest.fixture
def paid_plan(db) -> SubscriptionPlan:
    return SubscriptionPlan.objects.create(
        name="Pro",
        plan_type="pro",
        credits_per_month=500,
        price=99,
        is_active=True,
    )


# =====================================================
# SUBSCRIPTIONS
# =====================================================

@pytest.fixture
def user_subscription(
    db,
    existing_user: User,
    free_plan: SubscriptionPlan,
) -> Subscription:
    return Subscription.objects.create(
        user=existing_user,
        plan=free_plan,
        status="active",
        billing_period="monthly",
        credits_used=0,
        bonus_credits=0,
    )


# =====================================================
# JWT (OPTIONAL IF YOU WANT LOCAL TOKENS)
# =====================================================

@pytest.fixture
def jwt_user_token(existing_user: User) -> str:
    return str(AccessToken.for_user(existing_user))
