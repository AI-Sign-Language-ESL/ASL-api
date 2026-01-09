import json
import time
import logging
from collections import deque

from channels.generic.websocket import AsyncWebsocketConsumer

from .services.streaming_translation_service import StreamingTranslationService
from .config import (
    WS_MAX_MESSAGES_PER_SECOND,
    SEND_INTERVAL,
    MAX_BUFFER_SIZE,
    MAX_BATCH_FRAMES,
    MAX_FRAMES_PER_REQUEST,
    MAX_REQUESTS_PER_SESSION,
    PIPELINE_TIMEOUT_SECONDS,
    HEARTBEAT_TIMEOUT,
    WS_MAX_CONNECTION_TIME,
)

logger = logging.getLogger(__name__)


class SignTranslationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket transport layer ONLY.
    No business logic.
    Production-ready and unit-test safe.
    """

    async def connect(self):
        self.user = self.scope.get("user")

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.message_times = deque()
        self.connection_start_time = time.time()

        self.service = StreamingTranslationService(
            user=self.user,
            send_json=self.send_json,
            close_ws=self.close,
            config={
                "SEND_INTERVAL": SEND_INTERVAL,
                "MAX_BUFFER_SIZE": MAX_BUFFER_SIZE,
                "MAX_BATCH_FRAMES": MAX_BATCH_FRAMES,
                "MAX_FRAMES_PER_REQUEST": MAX_FRAMES_PER_REQUEST,
                "MAX_REQUESTS_PER_SESSION": MAX_REQUESTS_PER_SESSION,
                "PIPELINE_TIMEOUT_SECONDS": PIPELINE_TIMEOUT_SECONDS,
                "HEARTBEAT_TIMEOUT": HEARTBEAT_TIMEOUT,
                "WS_MAX_CONNECTION_TIME": WS_MAX_CONNECTION_TIME,
            },
        )

        await self.accept()

        try:
            await self.service.start()
        except Exception:
            logger.exception("StreamingTranslationService failed to start")
            await self.send_json(
                {"type": "error", "message": "Translation service unavailable"}
            )
            await self.close(code=1011)

    async def disconnect(self, close_code):
        if hasattr(self, "service"):
            try:
                await self.service.shutdown()
            except Exception:
                logger.exception("Error during service shutdown")

    async def receive(self, text_data=None, bytes_data=None):
        # Ignore empty frames (important for tests)
        if not text_data and not bytes_data:
            return

        # Enforce max connection lifetime
        if time.time() - self.connection_start_time > WS_MAX_CONNECTION_TIME:
            await self.close(code=4009)
            return

        # Transport-level rate limiting
        now = time.time()
        self.message_times.append(now)
        while self.message_times and now - self.message_times[0] > 1:
            self.message_times.popleft()

        if len(self.message_times) > WS_MAX_MESSAGES_PER_SECOND:
            await self.close(code=4008)
            return

        # Binary frames (video chunks)
        if bytes_data:
            try:
                await self.service.on_frame(bytes_data)
            except Exception:
                logger.exception("Frame processing failed")
                await self.send_json(
                    {"type": "error", "message": "Frame processing error"}
                )
            return

        # Text frames (JSON control messages)
        try:
            data = json.loads(text_data)
        except Exception:
            await self.send_json({"type": "error", "message": "Invalid JSON"})
            return

        msg_type = data.get("type")
        action = data.get("action")

        if msg_type == "ping":
            await self.service.on_ping()
            return

        try:
            if action == "start":
                await self.service.start_translation(data.get("output_type"))

            elif action == "stop":
                await self.service.stop_translation("client")

            else:
                await self.send_json({"type": "error", "message": "Unknown action"})

        except Exception:
            logger.exception("Service action failed")
            await self.send_json({"type": "error", "message": "Translation error"})
