from dataclasses import dataclass
from typing import List, Optional


# ---------------------------
# COMPUTER VISION
# ---------------------------

@dataclass
class CVRequest:
    frames: List[str]           # base64-encoded frames
    fps: int = 30
    language: str = "ase"


@dataclass
class CVResponse:
    gloss: List[str]
    confidence: float


# ---------------------------
# NLP
# ---------------------------

@dataclass
class NLPRequest:
    gloss: List[str]
    target_language: str = "ar"


@dataclass
class NLPResponse:
    text: str
    confidence: Optional[float] = None


# ---------------------------
# SPEECH
# ---------------------------

@dataclass
class SpeechRequest:
    text: str
    voice: str = "ar-EG"
    speed: float = 1.0


@dataclass
class SpeechResponse:
    audio_url: str               # or base64 audio if needed
    duration_ms: Optional[int] = None
