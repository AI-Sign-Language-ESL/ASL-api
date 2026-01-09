import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from tafahom_api.apps.v1.translation.models import (
    TranslationRequest,
    SignLanguageConfig,
)
from tafahom_api.apps.v1.users.models import User
from tafahom_api.apps.v1.billing.models import SubscriptionPlan


@pytest.fixture
def asl_language(db) -> SignLanguageConfig:
    return SignLanguageConfig.objects.get(code="ase")


@pytest.fixture
def translation_request(
    db,
    existing_user: User,
    asl_language: SignLanguageConfig,
) -> TranslationRequest:
    return TranslationRequest.objects.create(
        user=existing_user,
        direction="from_sign",
        input_type="video",
        output_type="text",
        status="pending",
        source_language=asl_language.code,
        processing_mode="batch",
    )


@pytest.fixture
def free_plan(db) -> SubscriptionPlan:
    return SubscriptionPlan.objects.create(
        name="Free",
        plan_type="free",
        credits_per_month=50,
        price=0,
        is_active=True,
    )


# ✅ Added missing video file fixture
@pytest.fixture
def valid_video_file() -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name="test_translation.mp4",
        content=b"fake video content",
        content_type="video/mp4",
    )
