import tempfile
import subprocess
from django.conf import settings
from .base import BaseAIClient


class SpeechToTextClient(BaseAIClient):
    base_url = settings.AI_STT_BASE_URL

    async def speech_to_text(self, audio_file):
        # 🔹 Write uploaded file to temp WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as raw:
            for chunk in audio_file.chunks():
                raw.write(chunk)
            raw_path = raw.name

        # 🔹 Convert & normalize
        with tempfile.NamedTemporaryFile(suffix=".wav") as fixed:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    raw_path,
                    "-ac",
                    "1",  # mono
                    "-ar",
                    "16000",  # 16kHz
                    "-sample_fmt",
                    "s16",  # PCM16
                    fixed.name,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            fixed.seek(0)
            result = await self._post_file("/", files={"file": fixed})

        return result
