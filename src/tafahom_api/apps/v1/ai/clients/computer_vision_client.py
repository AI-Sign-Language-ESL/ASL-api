import time
from typing import List

import httpx
from django.conf import settings

from .models import AIRequest


class ComputerVisionClient:
    def __init__(self, user=None):
        self.base_url = settings.AI_CV_BASE_URL.rstrip("/")
        self.timeout = settings.AI_TIMEOUT
        self.user = user

    async def sign_to_gloss(self, frames: List[str]) -> dict:
        start_time = time.time()

        if not frames:
            raise ValueError("No frames provided")

        payload = {
            "frames": frames,  # base64-encoded JPEG frames
        }

        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/predict",
                    json=payload,
                    headers=headers,
                )

            latency_ms = int((time.time() - start_time) * 1000)

            # Raise HTTP errors (4xx / 5xx)
            response.raise_for_status()

            data = response.json()

            # 🔍 DEBUG LOGGING
            print("========== AI DEBUG ==========")
            print("Frames count:", len(frames))
            print("Response status:", response.status_code)
            print("AI raw response:", data)
            print("================================")

            # ❌ Validate response structure
            if not data or "gloss" not in data:
                raise ValueError(f"Invalid AI response format: {data}")

            gloss_tokens = data["gloss"]

            if not isinstance(gloss_tokens, list) or not gloss_tokens:
                raise ValueError(f"Empty or invalid gloss list: {gloss_tokens}")

            # ✅ Normalize tokens (IMPORTANT)
            gloss_tokens = [token.upper().strip() for token in gloss_tokens]

            # ✅ Log success
            AIRequest.objects.create(
                user=self.user,
                service="cv",
                endpoint="/predict",
                status="success",
                latency_ms=latency_ms,
            )

            return {"gloss": gloss_tokens}

        except httpx.TimeoutException as e:
            latency_ms = int((time.time() - start_time) * 1000)

            AIRequest.objects.create(
                user=self.user,
                service="cv",
                endpoint="/predict",
                status="timeout",
                latency_ms=latency_ms,
                error_message=str(e),
            )

            print("❌ AI TIMEOUT:", str(e))
            raise

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            AIRequest.objects.create(
                user=self.user,
                service="cv",
                endpoint="/predict",
                status="failed",
                latency_ms=latency_ms,
                error_message=str(e),
            )

            print("❌ AI ERROR:", str(e))
            raise
