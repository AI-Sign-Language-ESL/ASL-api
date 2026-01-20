import asyncio
import logging
import uuid
from typing import Any, Dict, List, Union

from django.conf import settings

from tafahom_api.apps.v1.ai.clients.computer_vision_client import ComputerVisionClient
from tafahom_api.apps.v1.ai.clients.text_to_gloss_client import TextToGlossClient
from tafahom_api.apps.v1.ai.clients.text_to_speech_client import TextToSpeechClient
from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
from tafahom_api.apps.v1.ai.utils.ensure_wav import ensure_wav
from tafahom_api.apps.v1.translation.sign_map import SIGN_MAP

logger = logging.getLogger("translation")


class TranslationPipelineService:
    """
    FINAL production pipeline:
    - CV returns TEXT
    - NLP returns gloss_translation (sentence)
    - We split + filter by SIGN_MAP
    """

    _cv_client = ComputerVisionClient()
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
    def _require(value: Any, name: str):
        if value is None:
            raise ValueError(f"{name} is None")
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{name} is empty")
        if isinstance(value, list) and not value:
            raise ValueError(f"{name} is empty")

    @staticmethod
    def _extract_text(resp: Any) -> str:
        """
        Safely extract text from any AI response
        """
        if isinstance(resp, dict):
            text = resp.get("text") or resp.get("output")
        else:
            text = resp

        if not text:
            raise ValueError("Text not returned from model")

        return str(text)

    @staticmethod
    def _extract_gloss(resp: Dict[str, Any]) -> List[str]:
        """
        NLP response examples:
        { "gloss_translation": "لا حرائق فقط إسعاف وصول" }
        """
        raw = (
            resp.get("gloss_translation")
            or resp.get("gloss")
            or resp.get("output")
            or resp.get("text")
        )

        if raw is None:
            logger.error("NLP response missing gloss: %s", resp)
            raise ValueError("Gloss not returned from NLP model")

        tokens = str(raw).split()

        # 🔥 Only keep signs we actually have videos for
        filtered = [t for t in tokens if t in SIGN_MAP]

        if not filtered:
            raise ValueError("No supported sign tokens found")

        return filtered

    # --------------------------------------------------
    # TEXT → SIGN
    # --------------------------------------------------

    @classmethod
    async def text_to_sign(cls, text: str) -> Dict[str, List[str]]:
        request_id = str(uuid.uuid4())

        try:
            cls._require(text, "text")

            nlp_resp = await cls._with_timeout(
                cls._text_to_gloss_client.text_to_gloss(text)
            )

            gloss = cls._extract_gloss(nlp_resp)
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

            stt_resp = await cls._with_timeout(
                cls._stt_client.speech_to_text(audio_file)
            )

            text = cls._extract_text(stt_resp)

            nlp_resp = await cls._with_timeout(
                cls._text_to_gloss_client.text_to_gloss(text)
            )

            gloss = cls._extract_gloss(nlp_resp)
            return {"text": text, "gloss": gloss}

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={"pipeline": "voice_to_sign", "request_id": request_id},
            )
            raise RuntimeError("Voice → Sign pipeline failed") from exc

    # --------------------------------------------------
    # SIGN → TEXT (CV RETURNS TEXT)
    # --------------------------------------------------

    @classmethod
    async def sign_to_text(cls, frames: List[str]) -> Dict[str, str]:
        """
        frames = list of base64 strings
        CV already returns TEXT
        """
        request_id = str(uuid.uuid4())

        try:
            cls._require(frames, "frames")

            cv_resp = await cls._with_timeout(cls._cv_client.sign_to_gloss(frames))

            text = cls._extract_text(cv_resp)
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
            cls._require(frames, "frames")

            cv_resp = await cls._with_timeout(cls._cv_client.sign_to_gloss(frames))

            text = cls._extract_text(cv_resp)

            audio = await cls._with_timeout(cls._tts_client.text_to_speech(text))

            cls._require(audio, "audio")
            return {"text": text, "audio": audio}

        except Exception as exc:
            logger.exception(
                "pipeline_failed",
                extra={"pipeline": "sign_to_voice", "request_id": request_id},
            )
            raise RuntimeError("Sign → Voice pipeline failed") from exc
