# text_to_gloss_client.py
from django.conf import settings
from .base import BaseAIClient


class TextToGlossClient(BaseAIClient):
    base_url = settings.AI_TEXT_TO_GLOSS_BASE_URL

    async def text_to_gloss(self, text: str):
        return await self._post_json("/generate", {"text": text})
