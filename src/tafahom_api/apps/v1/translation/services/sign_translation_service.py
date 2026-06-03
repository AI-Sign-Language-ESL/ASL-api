import asyncio
import logging
import time
from typing import Any, Callable, List, Optional
from tafahom_api.apps.v1.ai.clients.cv_ws_client import get_cv_client
from tafahom_api.apps.v1.ai.clients.nlp_model_client import NLPModelClient
from django.conf import settings

from tafahom_api.apps.v1.translation.services.dtos import (
    CVResponse,
    NLPResponse,
    PipelineConfig,
    TranslationPipelineResult,
)

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Async retry with exponential backoff for AI service calls.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 5.0,
        backoff_factor: float = 2.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    async def execute(
        self,
        coro_factory: Callable,
        service_name: str = "unknown",
        timeout: Optional[float] = None,
    ) -> Any:
        last_exc = None

        for attempt in range(1, self.max_retries + 1):
            try:
                coro = coro_factory()
                if timeout:
                    result = await asyncio.wait_for(coro, timeout=timeout)
                else:
                    result = await coro

                if attempt > 1:
                    logger.info(
                        "%s succeeded on retry %d",
                        service_name,
                        attempt,
                    )
                return result

            except asyncio.TimeoutError:
                last_exc = TimeoutError(f"{service_name} timed out")
                logger.warning(
                    "%s timeout (attempt %d/%d)",
                    service_name,
                    attempt,
                    self.max_retries,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "%s failed (attempt %d/%d): %s",
                    service_name,
                    attempt,
                    self.max_retries,
                    str(exc),
                )

            if attempt < self.max_retries:
                delay = min(
                    self.base_delay * (self.backoff_factor ** (attempt - 1)),
                    self.max_delay,
                )
                await asyncio.sleep(delay)

        raise last_exc or RuntimeError(f"{service_name} failed after {self.max_retries} retries")


class SignTranslationService:
    """
    Orchestrates the sign language translation pipeline.

    Pipeline:
        1. Receive buffered video frames
        2. Send to CV model → receives gloss text
        3. Send gloss to NLP model → receives Arabic text
        4. Return TranslationPipelineResult with full metadata

    Supports:
        - Dependency injection of CV and NLP clients
        - Retry handling with exponential backoff
        - Per-call timeout protection
        - Structured logging at every stage
        - Latency tracking per stage
    """

    def __init__(
        self,
        cv_client=None,
        nlp_client=None,
        retry_handler: Optional[RetryHandler] = None,
        config: Optional[PipelineConfig] = None,
        event_callback: Optional[Callable] = None,
    ):
        

        self.cv_client = cv_client or get_cv_client()
        self.nlp_client = nlp_client or NLPModelClient()
        self.retry_handler = retry_handler or RetryHandler(
            max_retries=getattr(settings, "MAX_CV_RETRIES", 3),
            base_delay=0.5,
            max_delay=5.0,
        )
        self.config = config or PipelineConfig()
        self.event_callback = event_callback

    async def initialize(self):
        """Called to initialize any persistent connections."""
        if hasattr(self.cv_client, "connect"):
            await self.cv_client.connect()

    async def cleanup(self):
        """Called to close persistent connections."""
        if hasattr(self.cv_client, "disconnect"):
            await self.cv_client.disconnect()

    async def translate(
        self, frames: List[bytes], session_id: Optional[str] = None
    ) -> TranslationPipelineResult:
        """
        Run the full CV → NLP translation pipeline on buffered frames.

        Args:
            frames: List of binary video frame bytes.
            session_id: Optional session identifier for logging.

        Returns:
            TranslationPipelineResult with gloss, text, and timing metadata.
        """
        request_id = session_id or f"tr_{int(time.time() * 1000)}"
        overall_start = time.perf_counter()
        cv_latency: Optional[float] = None
        nlp_latency: Optional[float] = None
        cv_retries = 0
        nlp_retries = 0

        if not frames:
            logger.warning(
                "translate_called_empty_frames",
                extra={"request_id": request_id},
            )
            return TranslationPipelineResult(
                gloss="",
                text="",
                success=False,
                error="No frames provided",
            )

        try:
            await self._emit_event("translation_started", {"request_id": request_id})
        except Exception:
            pass

        combined_chunk = b"".join(frames)

        cv_start = time.perf_counter()
        cv_result = await self._call_cv_with_retry(
            combined_chunk, request_id
        )
        cv_latency = (time.perf_counter() - cv_start) * 1000

        gloss = cv_result.gloss
        gloss_upper = gloss.strip().upper()

        logger.info(
            "cv_result",
            extra={
                "request_id": request_id,
                "gloss": gloss_upper,
                "latency_ms": round(cv_latency, 2),
            },
        )

        try:
            await self._emit_event(
                "gloss_received",
                {"request_id": request_id, "gloss": gloss_upper},
            )
        except Exception:
            pass

        nlp_start = time.perf_counter()
        nlp_result = await self._call_nlp_with_retry(
            gloss_upper, request_id
        )
        nlp_latency = (time.perf_counter() - nlp_start) * 1000

        text = nlp_result.text

        logger.info(
            "nlp_result",
            extra={
                "request_id": request_id,
                "gloss": gloss_upper,
                "text": text,
                "latency_ms": round(nlp_latency, 2),
            },
        )

        total_latency = (time.perf_counter() - overall_start) * 1000

        try:
            await self._emit_event(
                "translation_received",
                {
                    "request_id": request_id,
                    "gloss": gloss_upper,
                    "text": text,
                },
            )
        except Exception:
            pass

        return TranslationPipelineResult(
            gloss=gloss_upper,
            text=text,
            success=True,
            cv_latency_ms=round(cv_latency, 2),
            nlp_latency_ms=round(nlp_latency, 2),
            total_latency_ms=round(total_latency, 2),
            cv_retries=cv_retries,
            nlp_retries=nlp_retries,
        )

    async def _call_cv_with_retry(
        self, video_chunk: bytes, request_id: str
    ) -> CVResponse:
        timeout = self.config.cv_timeout

        async def _cv_flow():
            await self.cv_client.send_video_chunk(video_chunk)
            return await self.cv_client.receive_gloss()

        try:
            result = await self.retry_handler.execute(
                _cv_flow,
                service_name="CV",
                timeout=timeout,
            )
            if isinstance(result, CVResponse):
                return result
            if isinstance(result, dict):
                gloss = result.get("gloss", "")
                if not gloss:
                    raise ValueError("CV returned empty gloss")
                return CVResponse(gloss=gloss, raw=result)
            return CVResponse(gloss="")
        except Exception as exc:
            logger.error(
                "cv_failed_after_retries",
                extra={
                    "request_id": request_id,
                    "error": str(exc),
                },
            )
            await self._emit_event(
                "translation_error",
                {
                    "request_id": request_id,
                    "stage": "cv",
                    "error": str(exc),
                },
            )
            raise

    async def _call_nlp_with_retry(
        self, gloss: str, request_id: str
    ) -> NLPResponse:
        nlp_retry = RetryHandler(
            max_retries=getattr(settings, "NLP_RETRIES", 3),
            base_delay=0.3,
            max_delay=3.0,
        )
        timeout = self.config.nlp_timeout

        try:
            result = await nlp_retry.execute(
                lambda: self.nlp_client.translate_gloss(gloss),
                service_name="NLP",
                timeout=timeout,
            )
            if isinstance(result, NLPResponse):
                return result
            if isinstance(result, dict):
                text = result.get("text", "")
                if not text:
                    raise ValueError("NLP returned empty text")
                return NLPResponse(text=text, raw=result)
            return NLPResponse(text="")
        except Exception as exc:
            logger.error(
                "nlp_failed_after_retries",
                extra={
                    "request_id": request_id,
                    "gloss": gloss,
                    "error": str(exc),
                },
            )
            await self._emit_event(
                "translation_error",
                {
                    "request_id": request_id,
                    "stage": "nlp",
                    "gloss": gloss,
                    "error": str(exc),
                },
            )
            raise

    async def _emit_event(self, event_type: str, data: dict):
        if self.event_callback:
            payload = {"type": event_type, **data}
            await self.event_callback(payload)
