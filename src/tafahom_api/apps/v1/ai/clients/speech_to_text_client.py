import tempfile
import subprocess
from django.conf import settings
from .base import BaseAIClient


class SpeechToTextClient(BaseAIClient):
    base_url = settings.AI_STT_BASE_URL

    async def speech_to_text(self, audio_file):
        # Convert incoming upload to REAL wav file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fixed:

            input_path = audio_file.file.name if hasattr(audio_file, "file") else None

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_path or "/dev/stdin",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-sample_fmt",
                    "s16",
                    fixed.name,
                ],
                stdin=audio_file.file,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

        # 🔥 SEND WITH EXPLICIT FILENAME + MIME TYPE
        with open(fixed.name, "rb") as wav:
            return await self._post_file(
                "/",
                files={"file": ("audio.wav", wav, "audio/wav")},
            )
