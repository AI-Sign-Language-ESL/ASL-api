import tempfile
import subprocess
from django.conf import settings
from .base import BaseAIClient


class SpeechToTextClient(BaseAIClient):
    base_url = settings.AI_STT_BASE_URL

    async def speech_to_text(self, audio_file):
        # 🔥 FORCE CORRECT FORMAT
        with tempfile.NamedTemporaryFile(suffix=".wav") as fixed:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    audio_file.temporary_file_path(),
                    "-ac",
                    "1",  # mono
                    "-ar",
                    "16000",  # 16kHz
                    "-sample_fmt",
                    "s16",  # PCM16
                    fixed.name,
                ],
                check=True,
            )

            fixed.seek(0)

            result = await self._post_file("/", files={"file": fixed})

        if "text" not in result:
            raise ValueError(result)

        return result
