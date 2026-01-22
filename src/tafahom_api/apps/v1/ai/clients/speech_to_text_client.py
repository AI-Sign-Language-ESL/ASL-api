import httpx
from django.conf import settings
from .base import BaseAIClient


class SpeechToTextClient(BaseAIClient):
    base_url = settings.AI_STT_BASE_URL

    async def speech_to_text(self, audio_file):
        filename = getattr(audio_file, "name", "")
        if not filename.lower().endswith(".wav"):
            raise ValueError("Speech-to-text only accepts .wav audio files")

        response = await self._post_file("/predict", files={"file": audio_file})

        # 🔥 FIX: modal returns {"text": "..."}
        if isinstance(response, dict) and "text" in response:
            return response

        # fallback if modal root endpoint is used
        response = await self._post_file("/", files={"file": audio_file})

        if isinstance(response, dict) and "text" in response:
            return response

        raise ValueError(f"Invalid STT response: {response}")
