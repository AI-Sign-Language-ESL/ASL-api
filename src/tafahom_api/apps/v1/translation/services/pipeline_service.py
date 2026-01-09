import asyncio
import logging
import time
import uuid

from django.conf import settings

from tafahom_api.apps.v1.ai.clients.computer_vision_client import ComputerVisionClient
from tafahom_api.apps.v1.ai.clients.nlp_client import NLPClient
from tafahom_api.apps.v1.ai.clients.speech_client import SpeechClient

logger = logging.getLogger("translation")


class TranslationPipelineService:
    """
    Production-grade AI orchestration layer.

    Guarantees:
    - Global timeout alignment with settings
    - Stage-level timing
    - Strong validation
    - Clean error contracts
    - No transport concerns (WS / HTTP agnostic)
    """

    # --------------------------------------------------
    # Shared clients (singleton-style, reused connections)
    # --------------------------------------------------
    _cv_client = ComputerVisionClient()
    _nlp_client = NLPClient()
    _speech_client = SpeechClient()

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------
    @staticmethod
    async def _with_timeout(coro):
        """
        Single source of truth for timeouts.
        """
        return await asyncio.wait_for(
            coro,
            timeout=settings.PIPELINE_TIMEOUT_SECONDS,
        )

    @staticmethod
    def _validate_non_empty(value, name: str):
        if value is None:
            raise ValueError(f"{name} is None")
        if hasattr(value, "__len__") and len(value) == 0:
            raise ValueError(f"{name} is empty")
        return value

    @staticmethod
    def _log_stage(stage: str, start: float, request_id: str):
        logger.info(
            "pipeline_stage_completed",
            extra={
                "stage": stage,
                "request_id": request_id,
                "duration_ms": (time.perf_counter() - start) * 1000,
            },
        )

    # --------------------------------------------------
    # Public pipeline methods
    # --------------------------------------------------
    @classmethod
    async def sign_to_text(cls, frames):
        request_id = str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        try:
            # ---------------- CV ----------------
            t = time.perf_counter()
            gloss = await cls._with_timeout(cls._cv_client.sign_to_gloss(frames))
            cls._validate_non_empty(gloss, "gloss")
            cls._log_stage("cv.sign_to_gloss", t, request_id)

            # ---------------- NLP ----------------
            t = time.perf_counter()
            text = await cls._with_timeout(cls._nlp_client.gloss_to_text(gloss))
            cls._validate_non_empty(text, "text")
            cls._log_stage("nlp.gloss_to_text", t, request_id)

            logger.info(
                "pipeline_completed",
                extra={
                    "pipeline": "sign_to_text",
                    "request_id": request_id,
                    "total_ms": (time.perf_counter() - pipeline_start) * 1000,
                },
            )

            return text

        except asyncio.TimeoutError:
            logger.warning(
                "pipeline_timeout",
                extra={
                    "pipeline": "sign_to_text",
                    "request_id": request_id,
                },
            )
            raise RuntimeError("AI pipeline timeout")

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={
                    "pipeline": "sign_to_text",
                    "request_id": request_id,
                },
            )
            raise RuntimeError("AI pipeline failed") from exc

    @classmethod
    async def sign_to_voice(cls, frames):
        request_id = str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        try:
            # ---------------- CV ----------------
            t = time.perf_counter()
            gloss = await cls._with_timeout(cls._cv_client.sign_to_gloss(frames))
            cls._validate_non_empty(gloss, "gloss")
            cls._log_stage("cv.sign_to_gloss", t, request_id)

            # ---------------- NLP ----------------
            t = time.perf_counter()
            text = await cls._with_timeout(cls._nlp_client.gloss_to_text(gloss))
            cls._validate_non_empty(text, "text")
            cls._log_stage("nlp.gloss_to_text", t, request_id)

            # ---------------- SPEECH ----------------
            t = time.perf_counter()
            audio = await cls._with_timeout(cls._speech_client.text_to_speech(text))
            cls._validate_non_empty(audio, "audio")
            cls._log_stage("speech.text_to_speech", t, request_id)

            logger.info(
                "pipeline_completed",
                extra={
                    "pipeline": "sign_to_voice",
                    "request_id": request_id,
                    "total_ms": (time.perf_counter() - pipeline_start) * 1000,
                },
            )

            return {
                "text": text,
                "audio": audio,
            }

        except asyncio.TimeoutError:
            logger.warning(
                "pipeline_timeout",
                extra={
                    "pipeline": "sign_to_voice",
                    "request_id": request_id,
                },
            )
            raise RuntimeError("AI pipeline timeout")

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={
                    "pipeline": "sign_to_voice",
                    "request_id": request_id,
                },
            )
            raise RuntimeError("AI pipeline failed") from exc

    @classmethod
    async def text_to_sign(cls, text):
        request_id = str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        try:
            cls._validate_non_empty(text, "text")

            # ---------------- NLP ----------------
            t = time.perf_counter()
            gloss = await cls._with_timeout(cls._nlp_client.text_to_gloss(text))
            cls._validate_non_empty(gloss, "gloss")
            cls._log_stage("nlp.text_to_gloss", t, request_id)

            logger.info(
                "pipeline_completed",
                extra={
                    "pipeline": "text_to_sign",
                    "request_id": request_id,
                    "total_ms": (time.perf_counter() - pipeline_start) * 1000,
                },
            )

            return gloss

        except asyncio.TimeoutError:
            logger.warning(
                "pipeline_timeout",
                extra={
                    "pipeline": "text_to_sign",
                    "request_id": request_id,
                },
            )
            raise RuntimeError("AI pipeline timeout")

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={
                    "pipeline": "text_to_sign",
                    "request_id": request_id,
                },
            )
            raise RuntimeError("AI pipeline failed") from exc

    @classmethod
    async def voice_to_sign(cls, audio):
        request_id = str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        try:
            cls._validate_non_empty(audio, "audio")

            # ---------------- SPEECH ----------------
            t = time.perf_counter()
            text = await cls._with_timeout(cls._speech_client.speech_to_text(audio))
            cls._validate_non_empty(text, "text")
            cls._log_stage("speech.speech_to_text", t, request_id)

            # ---------------- NLP ----------------
            t = time.perf_counter()
            gloss = await cls._with_timeout(cls._nlp_client.text_to_gloss(text))
            cls._validate_non_empty(gloss, "gloss")
            cls._log_stage("nlp.text_to_gloss", t, request_id)

            logger.info(
                "pipeline_completed",
                extra={
                    "pipeline": "voice_to_sign",
                    "request_id": request_id,
                    "total_ms": (time.perf_counter() - pipeline_start) * 1000,
                },
            )

            return gloss

        except asyncio.TimeoutError:
            logger.warning(
                "pipeline_timeout",
                extra={
                    "pipeline": "voice_to_sign",
                    "request_id": request_id,
                },
            )
            raise RuntimeError("AI pipeline timeout")

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={
                    "pipeline": "voice_to_sign",
                    "request_id": request_id,
                },
            )
            raise RuntimeError("AI pipeline failed") from exc
