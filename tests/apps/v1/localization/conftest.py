import pytest
from tafahom_api.apps.v1.localization.models import TranslationKey


@pytest.fixture
def translation_key_en_ar(db) -> TranslationKey:
    """
    General translation key used across localization tests.
    Using 'test_prefix' to avoid collision with seeded database data.
    """
    # Use update_or_create to ensure the test values are enforced
    # even if the record somehow exists from a previous run
    obj, _ = TranslationKey.objects.update_or_create(
        key="test_welcome_message",
        defaults={
            "description": "Test Welcome message",
            "context": "homepage",
            "text_en": "Welcome",
            "text_ar": "مرحبا",
        },
    )
    return obj


@pytest.fixture
def translation_key_auth(db) -> TranslationKey:
    """
    Authentication-related translation key.
    """
    obj, _ = TranslationKey.objects.update_or_create(
        key="test_login",
        defaults={
            "description": "Test Login button",
            "context": "authentication",
            "text_en": "Login",
            "text_ar": "تسجيل الدخول",
        },
    )
    return obj
