import pytest

from src.tafahom_api.apps.v1.translation.models import (
    TranslationRequest,
    SignLanguageConfig,
)
from src.tafahom_api.apps.v1.users.models import User


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
