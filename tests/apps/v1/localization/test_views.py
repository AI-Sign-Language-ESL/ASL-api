import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from src.tafahom_api.apps.v1.localization.models import TranslationKey
from src.tafahom_api.apps.v1.users.models import User

@pytest.mark.django_db
class TestLanguageListAPI:
    def test_list_languages(self, client: APIClient):
        response: Response = client.get("/localization/languages/")

        assert response.status_code == status.HTTP_200_OK
        assert "languages" in response.data
        assert "current_language" in response.data

    def test_languages_include_arabic(self, client: APIClient):
        response = client.get("/localization/languages/")
        codes = [lang["code"] for lang in response.data["languages"]]

        assert "ar" in codes

@pytest.mark.django_db
class TestSetLanguageAPI:
    def test_set_language_success(self, client: APIClient):
        response: Response = client.post(
            "/localization/set-language/",
            {"language": "ar"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["language_code"] == "ar"
        assert response.data["is_rtl"] is True
        assert "django_language" in response.cookies

    def test_set_invalid_language(self, client: APIClient):
        response = client.post(
            "/localization/set-language/",
            {"language": "fr"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
class TestCurrentLanguageAPI:
    def test_current_language_default(self, client: APIClient):
        response: Response = client.get(
            "/localization/current-language/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["language_code"] in ["en", "ar"]
        assert "direction" in response.data
        assert "is_rtl" in response.data

@pytest.mark.django_db
class TestBulkTranslationAPI:
    def test_bulk_translation_success(
        self,
        client: APIClient,
        translation_key_en_ar: TranslationKey,
        translation_key_auth: TranslationKey,
    ):
        payload = {
            "keys": ["welcome_message", "login"],
            "language": "en",
        }

        response: Response = client.post(
            "/localization/translations/bulk/",
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["translations"]["welcome_message"] == "Welcome"
        assert response.data["translations"]["login"] == "Login"

    def test_bulk_translation_arabic(
        self,
        client: APIClient,
        translation_key_en_ar: TranslationKey,
    ):
        response = client.post(
            "/localization/translations/bulk/",
            {"keys": ["welcome_message"], "language": "ar"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["translations"]["welcome_message"] == "مرحبا"

    def test_bulk_translation_missing_key(self, client: APIClient):
        response = client.post(
            "/localization/translations/bulk/",
            {"keys": ["missing_key"], "language": "en"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["translations"]["missing_key"] == "missing_key"

    def test_bulk_translation_empty_keys(self, client: APIClient):
        response = client.post(
            "/localization/translations/bulk/",
            {"keys": [], "language": "en"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_translation_too_many_keys(self, client: APIClient):
        response = client.post(
            "/localization/translations/bulk/",
            {
                "keys": [f"k{i}" for i in range(101)],
                "language": "en",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
class TestTranslationKeyAdminListAPI:
    def test_admin_can_list_keys(
        self,
        client: APIClient,
        admin_user: User,
        jwt_admin_token: str,
        translation_key_en_ar: TranslationKey,
    ):
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jwt_admin_token}"
        )

        response: Response = client.get("/localization/keys/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"][0]["key"] == "welcome_message"

    def test_non_admin_forbidden(
        self,
        client: APIClient,
        jwt_user_token: str,
    ):
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}"
        )

        response = client.get("/localization/keys/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
class TestTranslationKeyUpdateAPI:
    def test_update_translation_key(
        self,
        client: APIClient,
        admin_user: User,
        jwt_admin_token: str,
        translation_key_en_ar: TranslationKey,
    ):
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {jwt_admin_token}"
        )

        response: Response = client.patch(
            f"/localization/keys/{translation_key_en_ar.id}/",
            {"text_en": "Welcome Updated"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        translation_key_en_ar.refresh_from_db()
        assert translation_key_en_ar.text_en == "Welcome Updated"

@pytest.mark.django_db
class TestLocalizationPermissions:
    def test_anonymous_can_access_languages(self, client: APIClient):
        response = client.get("/localization/languages/")
        assert response.status_code == status.HTTP_200_OK

    def test_anonymous_can_access_bulk(self, client: APIClient):
        response = client.post(
            "/localization/translations/bulk/",
            {"keys": ["welcome_message"], "language": "en"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
