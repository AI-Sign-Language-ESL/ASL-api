import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class TextToSpeechClient:
    """
    Text-to-Speech client.
    POSTs text to AI_TTS_BASE_URL and returns raw audio bytes.
    """

    def __init__(self):
        self.base_url = getattr(settings, "AI_TTS_BASE_URL", "")
        self.timeout = 60.0

    async def text_to_speech(self, text: str) -> bytes | None:
        if not text or not text.strip():
            return None

        if not self.base_url:
            logger.warning("AI_TTS_BASE_URL is not configured.")
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json={"text": text.strip()},
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                return response.content
        except httpx.TimeoutException:
            logger.warning("TTS timed out for text: %r", text[:50])
            return None
        except Exception as e:
            logger.error("TTS error: %s", e)
            return None
