"""
base.py - Unified abstract interface for streaming ASR engines in S2.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import numpy as np


@dataclass
class Hypothesis:
    """Represents a speech recognition hypothesis at a specific point in time."""
    text: str
    is_final: bool = False
    timestamp_ms: float = 0.0
    confidence: Optional[float] = None
    tokens: List[str] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelInfo:
    """Metadata describing the loaded ASR model and runtime configuration."""
    engine_name: str
    model_name: str
    model_family: str       # e.g., 'zipformer', 'whisper', 'conformer'
    language: str           # e.g., 'en', 'ja', 'multilingual'
    model_size_mb: float
    quantization: str       # e.g., 'int8', 'fp16', 'fp32'
    sample_rate: int = 16000
    is_native_streaming: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)


class ASREngine(ABC):
    """
    Abstract interface for streaming ASR engines.
    
    Hot-path lifecycle:
    1. start(sample_rate)
    2. push_audio(chunk) -> loops during stream
    3. get_partial() -> polled or returned after chunks
    4. finalize_segment() -> marks endpoint / speech segment completion
    5. stop() -> cleans up resources
    """

    @abstractmethod
    def initialize(self) -> None:
        """Loads weights and prepares inference session."""
        pass

    @abstractmethod
    def start_stream(self) -> None:
        """Resets stream buffers for a new utterance/stream session."""
        pass

    @abstractmethod
    def push_audio(self, pcm_chunk: np.ndarray) -> None:
        """
        Accepts a chunk of 16kHz Mono audio.
        pcm_chunk: float32 in [-1.0, 1.0] or int16 array.
        """
        pass

    @abstractmethod
    def get_partial(self) -> Hypothesis:
        """Returns the current best streaming hypothesis."""
        pass

    @abstractmethod
    def is_endpoint_detected(self) -> bool:
        """Returns True if VAD/acoustic endpoint was detected."""
        pass

    @abstractmethod
    def finalize_segment(self) -> Hypothesis:
        """Forces endpointing on current audio buffer and returns final hypothesis."""
        pass

    @abstractmethod
    def stop_stream(self) -> None:
        """Finalizes current stream session."""
        pass

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """Returns model metadata and environment config."""
        pass
