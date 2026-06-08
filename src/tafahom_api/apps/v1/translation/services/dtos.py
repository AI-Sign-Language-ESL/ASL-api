from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CVRequest:
    video_chunk: bytes


@dataclass
class CVResponse:
    gloss: str
    raw: Optional[dict] = None
    confidence: Optional[float] = None


@dataclass
class NLPRequest:
    gloss: str


@dataclass
class NLPResponse:
    text: str
    raw: Optional[dict] = None


@dataclass
class TranslationPipelineResult:
    gloss: str
    text: str
    success: bool = True
    error: Optional[str] = None
    cv_latency_ms: Optional[float] = None
    nlp_latency_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    cv_retries: int = 0
    nlp_retries: int = 0


@dataclass
class PipelineConfig:
    send_interval: int = 5
    max_buffer_size: int = 120
    max_batch_frames: int = 30
    max_frames_per_request: int = 64
    max_requests_per_session: int = 5
    pipeline_timeout_seconds: int = 15
    heartbeat_timeout: int = 30
    ws_max_connection_time: int = 900
    cv_max_retries: int = 3
    nlp_retries: int = 3
    cv_timeout: int = 30
    nlp_timeout: int = 30
