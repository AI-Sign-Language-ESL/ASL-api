import tempfile
import subprocess
from django.conf import settings
from .base import BaseAIClient


class SpeechToTextClient(BaseAIClient):
    base_url = settings.AI_STT_BASE_URL

    async def speech_to_text(self, audio_file):
        # 1️⃣ Write uploaded file to disk
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as raw:
            for chunk in audio_file.chunks():
                raw.write(chunk)
            raw_path = raw.name

        # 2️⃣ Normalize audio for Whisper
        with tempfile.NamedTemporaryFile(suffix=".wav") as fixed:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    raw_path,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-sample_fmt",
                    "s16",
                    fixed.name,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            fixed.seek(0)

            # 🔥 THIS IS THE CRITICAL LINE
            result = await self._post_file(
                "/predict",
                files={"file": fixed},
            )

        # 3️⃣ GUARANTEE text extraction
        text = result.get("text", "").strip()

        return {"text": text}
