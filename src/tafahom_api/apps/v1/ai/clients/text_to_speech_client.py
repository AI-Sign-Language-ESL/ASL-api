import httpx
from django.conf import settings
from .base import BaseAIClient


class TextToSpeechClient(BaseAIClient):
    """
    ElevenLabs async Text-to-Speech client.

    - Base URL is env-driven (AI_TTS_BASE_URL)
    - Voice ID is runtime (NOT in env)
    - Fully async, timeout-safe
    """

    base_url = settings.AI_TTS_BASE_URL

    async def text_to_speech(
        self,
        text: str,
        *,
        voice_id: str = "Os2frcqCuUz8b9F93RuI",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> bytes:
        if not text or not text.strip():
            raise ValueError("Text must not be empty")

        headers = {
            "xi-api-key": settings.ELEVEN_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/text-to-speech/{voice_id}",
                json=payload,
                headers=headers,
            )

            response.raise_for_status()
            return response.content
