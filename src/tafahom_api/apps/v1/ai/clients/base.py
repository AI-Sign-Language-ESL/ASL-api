import httpx
from django.conf import settings


class BaseAIClient:
    base_url: str = None

    def __init__(self):
        if not self.base_url:
            raise ValueError("base_url must be defined in client")
        self.base_url = self.base_url.rstrip("/")
        self.timeout = settings.AI_TIMEOUT

    async def _post_json(self, path: str, json: dict):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}{path}", json=json)
            resp.raise_for_status()
            return resp.json()

    async def _post_file(self, path: str, files: dict):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}{path}", files=files)
            resp.raise_for_status()
            return resp.json()
