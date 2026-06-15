import asyncio
import logging
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings

from tafahom_api.apps.v1.ai.clients.cv_ws_client import get_cv_client
from tafahom_api.apps.v1.ai.clients.nlp_model_client import NLPModelClient
from tafahom_api.apps.v1.ai.clients.text_to_gloss_client import TextToGlossClient
from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
from tafahom_api.apps.v1.ai.clients.text_to_speech_client import TextToSpeechClient
from tafahom_api.apps.v1.ai.utils.ensure_wav import ensure_wav

from tafahom_api.apps.v1.translation.services.dtos import (
    CVResponse,
    NLPResponse,
    PipelineConfig,
    TranslationPipelineResult,
)
from tafahom_api.apps.v1.translation.services.sign_video_service import (
    generate_sign_video_from_gloss,
)
from tafahom_api.apps.v1.translation.sign_map import ANIMATION_MAP, SIGN_MAP, SYNONYM_MAP

logger = logging.getLogger(__name__)

class PredictionStabilizer:
    """
    Stabilizes real-time model predictions by enforcing confidence thresholds
    and consecutive frame consistency.
    """
    def __init__(self, confidence_threshold=0.6, consistency_frames=2):
        self.confidence_threshold = confidence_threshold
        self.consistency_frames = consistency_frames
        self.prediction_history = []
        self.last_accepted_prediction = None
        self._rejections_since_last_accept = 0
        # After this many rejected frames (different prediction), allow the same sign again.
        # This prevents permanent deadlock when the user signs the same word twice.
        self._reset_after_rejections = 5

    def clear(self):
        self.prediction_history.clear()
        self.last_accepted_prediction = None
        self._rejections_since_last_accept = 0
        logger.info("stabilizer: cleared state")

    def get_state(self):
        return {
            "history_length": len(self.prediction_history),
            "last_accepted": self.last_accepted_prediction
        }

    def process(self, prediction: str, confidence: float) -> Optional[str]:
        if not prediction:
            return None
            
        # 1. Ignore low confidence predictions
        if confidence < self.confidence_threshold:
            logger.debug("stabilizer: rejected '%s' confidence=%.2f < %.2f",
                         prediction, confidence, self.confidence_threshold)
            return None
            
        # 2. If this is the same sign as the last accepted one, track rejections.
        # After enough different frames have passed, clear last_accepted so the
        # sign can be recognized again (e.g., signing the same word twice).
        if prediction == self.last_accepted_prediction:
            self._rejections_since_last_accept += 1
            if self._rejections_since_last_accept >= self._reset_after_rejections:
                logger.debug("stabilizer: resetting last_accepted after %d rejections",
                             self._rejections_since_last_accept)
                self.last_accepted_prediction = None
                self._rejections_since_last_accept = 0
                self.prediction_history.clear()
            return None
        else:
            # Different prediction — reset the repeat-rejection counter
            self._rejections_since_last_accept = 0

        # 3. Add to sliding window
        self.prediction_history.append(prediction)

        # 4. Require N consecutive identical predictions
        if len(self.prediction_history) >= self.consistency_frames:
            recent = self.prediction_history[-self.consistency_frames:]
            if all(p == prediction for p in recent):
                logger.info("stabilizer: accepted '%s' confidence=%.2f", prediction, confidence)
                self.last_accepted_prediction = prediction
                self._rejections_since_last_accept = 0
                self.prediction_history.clear()
                return prediction
            
            self.prediction_history.pop(0)

        return None


class RetryHandler:
    """
    Async retry with exponential backoff for AI service calls.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 5.0,
        backoff_factor: float = 2.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    async def execute(
        self,
        coro_factory: Callable,
        service_name: str = "unknown",
        timeout: Optional[float] = None,
    ) -> Any:
        last_exc = None

        for attempt in range(1, self.max_retries + 1):
            try:
                coro = coro_factory()
                if timeout:
                    result = await asyncio.wait_for(coro, timeout=timeout)
                else:
                    result = await coro

                if attempt > 1:
                    logger.info(
                        "%s succeeded on retry %d",
                        service_name,
                        attempt,
                    )
                return result

            except asyncio.TimeoutError:
                last_exc = TimeoutError(f"{service_name} timed out")
                logger.warning(
                    "%s timeout (attempt %d/%d)",
                    service_name,
                    attempt,
                    self.max_retries,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "%s failed (attempt %d/%d): %s",
                    service_name,
                    attempt,
                    self.max_retries,
                    str(exc),
                )

            if attempt < self.max_retries:
                delay = min(
                    self.base_delay * (self.backoff_factor ** (attempt - 1)),
                    self.max_delay,
                )
                await asyncio.sleep(delay)

        raise last_exc or RuntimeError(f"{service_name} failed after {self.max_retries} retries")


class SignTranslationService:
    """
    Orchestrates the sign language translation pipeline.

    Pipeline:
        1. Receive buffered video frames
        2. Send to CV model → receives gloss text
        3. Send gloss to NLP model → receives Arabic text
        4. Return TranslationPipelineResult with full metadata

    Supports:
        - Dependency injection of CV and NLP clients
        - Retry handling with exponential backoff
        - Per-call timeout protection
        - Structured logging at every stage
        - Latency tracking per stage
    """

    def __init__(
        self,
        cv_client=None,
        nlp_client=None,
        retry_handler: Optional[RetryHandler] = None,
        config: Optional[PipelineConfig] = None,
        event_callback: Optional[Callable] = None,
    ):
        

        self.cv_client = cv_client or get_cv_client()
        self.nlp_client = nlp_client or NLPModelClient()
        self.retry_handler = retry_handler or RetryHandler(
            max_retries=getattr(settings, "MAX_CV_RETRIES", 3),
            base_delay=0.5,
            max_delay=5.0,
        )
        self.config = config or PipelineConfig()
        self.event_callback = event_callback
        self.stabilizer = PredictionStabilizer(confidence_threshold=0.6, consistency_frames=1)

    async def initialize(self):
        """Called to initialize any persistent connections."""
        if hasattr(self.cv_client, "connect"):
            await self.cv_client.connect()

    async def cleanup(self):
        """Called to close persistent connections."""
        if hasattr(self.cv_client, "disconnect"):
            await self.cv_client.disconnect()

    async def translate(
        self, frames: List[bytes], session_id: Optional[str] = None
    ) -> TranslationPipelineResult:
        """
        Run the full CV → NLP translation pipeline on buffered frames.

        Args:
            frames: List of binary video frame bytes.
            session_id: Optional session identifier for logging.

        Returns:
            TranslationPipelineResult with gloss, text, and timing metadata.
        """
        request_id = session_id or f"tr_{int(time.time() * 1000)}"
        overall_start = time.perf_counter()
        cv_latency: Optional[float] = None
        nlp_latency: Optional[float] = None
        cv_retries = 0
        nlp_retries = 0

        if not frames:
            logger.warning(
                "translate_called_empty_frames",
                extra={"request_id": request_id},
            )
            return TranslationPipelineResult(
                gloss="",
                text="",
                success=False,
                error="No frames provided",
            )

        try:
            await self._emit_event("translation_started", {"request_id": request_id})
        except Exception:
            pass

        combined_chunk = b"".join(frames)

        cv_start = time.perf_counter()
        cv_result = await self._call_cv_with_retry(
            combined_chunk, request_id
        )
        cv_latency = (time.perf_counter() - cv_start) * 1000

        gloss = cv_result.gloss
        gloss_upper = gloss.strip().upper()

        logger.info(
            "cv_result",
            extra={
                "request_id": request_id,
                "gloss": gloss_upper,
                "latency_ms": round(cv_latency, 2),
            },
        )

        try:
            await self._emit_event(
                "gloss_received",
                {"request_id": request_id, "gloss": gloss_upper},
            )
        except Exception:
            pass

        nlp_start = time.perf_counter()
        nlp_result = await self._call_nlp_with_retry(
            gloss_upper, request_id
        )
        nlp_latency = (time.perf_counter() - nlp_start) * 1000

        text = nlp_result.text

        logger.info(
            "nlp_result",
            extra={
                "request_id": request_id,
                "gloss": gloss_upper,
                "text": text,
                "latency_ms": round(nlp_latency, 2),
            },
        )

        total_latency = (time.perf_counter() - overall_start) * 1000

        try:
            await self._emit_event(
                "translation_received",
                {
                    "request_id": request_id,
                    "gloss": gloss_upper,
                    "text": text,
                },
            )
        except Exception:
            pass

        return TranslationPipelineResult(
            gloss=gloss_upper,
            text=text,
            success=True,
            cv_latency_ms=round(cv_latency, 2),
            nlp_latency_ms=round(nlp_latency, 2),
            total_latency_ms=round(total_latency, 2),
            cv_retries=cv_retries,
            nlp_retries=nlp_retries,
        )

    async def translate_landmarks(
        self, sequence: list, session_id: Optional[str] = None
    ) -> TranslationPipelineResult:
        """
        Run the full CV → NLP translation pipeline on a sequence of landmarks.
        Includes comprehensive diagnostic logging to compare production vs training input.
        """
        import numpy as np

        request_id = session_id or f"trl_{int(time.time() * 1000)}"
        overall_start = time.perf_counter()
        cv_latency: Optional[float] = None
        nlp_latency: Optional[float] = None

        if not sequence:
            return TranslationPipelineResult(
                gloss="", text="", success=False, error="No sequence provided"
            )

        # -------------------------------------------------------
        # DIAGNOSTIC: Validate and log sequence statistics.
        # Compare these numbers against your LOCAL training data.
        # If the numbers differ, that is your root cause.
        # -------------------------------------------------------
        try:
            arr = np.array(sequence, dtype=np.float32)
            n_frames, n_landmarks, n_coords = arr.shape if arr.ndim == 3 else (len(sequence), -1, -1)
            flat = arr.flatten()

            # Count frames that have at least one non-zero landmark
            frames_with_data = int(np.any(arr.reshape(n_frames, -1) != 0, axis=1).sum())
            zero_frames = n_frames - frames_with_data
            non_zero_values = int(np.count_nonzero(flat))

            logger.info(
                "sequence_diagnostic",
                extra={
                    "request_id": request_id,
                    "shape": [n_frames, n_landmarks, n_coords],
                    "frames_with_data": frames_with_data,
                    "zero_frames": zero_frames,        # ← HIGH if MediaPipe not detecting
                    "non_zero_values": non_zero_values,
                    "min": round(float(flat.min()), 4),
                    "max": round(float(flat.max()), 4),
                    "mean": round(float(flat.mean()), 4),
                    "std": round(float(flat.std()), 4),
                    # Training data reference (screen-space coords): min≈0, max≈1, mean≈0.3-0.6
                    # If mean ≈ 0 and std ≈ 0, MediaPipe is not detecting anything.
                }
            )

            if zero_frames > 48:  # More than half the sequence is empty
                logger.warning(
                    "sequence_mostly_empty",
                    extra={
                        "request_id": request_id,
                        "zero_frames": zero_frames,
                        "msg": "MediaPipe likely not detecting landmarks. Check camera/lighting."
                    }
                )

        except Exception as diag_err:
            logger.warning(f"Sequence diagnostic failed: {diag_err}")

        # DIAGNOSTIC: Save sequence to .npy file for direct comparison
        try:
            import os
            import numpy as np
            save_dir = os.path.join(settings.BASE_DIR, "sequence_logs")
            os.makedirs(save_dir, exist_ok=True)
            npy_path = os.path.join(save_dir, f"seq_{request_id}.npy")
            np.save(npy_path, np.array(sequence, dtype=np.float32))
            logger.info(f"Saved incoming sequence to {npy_path} for comparison.")
        except Exception as e:
            logger.error(f"Failed to save sequence to .npy: {e}")

        try:
            await self._emit_event("translation_started", {"request_id": request_id})
        except Exception:
            pass

        cv_start = time.perf_counter()
        cv_result = await self._call_cv_landmarks_with_retry(sequence, request_id)
        cv_latency = (time.perf_counter() - cv_start) * 1000

        raw_gloss = cv_result.gloss

        # BUG FIX: `cv_result.confidence or 1.0` is wrong in Python.
        # If confidence=0.0 (falsy), the expression evaluates to 1.0,
        # bypassing the stabilizer threshold entirely.
        # Correct fix: use `is not None` check.
        confidence = cv_result.confidence if cv_result.confidence is not None else 1.0

        logger.info(
            "cv_raw_prediction",
            extra={
                "request_id": request_id,
                "raw_gloss": raw_gloss,
                "confidence": round(confidence, 4),
                "threshold": self.stabilizer.confidence_threshold,
                "passes_threshold": confidence >= self.stabilizer.confidence_threshold,
            }
        )

        # Stabilize prediction
        gloss = self.stabilizer.process(raw_gloss, confidence)
        
        if not gloss or gloss == "NO_SIGN":
            # In discrete word-based translation, we must send a fallback response to avoid blocking the UI
            try:
                await self._emit_event(
                    "translation_received",
                    {"request_id": request_id, "gloss": "NO_SIGN", "text": "No Sign Detected"},
                )
            except Exception:
                pass
            return TranslationPipelineResult(
                gloss="NO_SIGN",
                text="No Sign Detected",
                success=True,
                cv_latency_ms=round(cv_latency, 2),
                nlp_latency_ms=0,
                total_latency_ms=round(cv_latency, 2),
                cv_retries=0,
                nlp_retries=0,
            )

        gloss_upper = gloss.strip().upper()

        try:
            await self._emit_event(
                "gloss_received", {"request_id": request_id, "gloss": gloss_upper}
            )
        except Exception:
            pass

        nlp_start = time.perf_counter()
        nlp_result = await self._call_nlp_with_retry(gloss_upper, request_id)
        nlp_latency = (time.perf_counter() - nlp_start) * 1000

        text = nlp_result.text

        total_latency = (time.perf_counter() - overall_start) * 1000

        try:
            await self._emit_event(
                "translation_received",
                {"request_id": request_id, "gloss": gloss_upper, "text": text},
            )
        except Exception:
            pass

        return TranslationPipelineResult(
            gloss=gloss_upper,
            text=text,
            success=True,
            cv_latency_ms=round(cv_latency, 2),
            nlp_latency_ms=round(nlp_latency, 2),
            total_latency_ms=round(total_latency, 2),
            cv_retries=0,
            nlp_retries=0,
        )

    async def _call_cv_with_retry(
        self, video_chunk: bytes, request_id: str
    ) -> CVResponse:
        timeout = self.config.cv_timeout

        async def _cv_flow():
            await self.cv_client.send_video_chunk(video_chunk)
            return await self.cv_client.receive_gloss()

        try:
            result = await self.retry_handler.execute(
                _cv_flow,
                service_name="CV",
                timeout=timeout,
            )
            if isinstance(result, CVResponse):
                return result
            if isinstance(result, dict):
                gloss = result.get("gloss", "")
                if not gloss:
                    raise ValueError("CV returned empty gloss")
                return CVResponse(gloss=gloss, raw=result)
            return CVResponse(gloss="")
        except Exception as exc:
            logger.error(
                "cv_failed_after_retries",
                extra={
                    "request_id": request_id,
                    "error": str(exc),
                },
            )
            await self._emit_event(
                "translation_error",
                {
                    "request_id": request_id,
                    "stage": "cv",
                    "error": str(exc),
                },
            )
            raise

    async def _call_cv_landmarks_with_retry(
        self, sequence: list, request_id: str
    ) -> CVResponse:
        timeout = self.config.cv_timeout

        async def _cv_flow():
            if hasattr(self.cv_client, "receive_gloss"):
                return await self.cv_client.receive_gloss(sequence=sequence)
            else:
                raise NotImplementedError("CV client does not support passing sequence to receive_gloss")

        try:
            result = await self.retry_handler.execute(
                _cv_flow,
                service_name="CV_Landmarks",
                timeout=timeout,
            )
            # receive_gloss always returns CVResponse; no need for isinstance fallbacks
            return result
        except Exception as exc:
            logger.error(f"cv_landmarks_failed: {exc}")
            await self._emit_event(
                "translation_error",
                {"request_id": request_id, "stage": "cv", "error": str(exc)},
            )
            raise

    async def _call_nlp_with_retry(
        self, gloss: str, request_id: str
    ) -> NLPResponse:
        nlp_retry = RetryHandler(
            max_retries=getattr(settings, "NLP_RETRIES", 3),
            base_delay=0.3,
            max_delay=3.0,
        )
        timeout = self.config.nlp_timeout

        try:
            result = await nlp_retry.execute(
                lambda: self.nlp_client.translate_gloss(gloss),
                service_name="NLP",
                timeout=timeout,
            )
            if isinstance(result, NLPResponse):
                return result
            if isinstance(result, dict):
                text = result.get("text", "")
                if not text:
                    raise ValueError("NLP returned empty text")
                return NLPResponse(text=text, raw=result)
            return NLPResponse(text="")
        except Exception as exc:
            logger.error(
                "nlp_failed_after_retries",
                extra={
                    "request_id": request_id,
                    "gloss": gloss,
                    "error": str(exc),
                },
            )
            await self._emit_event(
                "translation_error",
                {
                    "request_id": request_id,
                    "stage": "nlp",
                    "gloss": gloss,
                    "error": str(exc),
                },
            )
            raise

    async def _emit_event(self, event_type: str, data: dict):
        if self.event_callback:
            payload = {"type": event_type, **data}
            await self.event_callback(payload)

    # --------------------------------------------------
    # TEXT → SIGN (avatar pipeline, static helpers)
    # --------------------------------------------------

    @staticmethod
    def _with_timeout(coro):
        return asyncio.wait_for(coro, timeout=settings.AI_TIMEOUT)

    @staticmethod
    def _extract_gloss(nlp_resp: Dict[str, Any]) -> List[str]:
        raw = (
            nlp_resp.get("gloss_translation")
            or nlp_resp.get("gloss")
            or nlp_resp.get("text")
        )
        if not raw:
            raise ValueError("NLP returned empty output")
        from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names
        
        match_result = translate_to_animation_names(str(raw))
        resolved = match_result["animations"]
        
        if not resolved:
            raise ValueError(f"No supported sign tokens found for input: {raw}")
        return resolved

    @classmethod
    async def text_to_sign(cls, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            raise RuntimeError("Text must not be empty")
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Phase 1: Try direct phrase/word match using the unified animation service
        # This handles phrase priorities, synonym replacements, and word boundaries automatically
        from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names
        
        match_result = translate_to_animation_names(text)
        resolved = list(match_result["animations"])
        unmatched = list(match_result["unknown_words"])

        # Phase 2: Send only unmatched words to NLP text-to-gloss
        if unmatched:
            nlp_resp = await cls._with_timeout(
                TextToGlossClient().text_to_gloss(" ".join(unmatched))
            )
            # This needs slightly adjusted logic because _extract_gloss also attempts dictionary mapping internally
            nlp_resolved = cls._extract_gloss(nlp_resp)
            resolved.extend(nlp_resolved)

        # Deduplicate while preserving order
        seen: set = set()
        gloss: List[str] = []
        for t in resolved:
            if t not in seen:
                seen.add(t)
                gloss.append(t)

        if not gloss:
            raise ValueError(f"No supported sign tokens found for input: {text}")

        video_url = generate_sign_video_from_gloss(gloss)
        logger.info(
            "text_to_sign_success",
            extra={
                "request_id": request_id,
                "gloss": gloss,
                "direct_match": len(resolved),
                "nlp_match": len(gloss) - len(resolved),
                "duration_ms": (time.perf_counter() - start) * 1000,
            },
        )
        return {"gloss": gloss, "video": video_url}

    @classmethod
    async def voice_to_sign(cls, uploaded_file) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        wav_file = ensure_wav(uploaded_file)
        stt_resp = await cls._with_timeout(SpeechToTextClient().speech_to_text(wav_file))
        text = stt_resp.get("text")
        if not text:
            raise RuntimeError("STT returned empty text")
        result = await cls.text_to_sign(text)
        logger.info(
            "voice_to_sign_success",
            extra={
                "request_id": request_id,
                "gloss": result["gloss"],
                "duration_ms": (time.perf_counter() - start) * 1000,
            },
        )
        return {"text": text, "gloss": result["gloss"], "video": result["video"]}


from tafahom_api.apps.v1.translation.services.normalization import normalize_arabic
