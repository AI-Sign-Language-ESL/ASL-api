import httpx
import json
from django.conf import settings
from .base import BaseAIClient


class SpeechToTextClient(BaseAIClient):
    base_url = settings.AI_STT_BASE_URL

    async def speech_to_text(self, audio_file):
        filename = getattr(audio_file, "name", "")
        if not filename.lower().endswith(".wav"):
            raise ValueError("Speech-to-text only accepts .wav audio files")

        try:
            response = await self._post_file(
                "/predict",
                files={"file": audio_file},
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 405):
                response = await self._post_file(
                    "/",
                    files={"file": audio_file},
                )
            else:
                raise

        # 🔥 FORCE NORMALIZATION (NO ASSUMPTIONS)
        if isinstance(response, httpx.Response):
            data = response.json()
        elif isinstance(response, str):
            data = json.loads(response)
        elif isinstance(response, dict):
            data = response
        else:
            raise ValueError(f"Unknown STT response type: {type(response)}")

        if "text" not in data:
            raise ValueError(f"STT response missing text: {data}")

        return data
