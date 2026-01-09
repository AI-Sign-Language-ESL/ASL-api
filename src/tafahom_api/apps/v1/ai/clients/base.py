# ai/clients/base.py
import httpx
from django.conf import settings

class BaseAIClient:
    def __init__(self):
        self.base_url = settings.AI_BASE_URL
        self.timeout = settings.AI_TIMEOUT

    async def _post(self, path: str, json: dict):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}{path}",
                json=json,
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}"
                }
            )
            resp.raise_for_status()
            return resp.json()
