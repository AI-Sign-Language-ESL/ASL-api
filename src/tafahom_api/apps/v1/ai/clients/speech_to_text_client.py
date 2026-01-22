import tempfile
import subprocess
from django.conf import settings
from .base import BaseAIClient


class SpeechToTextClient(BaseAIClient):
    base_url = settings.AI_STT_BASE_URL

    async def speech_to_text(self, audio_file):
        # 1️⃣ Write uploaded audio bytes to temp file
        with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as raw:
            raw.write(audio_file.read())
            raw.flush()
            raw_path = raw.name

        # 2️⃣ Convert to clean WAV (PCM16, mono, 16kHz)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav:
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
                    wav.name,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            wav_path = wav.name

        # 3️⃣ Send WAV bytes properly
        with open(wav_path, "rb") as f:
            return await self._post_file(
                "/",
                files={
                    "file": (
                        "audio.wav",  # ✅ filename REQUIRED
                        f,  # ✅ bytes
                        "audio/wav",  # ✅ MIME type
                    )
                },
            )
