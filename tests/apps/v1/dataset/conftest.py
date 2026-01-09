import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from src.tafahom_api.apps.v1.dataset.models import DatasetContribution
from src.tafahom_api.apps.v1.users.models import User
from src.tafahom_api.apps.v1.billing.models import SubscriptionPlan, Subscription


# =====================================================
# VIDEO FILE
# =====================================================

@pytest.fixture
def valid_video_file() -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name="test.mp4",
        content=b"fake video content",
        content_type="video/mp4",
    )


# =====================================================
# DATASET CONTRIBUTION
# =====================================================

@pytest.fixture
def dataset_contribution(
    db,
    existing_user: User,
    valid_video_file: SimpleUploadedFile,
) -> DatasetContribution:
    return DatasetContribution.objects.create(
        contributor=existing_user,
        word="hello",
        video=valid_video_file,
        status="pending",
    )


# =====================================================
# BILLING (FOR REWARD FLOW)
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
