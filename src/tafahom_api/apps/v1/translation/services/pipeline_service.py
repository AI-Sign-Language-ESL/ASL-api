import asyncio
import logging
import time
import uuid
from typing import List, Dict, Union

from django.conf import settings

from tafahom_api.apps.v1.ai.clients.computer_vision_client import ComputerVisionClient
from tafahom_api.apps.v1.ai.clients.gloss_to_text_client import GlossToTextClient
from tafahom_api.apps.v1.ai.clients.text_to_gloss_client import TextToGlossClient
from tafahom_api.apps.v1.ai.clients.text_to_speech_client import TextToSpeechClient
from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
from tafahom_api.apps.v1.ai.utils.ensure_wav import ensure_wav

logger = logging.getLogger("translation")


class TranslationPipelineService:
    """
    Production-grade AI orchestration layer.
    Handles logic, timeouts, and logging for AI model chains.
    """

    # --------------------------------------------------
    # Shared clients (singletons)
    # --------------------------------------------------
    _cv_client = ComputerVisionClient()
    _gloss_to_text_client = GlossToTextClient()
    _text_to_gloss_client = TextToGlossClient()
    _tts_client = TextToSpeechClient()
    _stt_client = SpeechToTextClient()

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------
    @staticmethod
    async def _with_timeout(coro):
        return await asyncio.wait_for(coro, timeout=settings.AI_TIMEOUT)

    @staticmethod
    def _validate_non_empty(value, name: str):
        if value is None:
            raise ValueError(f"{name} is None")

        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{name} is empty or whitespace")

        if hasattr(value, "__len__") and len(value) == 0:
            raise ValueError(f"{name} is empty")

        return value

    @staticmethod
    def _ensure_list(value: Union[str, List[str]]) -> List[str]:
        """Runtime safety: ensures gloss is always a list."""
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return value
        return [str(value)]

    @staticmethod
    def _log_stage(stage: str, start: float, request_id: str):
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "pipeline_stage_completed",
            extra={
                "stage": stage,
                "request_id": request_id,
                "duration_ms": duration,
            },
        )

    # --------------------------------------------------
    # PIPELINES
    # --------------------------------------------------

    @classmethod
    async def sign_to_text(cls, frames: List[bytes]) -> Dict[str, str]:
        request_id = str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        try:
            # -------- CV --------
            t = time.perf_counter()
            cv_resp = await cls._with_timeout(cls._cv_client.sign_to_gloss(frames))

            # Safe extraction
            raw_gloss = cv_resp.get("gloss") if isinstance(cv_resp, dict) else cv_resp
            cls._validate_non_empty(raw_gloss, "gloss")

            # Type safety fix
            gloss = cls._ensure_list(raw_gloss)
            cls._log_stage("cv.sign_to_gloss", t, request_id)

            # -------- NLP --------
            t = time.perf_counter()
            nlp_resp = await cls._with_timeout(
                cls._gloss_to_text_client.gloss_to_text(gloss)
            )
            raw_text = nlp_resp.get("text") if isinstance(nlp_resp, dict) else nlp_resp
            cls._validate_non_empty(raw_text, "text")

            text = str(raw_text)
            cls._log_stage("nlp.gloss_to_text", t, request_id)

            logger.info(
                "pipeline_completed",
                extra={
                    "pipeline": "sign_to_text",
                    "request_id": request_id,
                    "total_ms": (time.perf_counter() - pipeline_start) * 1000,
                },
            )

            return {"text": text}

        except asyncio.TimeoutError:
            logger.warning(
                "pipeline_timeout",
                extra={"pipeline": "sign_to_text", "request_id": request_id},
            )
            raise RuntimeError("AI pipeline timeout")

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={"pipeline": "sign_to_text", "request_id": request_id},
            )
            raise RuntimeError("AI pipeline failed") from exc

    # --------------------------------------------------

    @classmethod
    async def sign_to_voice(cls, frames: List[bytes]) -> Dict[str, str]:
        request_id = str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        try:
            # -------- CV --------
            t = time.perf_counter()
            cv_resp = await cls._with_timeout(cls._cv_client.sign_to_gloss(frames))

            raw_gloss = cv_resp.get("gloss") if isinstance(cv_resp, dict) else cv_resp
            cls._validate_non_empty(raw_gloss, "gloss")

            gloss = cls._ensure_list(raw_gloss)
            cls._log_stage("cv.sign_to_gloss", t, request_id)

            # -------- NLP --------
            t = time.perf_counter()
            nlp_resp = await cls._with_timeout(
                cls._gloss_to_text_client.gloss_to_text(gloss)
            )
            raw_text = nlp_resp.get("text") if isinstance(nlp_resp, dict) else nlp_resp
            cls._validate_non_empty(raw_text, "text")

            text = str(raw_text)
            cls._log_stage("nlp.gloss_to_text", t, request_id)

            # -------- TTS --------
            t = time.perf_counter()
            audio = await cls._with_timeout(cls._tts_client.text_to_speech(text))
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

            return {"text": text, "audio": audio}

        except asyncio.TimeoutError:
            logger.warning(
                "pipeline_timeout",
                extra={"pipeline": "sign_to_voice", "request_id": request_id},
            )
            raise RuntimeError("AI pipeline timeout")

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={"pipeline": "sign_to_voice", "request_id": request_id},
            )
            raise RuntimeError("AI pipeline failed") from exc

    # --------------------------------------------------

    @classmethod
    async def text_to_sign(cls, text: str) -> Dict[str, List[str]]:
        request_id = str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        try:
            cls._validate_non_empty(text, "text")

            t = time.perf_counter()
            nlp_resp = await cls._with_timeout(
                cls._text_to_gloss_client.text_to_gloss(text)
            )
            raw_gloss = (
                nlp_resp.get("gloss") if isinstance(nlp_resp, dict) else nlp_resp
            )
            cls._validate_non_empty(raw_gloss, "gloss")

            gloss = cls._ensure_list(raw_gloss)
            cls._log_stage("nlp.text_to_gloss", t, request_id)

            logger.info(
                "pipeline_completed",
                extra={
                    "pipeline": "text_to_sign",
                    "request_id": request_id,
                    "total_ms": (time.perf_counter() - pipeline_start) * 1000,
                },
            )

            return {"gloss": gloss}

        except Exception as exc:
            logger.exception("pipeline_failed", extra={"pipeline": "text_to_sign"})
            raise

    # --------------------------------------------------

    @classmethod
    async def voice_to_sign(cls, uploaded_file) -> Dict[str, object]:
        request_id = str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        try:
            audio_file = ensure_wav(uploaded_file)

            # -------- STT --------
            t = time.perf_counter()
            stt_resp = await cls._with_timeout(
                cls._stt_client.speech_to_text(audio_file)
            )
            raw_text = stt_resp.get("text") if isinstance(stt_resp, dict) else stt_resp
            cls._validate_non_empty(raw_text, "text")

            text = str(raw_text)
            cls._log_stage("speech.speech_to_text", t, request_id)

            # -------- NLP --------
            t = time.perf_counter()
            nlp_resp = await cls._with_timeout(
                cls._text_to_gloss_client.text_to_gloss(text)
            )
            raw_gloss = (
                nlp_resp.get("gloss") if isinstance(nlp_resp, dict) else nlp_resp
            )
            cls._validate_non_empty(raw_gloss, "gloss")

            gloss = cls._ensure_list(raw_gloss)
            cls._log_stage("nlp.text_to_gloss", t, request_id)

            return {"text": text, "gloss": gloss}

        except Exception as exc:
            logger.exception("pipeline_failed", extra={"pipeline": "voice_to_sign"})
            raise
