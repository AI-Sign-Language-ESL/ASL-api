# ai/clients/speech.py
from .base import BaseAIClient

class SpeechClient(BaseAIClient):
    async def text_to_speech(self, text: str, voice="ar-EG"):
        return await self._post(
            "/speech/tts",
            {"text": text, "voice": voice}
        )
