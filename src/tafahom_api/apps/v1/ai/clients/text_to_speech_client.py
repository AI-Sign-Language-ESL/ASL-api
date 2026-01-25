import httpx
from django.conf import settings


class TextToSpeechClient:
    def __init__(self):
        self.base_url = settings.AI_TTS_BASE_URL.rstrip("/")
        self.timeout = 60.0  # 🔥 FIXED (explicit timeout)

    async def text_to_speech(self, text: str) -> bytes:
        if not text or not text.strip():
            raise ValueError("Text is empty")

        payload = {
            "text": text.strip(),
            "language": "ar",
        }

        headers = {
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/synthesize",
                json=payload,
                headers=headers,
            )

            response.raise_for_status()

            # ✅ Return raw audio bytes
            return response.content
