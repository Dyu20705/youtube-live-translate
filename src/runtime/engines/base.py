"""
base.py - Base abstract classes and data contracts for ASR and MT engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class Hypothesis:
    text: str
    is_final: bool = False
    start_time_ms: float = 0.0
    end_time_ms: float = 0.0
    confidence: float = 1.0
    tokens: Optional[List[str]] = None


@dataclass
class TranslationResult:
    target_text: str
    source_text: str
    tokenizer_time_ms: float = 0.0
    inference_time_ms: float = 0.0
    detokenizer_time_ms: float = 0.0
    total_time_ms: float = 0.0
    src_tokens_count: int = 0
    tgt_tokens_count: int = 0
    raw_tokens: Optional[List[str]] = None


class ASREngine(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def start_stream(self) -> None:
        pass

    @abstractmethod
    def push_audio(self, pcm_chunk: np.ndarray) -> None:
        pass

    @abstractmethod
    def get_partial(self) -> Hypothesis:
        pass

    @abstractmethod
    def is_endpoint_detected(self) -> bool:
        pass

    @abstractmethod
    def finalize_segment(self) -> Hypothesis:
        pass

    @abstractmethod
    def stop_stream(self) -> None:
        pass


class MTEngine(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def translate(self, text: str, beam_size: int = 1, max_decoding_length: int = 256) -> TranslationResult:
        pass

    @abstractmethod
    def translate_batch(self, texts: List[str], beam_size: int = 1, max_decoding_length: int = 256) -> List[TranslationResult]:
        pass
