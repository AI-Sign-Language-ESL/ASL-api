import asyncio
import logging
import re
import time
import uuid
from typing import Dict, Any, List

from django.conf import settings

from tafahom_api.apps.v1.ai.clients.computer_vision_client import ComputerVisionClient
from tafahom_api.apps.v1.ai.clients.text_to_gloss_client import TextToGlossClient
from tafahom_api.apps.v1.ai.clients.gloss_to_text_client import GlossToTextClient
from tafahom_api.apps.v1.ai.clients.text_to_speech_client import TextToSpeechClient
from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
from tafahom_api.apps.v1.ai.utils.ensure_wav import ensure_wav

from tafahom_api.apps.v1.translation.services.sign_video_service import (
    generate_sign_video_from_gloss,
)
from tafahom_api.apps.v1.translation.sign_map import SIGN_MAP, SYNONYM_MAP

logger = logging.getLogger("translation")


# =====================================================
# Arabic helpers
# =====================================================
def normalize_arabic(text: str) -> str:
    text = re.sub("[إأآا]", "ا", text)
    text = re.sub("ى", "ي", text)
    text = re.sub("ؤ", "و", text)
    text = re.sub("ئ", "ي", text)
    text = re.sub("ة", "ه", text)
    text = re.sub("[ًٌٍَُِّْ]", "", text)
    return text.strip()


# =====================================================
# Pipeline Service
# =====================================================
class TranslationPipelineService:
    """
    Central orchestration layer for all translation pipelines.
    """

    _cv_client = ComputerVisionClient()
    _text_to_gloss_client = TextToGlossClient()
    _gloss_to_text_client = GlossToTextClient()
    _tts_client = TextToSpeechClient()
    _stt_client = SpeechToTextClient()

    # -------------------------------------------------
    @staticmethod
    async def _with_timeout(coro):
        return await asyncio.wait_for(coro, timeout=settings.AI_TIMEOUT)

    # -------------------------------------------------
    @staticmethod
    def _extract_gloss(nlp_resp: Dict[str, Any]) -> List[str]:
        """
        Convert NLP output into SIGN_MAP-compatible gloss tokens.
        """

        raw = (
            nlp_resp.get("gloss_translation")
            or nlp_resp.get("gloss")
            or nlp_resp.get("text")
        )

        if not raw:
            raise ValueError("NLP returned empty output")

        normalized = normalize_arabic(str(raw))
        tokens = normalized.split()

        resolved: List[str] = []

        for token in tokens:
            if token in SIGN_MAP:
                resolved.append(token)
                continue

            mapped = SYNONYM_MAP.get(token)
            if mapped and mapped in SIGN_MAP:
                resolved.append(mapped)

        # 🚫 CRITICAL FIX — NO FALLBACK
        if not resolved:
            raise ValueError(f"No supported sign tokens found for input: {raw}")

        return resolved

    # =================================================
    # TEXT → SIGN
    # =================================================
    @classmethod
    async def text_to_sign(cls, text: str) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        nlp_resp = await cls._with_timeout(
            cls._text_to_gloss_client.text_to_gloss(text)
        )

        gloss = cls._extract_gloss(nlp_resp)
        video_url = generate_sign_video_from_gloss(gloss)

        logger.info(
            "text_to_sign_success",
            extra={
                "request_id": request_id,
                "gloss": gloss,
                "duration_ms": (time.perf_counter() - start) * 1000,
            },
        )

        return {
            "gloss": gloss,
            "video": video_url,
        }

    # =================================================
    # VOICE → SIGN
    # =================================================
    @classmethod
    async def voice_to_sign(cls, uploaded_file) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        wav_file = ensure_wav(uploaded_file)

        stt_resp = await cls._with_timeout(cls._stt_client.speech_to_text(wav_file))

        text = stt_resp.get("text")
        if not text:
            raise ValueError("STT returned empty text")

        nlp_resp = await cls._with_timeout(
            cls._text_to_gloss_client.text_to_gloss(text)
        )

        gloss = cls._extract_gloss(nlp_resp)
        video_url = generate_sign_video_from_gloss(gloss)

        logger.info(
            "voice_to_sign_success",
            extra={
                "request_id": request_id,
                "gloss": gloss,
                "duration_ms": (time.perf_counter() - start) * 1000,
            },
        )

        return {
            "text": text,
            "gloss": gloss,
            "video": video_url,
        }
