from dataclasses import dataclass
from typing import List, Optional


# =====================================================
# COMPUTER VISION (SIGN → GLOSS)
# =====================================================


@dataclass
class CVRequest:
    frames: List[str]  # base64-encoded JPEG frames
    fps: int = 30
    language: str = "ase"  # Arabic Sign Language


@dataclass
class CVResponse:
    gloss: List[str]  # e.g. ["HELLO", "YOU"]
    confidence: Optional[float] = None


# =====================================================
# NLP (GLOSS → TEXT)
# =====================================================


@dataclass
class NLPRequest:
    gloss: List[str]
    target_language: str = "ar"


@dataclass
class NLPResponse:
    text: str  # e.g. "مرحبا"
    confidence: Optional[float] = None


# =====================================================
# SPEECH (TEXT → VOICE)
# =====================================================


@dataclass
class SpeechRequest:
    text: str
    voice: str = "ar-EG"
    speed: float = 1.0


@dataclass
class SpeechResponse:
    audio_base64: str  # 🔥 FIXED: base64-encoded audio (NOT URL)
    duration_ms: Optional[int] = None
