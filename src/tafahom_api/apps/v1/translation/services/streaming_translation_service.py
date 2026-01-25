import contextlib
import time
import asyncio
import uuid
import logging
import base64
from collections import deque
from typing import List

from django.utils import timezone
from channels.db import database_sync_to_async

from .pipeline_service import TranslationPipelineService
from tafahom_api.apps.v1.billing.services import consume_translation_credit

logger = logging.getLogger(__name__)


class StreamingTranslationService:
    """
    Stateful Logic for WebSocket Streaming.

    Flow:
    - Stream TEXT only while user is signing
    - Buffer frames
    - Every SEND_INTERVAL → CV → gloss → text
    - When user stops → generate VOICE ONCE
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
        self.running = False
        self.closed = False

        self.partial_text_buffer: List[str] = []

        self.connection_started_at = time.time()
        self.last_heartbeat = time.time()
        self.last_sent = time.time()

        self.task: asyncio.Task | None = None

    # --------------------------------------------------
    # LIFECYCLE
    # --------------------------------------------------

    async def start(self):
        """Called on WS connect"""
        self.task = asyncio.create_task(self._ai_loop())

    async def shutdown(self):
        """Called on WS disconnect"""
        self.closed = True
        self.running = False

        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task

        if self.translation:
            await self._finalize_translation()

        self.frame_buffer.clear()

    # --------------------------------------------------
    # FRAME / HEARTBEAT
    # --------------------------------------------------

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

    # --------------------------------------------------
    # SESSION MANAGEMENT
    # --------------------------------------------------

    async def start_translation(self, output_type: str):
        if self.running:
            return

        if self.requests_count >= self.config["MAX_REQUESTS_PER_SESSION"]:
            await self.send_json({"type": "error", "message": "Session quota exceeded"})
            await self.close_ws(code=4011)
            return

        subscription = getattr(self.user, "subscription", None)
        has_credit = await database_sync_to_async(
            lambda: subscription and subscription.can_consume(1)
        )()

        if not has_credit:
            await self.send_json({"type": "error", "message": "Not enough credits"})
            return

        await self._consume_credit(subscription)

        # 🔥 IMPORTANT:
        # We ALWAYS stream TEXT.
        # Voice is generated ONLY after STOP.
        self.translation = await self._create_translation("text")

        self.requests_count += 1
        self.running = True
        self.last_sent = time.time()
        self.partial_text_buffer.clear()

        async with self.buffer_lock:
            self.frame_buffer.clear()

        await self.send_json(
            {
                "type": "status",
                "status": "processing",
                "translation_id": self.translation.pk,
            }
        )

    async def stop_translation(self, reason="client"):
        if not self.running:
            return

        self.running = False

        async with self.buffer_lock:
            self.frame_buffer.clear()

        await self._finalize_translation()
        await self.send_json({"type": "status", "status": "stopped"})

    # --------------------------------------------------
    # MAIN AI LOOP
    # --------------------------------------------------

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

    # --------------------------------------------------
    # AI BATCH PROCESSING (TEXT ONLY)
    # --------------------------------------------------

    async def _process_batch(self, frames: List[bytes]):
        try:
            # 🔑 Convert frames to base64 (CV API requirement)
            encoded_frames = [
                base64.b64encode(frame).decode("utf-8") for frame in frames
            ]

            response = await asyncio.wait_for(
                TranslationPipelineService.sign_to_text(encoded_frames),
                timeout=self.config["PIPELINE_TIMEOUT_SECONDS"],
            )

            text = response.get("text")
            if text:
                self.partial_text_buffer.append(text)
                await self.send_json({"type": "partial_result", "text": text})

        except asyncio.TimeoutError:
            await self.send_json(
                {"type": "warning", "message": "Poor connection, retrying..."}
            )
        except Exception:
            logger.exception("pipeline_failure")
            await self.send_json(
                {"type": "error", "message": "AI service temporary error"}
            )

    # --------------------------------------------------
    # FINALIZATION (VOICE GENERATED HERE)
    # --------------------------------------------------

    async def _finalize_translation(self):
        if not self.translation:
            return

        final_text = " ".join(self.partial_text_buffer).strip()

        audio_base64 = None

        # 🔊 Generate voice ONCE after user finishes signing
        if final_text:
            try:
                audio_bytes = (
                    await TranslationPipelineService._tts_client.text_to_speech(
                        final_text
                    )
                )
                if audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            except Exception:
                logger.exception("TTS failed")

        await self._update_translation(
            output_text=final_text,
            status="completed",
            completed_at=timezone.now(),
        )

        payload = {
            "type": "final_result",
            "text": final_text,
        }

        if audio_base64:
            payload["audio"] = audio_base64

        await self.send_json(payload)

    # --------------------------------------------------
    # DB HELPERS
    # --------------------------------------------------

    @database_sync_to_async
    def _consume_credit(self, subscription):
        consume_translation_credit(subscription)

    @database_sync_to_async
    def _create_translation(self, output_type):
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
        if not self.translation:
            return
        for key, value in fields.items():
            setattr(self.translation, key, value)
        self.translation.save(update_fields=list(fields.keys()))
