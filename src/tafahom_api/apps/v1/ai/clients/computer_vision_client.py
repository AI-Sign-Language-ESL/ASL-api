# ai/clients/computer_vision.py
from .base import BaseAIClient

class ComputerVisionClient(BaseAIClient):
    async def sign_to_gloss(self, frames: list[str]):
        return await self._post(
            "/cv/sign-to-gloss",
            {"frames": frames}
        )
