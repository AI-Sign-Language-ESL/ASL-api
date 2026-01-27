from typing import List
from django.conf import settings
import httpx


class ComputerVisionClient:
    def __init__(self):
        self.base_url = settings.AI_CV_BASE_URL
        self.timeout = settings.AI_TIMEOUT

    async def sign_to_gloss(self, frames: List[str]) -> dict:
        if not frames:
            raise ValueError("No frames provided")

        payload = {
            "frames": frames,  # base64-encoded JPEG frames
        }

        headers = {
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/predict",
                json=payload,
                headers=headers,
            )

            response.raise_for_status()
            return response.json()
