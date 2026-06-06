import abc
import asyncio
import json
import logging
import time
from typing import Optional

from django.conf import settings

from tafahom_api.apps.v1.translation.services.dtos import CVResponse

logger = logging.getLogger(__name__)


class CVModelClient(abc.ABC):
    """
    Abstract Interface for the Computer Vision model client.
    Ensures the future CV API is pluggable without changing frontend code.
    """

    @abc.abstractmethod
    async def connect(self):
        """Establish connection to the CV model."""
        pass

    @abc.abstractmethod
    async def send_video_chunk(self, video_chunk: bytes):
        """Send a video frame chunk to the CV model."""
        pass

    @abc.abstractmethod
    async def receive_gloss(self) -> CVResponse:
        """Receive the next gloss from the CV model."""
        pass

    @abc.abstractmethod
    async def disconnect(self):
        """Close the connection to the CV model."""
        pass


class CVWebSocketClient(CVModelClient):
    """
    Stateful WebSocket-based client for Computer Vision model.
    Maintains a persistent connection for the duration of the session.
    """

    def __init__(
        self,
        ws_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.ws_url = ws_url or getattr(settings, "CV_MODEL_WS_URL", None)
        self.timeout = timeout or getattr(settings, "CV_WS_TIMEOUT", 30)
        self.ws = None

    async def connect(self):
        if not self.ws_url:
            raise ValueError("CV_MODEL_WS_URL is not set.")
        
        if self.ws:
            return

        import websockets
        try:
            self.ws = await websockets.connect(
                self.ws_url,
                max_size=10 * 1024 * 1024,
                open_timeout=10,
            )
            logger.info("Connected to CV model WebSocket.")
        except Exception as e:
            logger.error(f"Failed to connect to CV model WebSocket: {e}")
            raise ConnectionError(f"Could not connect to CV WebSocket: {e}") from e

    async def send_video_chunk(self, video_chunk: bytes):
        if not self.ws:
            await self.connect()
        try:
            await self.ws.send(video_chunk)
        except Exception as e:
            logger.error(f"Failed to send video chunk to CV: {e}")
            self.ws = None
            raise

    async def receive_gloss(self) -> CVResponse:
        if not self.ws:
            raise ConnectionError("CV WebSocket is not connected.")
        
        start = time.perf_counter()
        try:
            response_raw = await asyncio.wait_for(
                self.ws.recv(), timeout=self.timeout
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

        except asyncio.TimeoutError:
            raise TimeoutError("CV model did not respond in time") from None
        except Exception as e:
            logger.error(f"Error receiving gloss from CV: {e}")
            self.ws = None
            raise

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("Disconnected from CV model WebSocket.")


class MockCVClient(CVModelClient):
    """Mock CV Client for Test Mode (Phase 7)."""
    
    async def connect(self):
        logger.info("MockCVClient connected.")
        
    async def send_video_chunk(self, video_chunk: bytes):
        # Simulate processing time
        await asyncio.sleep(0.1)
        
    async def receive_gloss(self) -> CVResponse:
        # Mock response as requested
        return CVResponse(gloss="سبب رغبه شراء", raw={"gloss": "سبب رغبه شراء", "mock": True})
        
    async def disconnect(self):
        logger.info("MockCVClient disconnected.")


class CVModalRESTClient(CVModelClient):
    """
    Adapter that integrates the Modal Prediction REST API into the CV pipeline.
    Accepts landmark sequences instead of video chunks.
    """
    def __init__(self):
        self.predict_url = getattr(settings, 'MODAL_API_PREDICT_URL', "https://zein1312004--sign-language-api-predict.modal.run")
        self.timeout = getattr(settings, 'MODAL_API_TIMEOUT', 15.0)
        self._pending_sequence = None

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def send_video_chunk(self, video_chunk: bytes):
        """Not used in Modal pipeline, but required by interface. Use send_landmarks instead."""
        pass
        
    async def send_landmarks(self, sequence: list):
        """Specific method to queue landmarks for the next receive_gloss call."""
        self._pending_sequence = sequence

    async def receive_gloss(self) -> CVResponse:
        if not self._pending_sequence:
            raise ValueError("No landmarks sequence provided for Modal API prediction.")

        import httpx
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.predict_url,
                    json={"sequence": self._pending_sequence}
                )
                response.raise_for_status()
                data = response.json()

                if "prediction" not in data:
                    raise ValueError(f"Modal API missing 'prediction' in response: {data}")

                gloss = data["prediction"]
                latency = (time.perf_counter() - start) * 1000

                logger.info(
                    "cv_modal_success",
                    extra={
                        "gloss": gloss,
                        "latency_ms": round(latency, 2),
                    },
                )
                
                self._pending_sequence = None
                return CVResponse(gloss=gloss, raw=data)
                
        except httpx.TimeoutException:
            raise TimeoutError("Modal API prediction timed out")
        except Exception as e:
            logger.error(f"Error receiving prediction from Modal API: {e}")
            raise


def get_cv_client() -> CVModelClient:
    """Factory to return the appropriate CV client based on settings."""
    if getattr(settings, "MOCK_CV", False):
        return MockCVClient()
    if getattr(settings, "MODAL_API_PREDICT_URL", None):
        return CVModalRESTClient()
    return CVWebSocketClient()
