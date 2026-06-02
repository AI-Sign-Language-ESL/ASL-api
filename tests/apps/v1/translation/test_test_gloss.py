import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestTestGlossEndpoint:
    endpoint = "/sign-language/test-gloss/"

    def test_requires_gloss(self, client: APIClient):
        response = client.post(self.endpoint, {"gloss": ""}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not be empty" in response.data["error"]

    def test_requires_gloss_key(self, client: APIClient):
        response = client.post(self.endpoint, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_gloss_only_whitespace(self, client: APIClient):
        response = client.post(self.endpoint, {"gloss": "   "}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("tafahom_api.apps.v1.translation.views.httpx.Client")
    def test_successful_translation(self, mock_httpx_client, client: APIClient):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"translation": "سبب الرغبة في الشراء"}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_response

        response = client.post(
            self.endpoint,
            {"gloss": "سبب رغبه شراء"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["gloss"] == "سبب رغبه شراء"
        assert response.data["translation"] == "سبب الرغبة في الشراء"

    @patch("tafahom_api.apps.v1.translation.views.httpx.Client")
    def test_handles_nlp_text_field(self, mock_httpx_client, client: APIClient):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "سبب الرغبة في الشراء"}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_response

        response = client.post(
            self.endpoint,
            {"gloss": "سبب رغبه شراء"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["translation"] == "سبب الرغبة في الشراء"

    @patch("tafahom_api.apps.v1.translation.views.httpx.Client")
    def test_handles_nlp_gloss_field(self, mock_httpx_client, client: APIClient):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"gloss": "سبب الرغبة في الشراء"}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_response

        response = client.post(
            self.endpoint,
            {"gloss": "سبب رغبه شراء"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["translation"] == "سبب الرغبة في الشراء"

    @patch("tafahom_api.apps.v1.translation.views.httpx.Client")
    def test_retry_on_503(self, mock_httpx_client, client: APIClient):
        mock_503 = MagicMock()
        mock_503.status_code = 503
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"translation": "سبب الرغبة"}

        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_503,
            mock_200,
        ]

        response = client.post(
            self.endpoint,
            {"gloss": "سبب رغبه شراء"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["translation"] == "سبب الرغبة"
        assert mock_httpx_client.return_value.__enter__.return_value.post.call_count == 2

    @patch("tafahom_api.apps.v1.translation.views.httpx.Client")
    def test_all_retries_exhausted(self, mock_httpx_client, client: APIClient):
        mock_503 = MagicMock()
        mock_503.status_code = 503

        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_503

        response = client.post(
            self.endpoint,
            {"gloss": "سبب رغبه شراء"},
            format="json",
        )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "error" in response.data

    @patch("tafahom_api.apps.v1.translation.views.httpx.Client")
    def test_timeout_handling(self, mock_httpx_client, client: APIClient):
        from httpx import TimeoutException

        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = TimeoutException("Timed out")

        response = client.post(
            self.endpoint,
            {"gloss": "سبب رغبه شراء"},
            format="json",
        )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "error" in response.data
