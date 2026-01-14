# text_to_speech_client.py
from django.conf import settings
from .base import BaseAIClient


class TextToSpeechClient(BaseAIClient):
    base_url = settings.AI_TTS_BASE_URL

    async def text_to_speech(self, text: str):
        return await self._post_json("/", {"text": text})
