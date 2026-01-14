from django.conf import settings
from .base import BaseAIClient


class ComputerVisionClient(BaseAIClient):
    base_url = settings.AI_CV_BASE_URL

    async def sign_to_gloss(self, frames: list[str]):
        return await self._post_json("/", {"frames": frames})
