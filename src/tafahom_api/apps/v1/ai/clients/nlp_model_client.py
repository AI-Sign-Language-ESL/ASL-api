import logging
from typing import Optional

from django.conf import settings

from tafahom_api.apps.v1.ai.clients.base import BaseAIClient
from tafahom_api.apps.v1.translation.services.dtos import NLPResponse

logger = logging.getLogger(__name__)


class NLPModelClient(BaseAIClient):
    """
    Client for the NLP translation service.

    Sends gloss text and receives Arabic text translation.
    Uses HTTP POST to the configured NLP endpoint.

    Endpoint: POST /translate
    Request:  {"gloss": "HELLO HOW ARE YOU"}
    Response: {"text": "مرحباً كيف حالك"}
    """

    base_url = getattr(settings, "AI_GLOSS_TO_TEXT_BASE_URL", "")

    def __init__(self, timeout: Optional[int] = None):
        self.request_timeout = timeout or getattr(
            settings, "NLP_REQUEST_TIMEOUT", 30
        )

    async def translate_gloss(self, gloss: str) -> NLPResponse:
        if not gloss or not gloss.strip():
            raise ValueError("Gloss text must not be empty")

        result = await self._post_json(
            "/translate",
            {"gloss": gloss.strip()},
        )

        text = ""
        if isinstance(result, dict):
            text = result.get("text", "") or result.get("translation", "")

        if not text:
            logger.warning("NLP returned empty text for gloss: %s", gloss)
            raise ValueError("NLP service returned empty translation")

        logger.info(
            "nlp_translate_success",
            extra={
                "gloss": gloss,
                "text": text,
            },
        )

        return NLPResponse(text=text, raw=result)
