import httpx
from django.conf import settings
from .base import BaseAIClient


class SpeechToTextClient(BaseAIClient):
    base_url = settings.AI_STT_BASE_URL

    async def speech_to_text(self, audio_file):
        # ✅ enforce .wav
        filename = getattr(audio_file, "name", "")
        if not filename.lower().endswith(".wav"):
            raise ValueError("Speech-to-text only accepts .wav audio files")

        try:
            return await self._post_file("/predict", files={"file": audio_file})
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 405):
                return await self._post_file("/", files={"file": audio_file})
            raise
