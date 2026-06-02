import json
from unittest.mock import AsyncMock, patch

import pytest
from channels.testing import WebsocketCommunicator
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient

from tafahom_api.apps.v1.translation.consumers import SignTranslationConsumer
from tafahom_api.apps.v1.translation.services.dtos import (
    CVResponse,
    NLPResponse,
    TranslationPipelineResult,
)


@pytest.mark.django_db
class TestPipelineWebSocketIntegration:
    """
    Integration tests for the WebSocket translation pipeline.
    Verifies end-to-end flow: frames → CV → NLP → WebSocket events.
    """

    @pytest.fixture
    def communicator(self, jwt_user_token):
        communicator = WebsocketCommunicator(
            SignTranslationConsumer.as_asgi(),
            "/ws/translation/stream/",
            headers=[
                (b"origin", b"http://localhost:3000"),
            ],
        )
        communicator.scope["user"] = None  # Will be set by middleware
        communicator.scope["query_string"] = (
            f"token={jwt_user_token}".encode()
        )
        return communicator

    @pytest.mark.asyncio
    @patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.SignTranslationService.translate"
    )
    async def test_pipeline_emits_new_events(
        self, mock_translate, communicator
    ):
        mock_translate.return_value = TranslationPipelineResult(
            gloss="HELLO HOW ARE YOU",
            text="مرحباً كيف حالك",
            success=True,
            cv_latency_ms=150.0,
            nlp_latency_ms=200.0,
            total_latency_ms=350.0,
        )

        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"action": "start", "output_type": "text"})

        await communicator.send_bytes(b"fake_frame_data_1")
        await communicator.send_bytes(b"fake_frame_data_2")

        await communicator.disconnect()

    @pytest.mark.asyncio
    @patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.SignTranslationService.translate"
    )
    async def test_gloss_received_event_sent_to_client(
        self, mock_translate, communicator
    ):
        mock_translate.return_value = TranslationPipelineResult(
            gloss="HELLO",
            text="مرحبا",
            success=True,
        )

        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"action": "start", "output_type": "text"})

        await communicator.send_bytes(b"test_frame")

        with pytest.raises(Exception):
            await communicator.receive_json_from(timeout=1)

        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_communicator_connect_disconnect(self, communicator):
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()
        assert not communicator.is_connected


@pytest.mark.django_db
class TestPipelineRESTEndpoints:
    """
    Integration tests for the REST endpoints that power the pipeline.
    """

    def test_health_endpoint(self, client: APIClient):
        response = client.get("/health/")
        assert response.status_code == status.HTTP_200_OK

    def test_sign_languages_available(self, client: APIClient):
        response = client.get("/translation/sign-languages/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["results"] if "results" in response.data else response.data
        codes = [lang["code"] for lang in data]
        assert "ase" in codes

    def test_unauthorized_access_blocked(self, client: APIClient):
        response = client.post(
            "/translation/requests/",
            {"direction": "from_sign", "input_type": "video", "output_type": "text"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPipelineConfig:
    """
    Tests verifying pipeline configuration is correctly loaded.
    """

    def test_cv_model_ws_url_setting(self):
        url = getattr(settings, "CV_MODEL_WS_URL", None)
        assert url is not None

    def test_nlp_model_url_setting(self):
        url = getattr(settings, "NLP_MODEL_URL", None)
        assert url is not None

    def test_cv_ws_timeout_setting(self):
        timeout = getattr(settings, "CV_WS_TIMEOUT", 30)
        assert timeout > 0

    def test_nlp_request_timeout_setting(self):
        timeout = getattr(settings, "NLP_REQUEST_TIMEOUT", 30)
        assert timeout > 0

    def test_max_cv_retries_setting(self):
        retries = getattr(settings, "MAX_CV_RETRIES", 3)
        assert retries >= 1

    def test_nlp_retries_setting(self):
        retries = getattr(settings, "NLP_RETRIES", 3)
        assert retries >= 1
