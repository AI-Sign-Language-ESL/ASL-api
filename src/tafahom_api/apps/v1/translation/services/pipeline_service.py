import asyncio
import logging
import time
import uuid
from typing import List, Dict, Union, Any

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
    Coordinates CV, NLP, and Speech services.
    """

    _cv_client = ComputerVisionClient()
    _gloss_to_text_client = GlossToTextClient()
    _text_to_gloss_client = TextToGlossClient()
    _tts_client = TextToSpeechClient()
    _stt_client = SpeechToTextClient()

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    async def _with_timeout(coro: Any):
        return await asyncio.wait_for(coro, timeout=settings.AI_TIMEOUT)

    @staticmethod
    def _validate_non_empty(value: Any, name: str) -> None:
        if value is None:
            raise ValueError(f"{name} is None")

        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{name} is empty")

        if isinstance(value, list) and not value:
            raise ValueError(f"{name} is empty")

    @staticmethod
    def _ensure_list(value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def _log_stage(stage: str, start: float, request_id: str) -> None:
        logger.info(
            "pipeline_stage_completed",
            extra={
                "stage": stage,
                "request_id": request_id,
                "duration_ms": (time.perf_counter() - start) * 1000,
            },
        )

    # --------------------------------------------------
    # SIGN → TEXT
    # --------------------------------------------------

    @classmethod
    async def sign_to_text(cls, frames: List[str]) -> Dict[str, str]:
        """
        frames: list of base64-encoded frame strings
        """
        request_id = str(uuid.uuid4())

        try:
            cls._validate_non_empty(frames, "frames")

            # CV: Sign → Gloss
            t = time.perf_counter()
            cv_resp = await cls._with_timeout(cls._cv_client.sign_to_gloss(frames))

            raw_gloss = cv_resp.get("gloss")
            cls._validate_non_empty(raw_gloss, "gloss")

            gloss = cls._ensure_list(raw_gloss)
            cls._log_stage("cv.sign_to_gloss", t, request_id)

            # NLP: Gloss → Text
            t = time.perf_counter()
            nlp_resp = await cls._with_timeout(
                cls._gloss_to_text_client.gloss_to_text(gloss)
            )

            raw_text = nlp_resp.get("text")
            cls._validate_non_empty(raw_text, "text")

            text = str(raw_text)
            cls._log_stage("nlp.gloss_to_text", t, request_id)

            return {"text": text}

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={"pipeline": "sign_to_text", "request_id": request_id},
            )
            raise RuntimeError("Sign → Text pipeline failed") from exc

    # --------------------------------------------------
    # SIGN → VOICE
    # --------------------------------------------------

    @classmethod
    async def sign_to_voice(cls, frames: List[str]) -> Dict[str, Union[str, bytes]]:
        request_id = str(uuid.uuid4())

        try:
            cls._validate_non_empty(frames, "frames")

            # CV
            t = time.perf_counter()
            cv_resp = await cls._with_timeout(cls._cv_client.sign_to_gloss(frames))

            raw_gloss = cv_resp.get("gloss")
            cls._validate_non_empty(raw_gloss, "gloss")
            gloss = cls._ensure_list(raw_gloss)
            cls._log_stage("cv.sign_to_gloss", t, request_id)

            # NLP
            t = time.perf_counter()
            nlp_resp = await cls._with_timeout(
                cls._gloss_to_text_client.gloss_to_text(gloss)
            )

            raw_text = nlp_resp.get("text")
            cls._validate_non_empty(raw_text, "text")
            text = str(raw_text)
            cls._log_stage("nlp.gloss_to_text", t, request_id)

            # TTS
            t = time.perf_counter()
            audio = await cls._with_timeout(cls._tts_client.text_to_speech(text))
            cls._validate_non_empty(audio, "audio")
            cls._log_stage("speech.text_to_speech", t, request_id)

            return {"text": text, "audio": audio}

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={"pipeline": "sign_to_voice", "request_id": request_id},
            )
            raise RuntimeError("Sign → Voice pipeline failed") from exc

    # --------------------------------------------------
    # TEXT → SIGN
    # --------------------------------------------------

    @classmethod
    async def text_to_sign(cls, text: str) -> Dict[str, List[str]]:
        request_id = str(uuid.uuid4())

        try:
            cls._validate_non_empty(text, "text")

            t = time.perf_counter()
            nlp_resp = await cls._with_timeout(
                cls._text_to_gloss_client.text_to_gloss(text)
            )

            raw_gloss = nlp_resp.get("gloss")
            cls._validate_non_empty(raw_gloss, "gloss")

            gloss = cls._ensure_list(raw_gloss)
            cls._log_stage("nlp.text_to_gloss", t, request_id)

            return {"gloss": gloss}

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={"pipeline": "text_to_sign", "request_id": request_id},
            )
            raise RuntimeError("Text → Sign pipeline failed") from exc

    # --------------------------------------------------
    # VOICE → SIGN
    # --------------------------------------------------

    @classmethod
    async def voice_to_sign(cls, uploaded_file) -> Dict[str, Union[str, List[str]]]:
        request_id = str(uuid.uuid4())

        try:
            audio_file = ensure_wav(uploaded_file)

            # STT
            t = time.perf_counter()
            stt_resp = await cls._with_timeout(
                cls._stt_client.speech_to_text(audio_file)
            )

            raw_text = stt_resp.get("text")
            cls._validate_non_empty(raw_text, "text")
            text = str(raw_text)
            cls._log_stage("speech.speech_to_text", t, request_id)

            # NLP
            t = time.perf_counter()
            nlp_resp = await cls._with_timeout(
                cls._text_to_gloss_client.text_to_gloss(text)
            )

            raw_gloss = nlp_resp.get("gloss")
            cls._validate_non_empty(raw_gloss, "gloss")
            gloss = cls._ensure_list(raw_gloss)
            cls._log_stage("nlp.text_to_gloss", t, request_id)

            return {"text": text, "gloss": gloss}

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={"pipeline": "voice_to_sign", "request_id": request_id},
            )
            raise RuntimeError("Voice → Sign pipeline failed") from exc
