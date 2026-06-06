import contextlib
import time
import asyncio
import uuid
import logging
import base64
from collections import deque
from typing import List, Optional, Callable

from django.utils import timezone
from channels.db import database_sync_to_async

from .sign_translation_service import SignTranslationService, PipelineConfig

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

    def __init__(
        self,
        *,
        user,
        send_json,
        close_ws,
        config,
        sign_service: Optional[SignTranslationService] = None,
    ):
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
        self._bg_tasks: set[asyncio.Task] = set()

        pipeline_config = PipelineConfig(
            send_interval=config.get("SEND_INTERVAL", 5),
            max_buffer_size=config.get("MAX_BUFFER_SIZE", 120),
            max_batch_frames=config.get("MAX_BATCH_FRAMES", 30),
            max_frames_per_request=config.get("MAX_FRAMES_PER_REQUEST", 64),
            max_requests_per_session=config.get("MAX_REQUESTS_PER_SESSION", 5),
            pipeline_timeout_seconds=config.get("PIPELINE_TIMEOUT_SECONDS", 15),
            heartbeat_timeout=config.get("HEARTBEAT_TIMEOUT", 30),
            ws_max_connection_time=config.get("WS_MAX_CONNECTION_TIME", 900),
        )
        self.sign_service = sign_service or SignTranslationService(
            config=pipeline_config,
            event_callback=self._on_pipeline_event,
        )

    # --------------------------------------------------
    # LIFECYCLE
    # --------------------------------------------------

    async def start(self):
        """Called on WS connect"""
        await self.sign_service.initialize()
        self.task = asyncio.create_task(self._ai_loop())

    async def shutdown(self):
        """Called on WS disconnect"""
        self.closed = True
        self.running = False

        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task

        for t in list(self._bg_tasks):
            t.cancel()
        if self._bg_tasks:
            await asyncio.wait(self._bg_tasks, timeout=5)
        self._bg_tasks.clear()

        if self.translation:
            await self._finalize_translation()

        await self.sign_service.cleanup()
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

    async def on_landmarks(self, sequence: list):
        if not self.running:
            return

        # Unlike binary frames which are batched by the _ai_loop,
        # we process the exactly 96-frame landmark sequence immediately.
        try:
            # We bypass the _process_batch logic, which is for binary frames,
            # and directly call a new method on SignTranslationService for landmarks.
            result = await self.sign_service.translate_landmarks(sequence, self.session_id)
            if result and result.success:
                self.partial_text_buffer.append(result.text)
        except Exception as e:
            logger.error(f"Error processing landmarks: {e}")
            await self.send_json({"type": "error", "message": "Failed to process landmarks"})

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

        subscription = await database_sync_to_async(
            lambda: getattr(self.user, "subscription", None)
        )()
        has_token = subscription and await database_sync_to_async(
            lambda: subscription.can_consume(5)
        )()

        if not has_token:
            await self.send_json({"type": "error", "message": "Not enough tokens"})
            return

        await self._consume_token(subscription)

        # 🔥 ALWAYS stream TEXT
        # Voice is generated ONLY after STOP
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

    async def _on_pipeline_event(self, payload: dict):
        event_type = payload.get("type", "")

        if event_type == "translation_started":
            await self.send_json({"type": "translation_started", "request_id": payload.get("request_id", "")})

        elif event_type == "gloss_received":
            await self.send_json({
                "type": "gloss_received",
                "gloss": payload.get("gloss", ""),
            })

        elif event_type == "translation_received":
            await self.send_json({
                "type": "translation_received",
                "gloss": payload.get("gloss", ""),
                "text": payload.get("text", ""),
            })

        elif event_type == "translation_error":
            await self.send_json({
                "type": "translation_error",
                "stage": payload.get("stage", ""),
                "message": payload.get("error", "Unknown error"),
            })

    async def _process_batch(self, frames: List[bytes]):
        try:
            result = await asyncio.wait_for(
                self.sign_service.translate(frames, session_id=self.session_id),
                timeout=self.config["PIPELINE_TIMEOUT_SECONDS"],
            )

            if result.success and result.text:
                self.partial_text_buffer.append(result.text)

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
    # FINALIZATION
    # --------------------------------------------------

    async def _finalize_translation(self):
        if not self.translation:
            return

        final_text = " ".join(self.partial_text_buffer).strip()

        await self._update_translation(
            output_text=final_text,
            status="completed",
            completed_at=timezone.now(),
        )

        # 1) Send text immediately — frontend speaks via native TTS right away
        await self.send_json({
            "type": "final_result",
            "text": final_text,
        })

        # 2) Fetch ElevenLabs audio in background — send when ready to upgrade quality
        if final_text:
            t = asyncio.create_task(self._send_elevenlabs_audio(final_text))
            self._bg_tasks.add(t)
            t.add_done_callback(self._bg_tasks.discard)

    async def _send_elevenlabs_audio(self, text: str):
        """Fetch ElevenLabs audio and push it to the client as a follow-up event."""
        try:
            from tafahom_api.apps.v1.ai.clients.text_to_speech_client import TextToSpeechClient
            audio_bytes = await TextToSpeechClient().text_to_speech(text)
            if audio_bytes:
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                await self.send_json({
                    "type": "tts_audio",
                    "audio_b64": audio_b64,
                    "mime_type": "audio/mpeg",
                })
        except Exception:
            logger.exception("ElevenLabs background TTS failed — native TTS already played")

    # --------------------------------------------------
    # DB HELPERS (ALL LAZY IMPORTS)
    # --------------------------------------------------

    @database_sync_to_async
    def _consume_token(self, subscription):
        # 🔑 LAZY IMPORT (CRITICAL FIX)
        from tafahom_api.apps.v1.billing.services import consume_translation_token

        consume_translation_token(subscription)

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
