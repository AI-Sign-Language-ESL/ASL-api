import tempfile
import subprocess
import os
from django.conf import settings
from .base import BaseAIClient


class SpeechToTextClient(BaseAIClient):
    base_url = settings.AI_STT_BASE_URL

    async def speech_to_text(self, audio_file):
        """
        Converts uploaded audio to PCM16 WAV (mono, 16kHz)
        and sends it to the STT service with REQUIRED params.
        """

        # -------------------------------------------------
        # 1️⃣ Save uploaded audio bytes to temp file
        # -------------------------------------------------
        with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as raw:
            raw.write(audio_file.read())
            raw.flush()
            raw_path = raw.name

        # -------------------------------------------------
        # 2️⃣ Convert to clean WAV (PCM16, mono, 16kHz)
        # -------------------------------------------------
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav:
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
                    wav.name,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            wav_path = wav.name
            print("FINAL WAV SIZE:", os.path.getsize(wav_path))

        # -------------------------------------------------
        # 3️⃣ Send WAV to STT service (FIXED)
        # -------------------------------------------------
        with open(wav_path, "rb") as f:
            return await self._post_file(
                "/",
                files={
                    "file": (
                        "audio.wav",  # ✅ filename REQUIRED
                        f,  # ✅ file bytes
                        "audio/wav",  # ✅ MIME type
                    ),
                },
                data={
                    "language": "ar",  # 🔥 REQUIRED FOR ARABIC
                    "task": "transcribe",  # 🔥 REQUIRED FOR WHISPER-LIKE MODELS
                },
            )
