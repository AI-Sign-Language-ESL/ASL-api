import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tafahom_api.apps.v1.translation.services.dtos import (
    CVResponse,
    NLPResponse,
    PipelineConfig,
    TranslationPipelineResult,
)
from tafahom_api.apps.v1.translation.services.sign_translation_service import (
    RetryHandler,
    SignTranslationService,
)


class TestRetryHandler:
    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        handler = RetryHandler(max_retries=3)
        mock_coro = AsyncMock(return_value={"ok": True})

        result = await handler.execute(
            lambda: mock_coro(), service_name="test", timeout=5
        )

        assert result == {"ok": True}
        assert mock_coro.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure_then_success(self):
        handler = RetryHandler(max_retries=3, base_delay=0.01, max_delay=0.05)
        mock_coro = AsyncMock(side_effect=[ValueError("fail"), {"ok": True}])

        result = await handler.execute(
            lambda: mock_coro(), service_name="test", timeout=5
        )

        assert result == {"ok": True}
        assert mock_coro.call_count == 2

    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        handler = RetryHandler(max_retries=2, base_delay=0.01, max_delay=0.05)
        mock_coro = AsyncMock(side_effect=ValueError("persistent"))

        with pytest.raises(ValueError, match="persistent"):
            await handler.execute(
                lambda: mock_coro(), service_name="test", timeout=5
            )

        assert mock_coro.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        handler = RetryHandler(max_retries=2, base_delay=0.01, max_delay=0.05)

        async def slow_coro():
            await asyncio.sleep(10)
            return {"ok": True}

        with pytest.raises(TimeoutError):
            await handler.execute(
                lambda: slow_coro(), service_name="test", timeout=0.05
            )


class TestSignTranslationService:
    @pytest.fixture
    def mock_cv_client(self):
        client = AsyncMock()
        client.send_video_chunk = AsyncMock(
            return_value=CVResponse(gloss="HELLO HOW ARE YOU")
        )
        return client

    @pytest.fixture
    def mock_nlp_client(self):
        client = AsyncMock()
        client.translate_gloss = AsyncMock(
            return_value=NLPResponse(text="مرحباً كيف حالك")
        )
        return client

    @pytest.fixture
    def event_collector(self):
        events = []

        async def collector(payload):
            events.append(payload)

        collector.events = events
        return collector

    @pytest.fixture
    def service(self, mock_cv_client, mock_nlp_client, event_collector):
        return SignTranslationService(
            cv_client=mock_cv_client,
            nlp_client=mock_nlp_client,
            retry_handler=RetryHandler(max_retries=1, base_delay=0.01),
            config=PipelineConfig(cv_timeout=5, nlp_timeout=5),
            event_callback=event_collector,
        )

    @pytest.mark.asyncio
    async def test_translate_success(self, service, event_collector):
        frames = [b"frame1_data", b"frame2_data", b"frame3_data"]

        result = await service.translate(frames)

        assert result.success is True
        assert result.gloss == "HELLO HOW ARE YOU"
        assert result.text == "مرحباً كيف حالك"
        assert result.cv_latency_ms is not None
        assert result.nlp_latency_ms is not None
        assert result.total_latency_ms is not None

    @pytest.mark.asyncio
    async def test_events_emitted_in_order(self, service, event_collector):
        frames = [b"test_frame"]

        await service.translate(frames)

        event_types = [e["type"] for e in event_collector.events]
        assert event_types == [
            "translation_started",
            "gloss_received",
            "translation_received",
        ]

    @pytest.mark.asyncio
    async def test_gloss_received_event_content(self, service, event_collector):
        frames = [b"test_frame"]

        await service.translate(frames)

        gloss_events = [
            e for e in event_collector.events if e["type"] == "gloss_received"
        ]
        assert len(gloss_events) == 1
        assert gloss_events[0]["gloss"] == "HELLO HOW ARE YOU"

    @pytest.mark.asyncio
    async def test_translation_received_event_content(
        self, service, event_collector
    ):
        frames = [b"test_frame"]

        await service.translate(frames)

        tr_events = [
            e
            for e in event_collector.events
            if e["type"] == "translation_received"
        ]
        assert len(tr_events) == 1
        assert tr_events[0]["gloss"] == "HELLO HOW ARE YOU"
        assert tr_events[0]["text"] == "مرحباً كيف حالك"

    @pytest.mark.asyncio
    async def test_empty_frames_returns_error(self, service, event_collector):
        result = await service.translate([])

        assert result.success is False
        assert result.error == "No frames provided"

    @pytest.mark.asyncio
    async def test_cv_failure_emits_error_event(self, mock_nlp_client, event_collector):
        failing_cv = AsyncMock()
        failing_cv.send_video_chunk = AsyncMock(
            side_effect=ValueError("CV model down")
        )
        service = SignTranslationService(
            cv_client=failing_cv,
            nlp_client=mock_nlp_client,
            retry_handler=RetryHandler(max_retries=1, base_delay=0.01),
            config=PipelineConfig(cv_timeout=1, nlp_timeout=1),
            event_callback=event_collector,
        )

        with pytest.raises(ValueError, match="CV model down"):
            await service.translate([b"test"])

        error_events = [
            e for e in event_collector.events if e["type"] == "translation_error"
        ]
        assert len(error_events) >= 1
        assert error_events[0]["stage"] == "cv"

    @pytest.mark.asyncio
    async def test_nlp_failure_emits_error_event(self, mock_cv_client, event_collector):
        failing_nlp = AsyncMock()
        failing_nlp.translate_gloss = AsyncMock(
            side_effect=ValueError("NLP model down")
        )
        service = SignTranslationService(
            cv_client=mock_cv_client,
            nlp_client=failing_nlp,
            retry_handler=RetryHandler(max_retries=1, base_delay=0.01),
            config=PipelineConfig(cv_timeout=1, nlp_timeout=1),
            event_callback=event_collector,
        )

        with pytest.raises(ValueError, match="NLP model down"):
            await service.translate([b"test"])

        error_events = [
            e for e in event_collector.events if e["type"] == "translation_error"
        ]
        assert len(error_events) >= 1
        assert error_events[-1]["stage"] == "nlp"

    @pytest.mark.asyncio
    async def test_gloss_is_uppercased(self, service, event_collector):
        service.cv_client.send_video_chunk = AsyncMock(
            return_value=CVResponse(gloss="hello world")
        )

        result = await service.translate([b"frame"])

        assert result.gloss == "HELLO WORLD"

    @pytest.mark.asyncio
    async def test_cv_http_fallback_dict_response(self, mock_nlp_client, event_collector):
        cv_dict = AsyncMock()
        cv_dict.send_video_chunk = AsyncMock(
            return_value={"gloss": "HELLO FROM DICT"}
        )
        service = SignTranslationService(
            cv_client=cv_dict,
            nlp_client=mock_nlp_client,
            event_callback=event_collector,
        )

        result = await service.translate([b"frame"])

        assert result.success is True
        assert result.gloss == "HELLO FROM DICT"

    @pytest.mark.asyncio
    async def test_nlp_dict_response_fallback(self, mock_cv_client, event_collector):
        nlp_dict = AsyncMock()
        nlp_dict.translate_gloss = AsyncMock(
            return_value={"text": "مرحباً", "raw": {}}
        )
        service = SignTranslationService(
            cv_client=mock_cv_client,
            nlp_client=nlp_dict,
            event_callback=event_collector,
        )

        result = await service.translate([b"frame"])

        assert result.success is True
        assert result.text == "مرحباً"


class TestSignTranslationServiceDI:
    """
    Tests verifying that dependency injection works correctly.
    """

    @pytest.mark.asyncio
    async def test_default_instantiation(self):
        service = SignTranslationService()
        assert service.cv_client is not None
        assert service.nlp_client is not None
        assert service.retry_handler is not None
        assert service.config is not None

    @pytest.mark.asyncio
    async def test_custom_clients_injected(self, mock_cv_client, mock_nlp_client):
        service = SignTranslationService(
            cv_client=mock_cv_client,
            nlp_client=mock_nlp_client,
        )
        assert service.cv_client is mock_cv_client
        assert service.nlp_client is mock_nlp_client

    @pytest.mark.asyncio
    async def test_custom_retry_handler(self):
        handler = RetryHandler(max_retries=5, base_delay=2.0)
        service = SignTranslationService(retry_handler=handler)
        assert service.retry_handler.max_retries == 5
        assert service.retry_handler.base_delay == 2.0

    @pytest.mark.asyncio
    async def test_custom_config(self):
        config = PipelineConfig(pipeline_timeout_seconds=30, cv_timeout=60)
        service = SignTranslationService(config=config)
        assert service.config.pipeline_timeout_seconds == 30
        assert service.config.cv_timeout == 60

    @pytest.mark.asyncio
    async def test_event_callback_called(self):
        callback = AsyncMock()
        service = SignTranslationService(event_callback=callback)
        service.cv_client.send_video_chunk = AsyncMock(
            return_value=CVResponse(gloss="HI")
        )
        service.nlp_client.translate_gloss = AsyncMock(
            return_value=NLPResponse(text="مرحبا")
        )

        await service.translate([b"frame"])

        assert callback.call_count >= 1
