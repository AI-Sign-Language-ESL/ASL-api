import httpx


class BaseAIClient:
    base_url: str

    async def _post_file(self, path: str, files: dict):
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, files=files)

        response.raise_for_status()

        # 🔥 CRITICAL: RETURN FULL JSON, NOT TEXT, NOT PARTIAL
        try:
            return response.json()
        except Exception:
            raise ValueError(f"Invalid JSON from AI service: {response.text}")
