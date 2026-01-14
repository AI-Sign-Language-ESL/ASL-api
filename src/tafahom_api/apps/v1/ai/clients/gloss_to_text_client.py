# gloss_to_text_client.py
from django.conf import settings
from .base import BaseAIClient


class GlossToTextClient(BaseAIClient):
    base_url = settings.AI_GLOSS_TO_TEXT_BASE_URL

    async def gloss_to_text(self, gloss: list[str]):
        return await self._post_json("/generate", {"gloss": gloss})
