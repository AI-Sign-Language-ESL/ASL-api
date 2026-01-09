import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from tafahom_api.apps.v1.translation.models import TranslationRequest


@pytest.mark.django_db
class TestSignLanguagesAPI:
    def test_list_sign_languages(self, client: APIClient):
        response: Response = client.get("/translation/sign-languages/")
        assert response.status_code == status.HTTP_200_OK

        codes = [lang["code"] for lang in response.data]
        assert "ase" in codes


@pytest.mark.django_db
class TestCreateTranslationRequestAPI:
    def test_create_translation_request(
        self,
        client: APIClient,
        jwt_user_token: str,
        asl_language,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response: Response = client.post(
            "/translation/requests/",
            {
                "direction": "from_sign",
                "input_type": "video",
                "output_type": "text",
                "source_language": asl_language.code,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert TranslationRequest.objects.count() == 1

    def test_requires_auth(self, client: APIClient, asl_language):
        response = client.post(
            "/translation/requests/",
            {
                "direction": "from_sign",
                "input_type": "video",
                "output_type": "text",
                "source_language": asl_language.code,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestMyTranslationRequestsAPI:
    def test_list_my_requests(
        self,
        client: APIClient,
        jwt_user_token: str,
        translation_request,
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        response: Response = client.get("/translation/requests/me/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
