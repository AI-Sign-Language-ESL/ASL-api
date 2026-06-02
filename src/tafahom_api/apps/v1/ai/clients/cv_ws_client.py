import asyncio
import json
import logging
import time
from typing import Optional

import httpx
from django.conf import settings

from tafahom_api.apps.v1.translation.services.dtos import CVResponse

logger = logging.getLogger(__name__)


class CVWebSocketClient:
    """
    WebSocket-based client for Computer Vision model.

    Sends buffered video chunks via WebSocket and receives gloss text.
    Falls back to the HTTP-based ComputerVisionClient if WS is unavailable.
    """

    def __init__(
        self,
        ws_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.ws_url = ws_url or getattr(settings, "CV_MODEL_WS_URL", None)
        self.timeout = timeout or getattr(settings, "CV_WS_TIMEOUT", 30)

    async def send_video_chunk(self, video_chunk: bytes) -> CVResponse:
        """
        Send a video frame chunk to the CV model via WebSocket and return gloss.

        Args:
            video_chunk: Binary video frame data (JPEG or raw bytes).

        Returns:
            CVResponse with gloss text.

        Raises:
            ConnectionError: If WebSocket connection fails.
            TimeoutError: If no response within timeout.
            ValueError: If response is malformed.
        """
        if not self.ws_url:
            return await self._http_fallback(video_chunk)

        try:
            return await self._ws_send(video_chunk)
        except (ConnectionError, asyncio.TimeoutError, ValueError) as exc:
            logger.warning(
                "CV WebSocket failed (%s), falling back to HTTP", str(exc)
            )
            return await self._http_fallback(video_chunk)

    async def _ws_send(self, video_chunk: bytes) -> CVResponse:
        import websockets

        start = time.perf_counter()
        try:
            async with websockets.connect(
                self.ws_url,
                max_size=10 * 1024 * 1024,
                open_timeout=10,
            ) as ws:
                await ws.send(video_chunk)
                response_raw = await asyncio.wait_for(
                    ws.recv(), timeout=self.timeout
                )

                if isinstance(response_raw, bytes):
                    data = json.loads(response_raw.decode("utf-8"))
                else:
                    data = json.loads(response_raw)

                gloss = data.get("gloss", "")
                if not gloss:
                    raise ValueError("CV model returned empty gloss")

                latency = (time.perf_counter() - start) * 1000
                logger.info(
                    "cv_ws_success",
                    extra={
                        "gloss": gloss,
                        "latency_ms": round(latency, 2),
                    },
                )

                return CVResponse(gloss=gloss, raw=data)

        except websockets.exceptions.ConnectionClosed as exc:
            raise ConnectionError(f"WebSocket closed unexpectedly: {exc}") from exc
        except asyncio.TimeoutError:
            raise TimeoutError("CV model did not respond in time") from None

    async def _http_fallback(self, video_chunk: bytes) -> CVResponse:
        from tafahom_api.apps.v1.ai.clients.computer_vision_client import (
            ComputerVisionClient,
        )

        http_client = ComputerVisionClient()
        frames = [video_chunk.hex()]

        try:
            result = await http_client.sign_to_gloss(frames)
            gloss = result.get("gloss", "")
            if not gloss:
                raise ValueError("CV HTTP fallback returned empty gloss")
            return CVResponse(gloss=gloss, raw=result)
        except Exception as exc:
            logger.error("CV HTTP fallback also failed: %s", str(exc))
            raise
