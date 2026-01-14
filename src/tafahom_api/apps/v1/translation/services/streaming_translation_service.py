import contextlib
import time
import asyncio
import uuid
import logging
from collections import deque
from typing import List

from django.utils import timezone
from channels.db import database_sync_to_async

from .pipeline_service import TranslationPipelineService
from tafahom_api.apps.v1.billing.services import consume_translation_credit

logger = logging.getLogger(__name__)


class StreamingTranslationService:
    """
    Streaming logic, buffering, AI calls, billing, DB lifecycle.
    ASGI-safe, Daphne-safe, production-ready.
    """

    def __init__(self, *, user, send_json, close_ws, config):
        self.user = user
        self.send_json = send_json
        self.close_ws = close_ws
        self.config = config

        self.session_id = str(uuid.uuid4())
        self.requests_count = 0

        self.frame_buffer = deque(maxlen=config["MAX_BUFFER_SIZE"])
        self.buffer_lock = asyncio.Lock()

        self.translation = None
        self.output_type = None
        self.running = False
        self.closed = False

        self.partial_text_buffer: List[str] = []

        self.connection_started_at = time.time()
        self.last_heartbeat = time.time()
        self.last_sent = time.time()

        self.task: asyncio.Task | None = None

    # -----------------------------------------------------
    async def start(self):
        self.task = asyncio.create_task(self._ai_loop())

    async def shutdown(self):
        self.closed = True
        self.running = False

        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task

        if self.translation:
            await self._finalize_translation()

        self.frame_buffer.clear()

    # -----------------------------------------------------
    async def on_frame(self, frame: bytes):
        if not self.running:
            return

        async with self.buffer_lock:
            if len(self.frame_buffer) >= self.config["MAX_BUFFER_SIZE"]:
                return
            self.frame_buffer.append(frame)

    async def on_ping(self):
        self.last_heartbeat = time.time()
        await self.send_json({"type": "pong"})

    # -----------------------------------------------------
    async def start_translation(self, output_type: str):
        if self.running:
            return

        if self.requests_count >= self.config["MAX_REQUESTS_PER_SESSION"]:
            await self.send_json({"type": "error", "message": "Session quota exceeded"})
            await self.close_ws(code=4011)
            return

        subscription = getattr(self.user, "subscription", None)
        if not subscription or not subscription.can_consume(1):
            await self.send_json({"type": "error", "message": "Not enough credits"})
            return

        await self._consume_credit(subscription)

        self.translation = await self._create_translation(output_type)

        self.requests_count += 1
        self.output_type = output_type
        self.running = True
        self.last_sent = time.time()
        self.partial_text_buffer.clear()

        async with self.buffer_lock:
            self.frame_buffer.clear()

        await self.send_json(
            {
                "type": "status",
                "status": "processing",
                "translation_id": self.translation.id,
            }
        )

    async def stop_translation(self, reason="unknown"):
        if not self.running:
            return

        self.running = False

        async with self.buffer_lock:
            self.frame_buffer.clear()

        await self._finalize_translation()
        await self.send_json({"type": "status", "status": "stopped"})

    # -----------------------------------------------------
    async def _ai_loop(self):
        try:
            while not self.closed:
                await asyncio.sleep(0.1)

                if (
                    time.time() - self.connection_started_at
                    > self.config["WS_MAX_CONNECTION_TIME"]
                ):
                    await self.close_ws(code=4009)
                    return

                if time.time() - self.last_heartbeat > self.config["HEARTBEAT_TIMEOUT"]:
                    await self.close_ws(code=4010)
                    return

                if not self.running:
                    continue

                if time.time() - self.last_sent < self.config["SEND_INTERVAL"]:
                    continue

                async with self.buffer_lock:
                    if not self.frame_buffer:
                        continue
                    frames = list(self.frame_buffer)[-self.config["MAX_BATCH_FRAMES"] :]
                    self.frame_buffer.clear()

                if len(frames) > self.config["MAX_FRAMES_PER_REQUEST"]:
                    await self.send_json(
                        {"type": "error", "message": "Too many frames"}
                    )
                    continue

                await self._process_batch(frames)
                self.last_sent = time.time()

        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("AI loop crashed")
            await self.send_json(
                {"type": "error", "message": "Streaming service crashed"}
            )
            await self.close_ws(code=1011)

    async def _process_batch(self, frames: List[bytes]):
        try:
            if self.output_type == "text":
                text = await asyncio.wait_for(
                    TranslationPipelineService.sign_to_text(frames),
                    timeout=self.config["PIPELINE_TIMEOUT_SECONDS"],
                )
                if text:
                    self.partial_text_buffer.append(text)
                    await self.send_json({"type": "partial_result", "text": text})
            else:
                result = await asyncio.wait_for(
                    TranslationPipelineService.sign_to_voice(frames),
                    timeout=self.config["PIPELINE_TIMEOUT_SECONDS"],
                )
                if result:
                    self.partial_text_buffer.append(result["text"])
                    await self.send_json(
                        {
                            "type": "partial_result",
                            "text": result["text"],
                            "audio": result["audio"],
                        }
                    )

        except asyncio.TimeoutError:
            await self.send_json(
                {"type": "warning", "message": "Poor connection, retrying..."}
            )

        except Exception:
            logger.exception("pipeline_failure")
            await self.send_json(
                {"type": "error", "message": "AI service temporary error"}
            )

    async def _finalize_translation(self):
        if not self.translation:
            return

        await self._update_translation(
            output_text=" ".join(self.partial_text_buffer),
            status="completed",
            completed_at=timezone.now(),
        )

    # -----------------------------------------------------
    # ASYNC DB / BILLING HELPERS (ASGI SAFE)
    # -----------------------------------------------------

    @database_sync_to_async
    def _consume_credit(self, subscription):
        consume_translation_credit(subscription)

    @database_sync_to_async
    def _create_translation(self, output_type):
        # ✅ LAZY IMPORT — FIXES AppRegistryNotReady
        from ..models import TranslationRequest

        return TranslationRequest.objects.create(
            user=self.user,
            direction="from_sign",
            input_type="video",
            output_type=output_type,
            status="processing",
            started_at=timezone.now(),
            processing_mode="streaming",
            source_language="ase",
        )

    @database_sync_to_async
    def _update_translation(self, **fields):
        for key, value in fields.items():
            setattr(self.translation, key, value)
        self.translation.save(update_fields=list(fields.keys()))
