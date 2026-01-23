from django.conf import settings
from .base import BaseAIClient


class TextToGlossClient(BaseAIClient):
    base_url = settings.AI_TEXT_TO_GLOSS_BASE_URL

    async def text_to_gloss(self, text: str):
        if not text or not text.strip():
            raise ValueError("Text is empty")

        payload = {"prompt": text.strip()}  # REQUIRED

        return await self._post_json("/generate", json=payload)
