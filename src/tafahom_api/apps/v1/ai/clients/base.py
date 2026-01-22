import httpx


class BaseAIClient:
    base_url: str

    async def _post_file(self, path: str, files: dict, data: dict | None = None):
        """
        Send multipart/form-data with optional extra fields (e.g. language, task).
        """
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                files=files,
                data=data,
            )

        # ❌ DO NOT raise here — let caller handle fallbacks
        if response.status_code >= 500:
            response.raise_for_status()

        try:
            return response.json()
        except Exception:
            return {
                "error": "invalid_json",
                "raw": response.text,
                "status": response.status_code,
            }
