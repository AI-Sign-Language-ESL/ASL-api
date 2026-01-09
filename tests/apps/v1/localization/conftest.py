import pytest

from tafahom_api.apps.v1.localization.models import TranslationKey


# =====================================================
# TRANSLATION KEYS
# =====================================================


@pytest.fixture
def translation_key_en_ar(db: None) -> TranslationKey:
    return TranslationKey.objects.create(
        key="welcome_message",
        description="Welcome message",
        context="homepage",
        text_en="Welcome",
        text_ar="مرحبا",
    )


@pytest.fixture
def translation_key_auth(db: None) -> TranslationKey:
    return TranslationKey.objects.create(
        key="login",
        description="Login button",
        context="authentication",
        text_en="Login",
        text_ar="تسجيل الدخول",
    )
