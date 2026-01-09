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

        # Handle pagination wrapper (DRF returns 'results' list inside a dict)
        data = response.data["results"] if "results" in response.data else response.data

        codes = [lang["code"] for lang in data]
        assert "ase" in codes


@pytest.mark.django_db
class TestCreateTranslationRequestAPI:
    def test_create_translation_request(
        self,
        client: APIClient,
        jwt_user_token: str,
        asl_language,
        free_plan,
        valid_video_file,  # ✅ INJECTED: File fixture from conftest.py
    ):
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_user_token}")

        # ✅ CHANGED: Use 'multipart' format and pass the actual file
        response: Response = client.post(
            "/translation/requests/",
            {
                "direction": "from_sign",
                "input_type": "video",
                "output_type": "text",
                "source_language": asl_language.code,
                "input_video": valid_video_file,  # ✅ Pass the file object
            },
            format="multipart",  # ✅ MUST be multipart for file uploads
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert TranslationRequest.objects.count() == 1

    def test_requires_auth(self, client: APIClient, asl_language):
        # This test can stay JSON as it fails before payload validation
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

        # Handle pagination wrapper
        data = response.data["results"] if "results" in response.data else response.data

        assert len(data) == 1
        assert data[0]["id"] == translation_request.id
