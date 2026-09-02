"""
base.py - Abstract interface and data models for local Machine Translation (MT) engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class TranslationResult:
    target_text: str
    source_text: str
    tokenizer_time_ms: float
    inference_time_ms: float
    detokenizer_time_ms: float
    total_time_ms: float
    src_tokens_count: int
    tgt_tokens_count: int
    raw_tokens: List[str] = field(default_factory=list)


@dataclass
class MTModelInfo:
    engine_name: str
    model_name: str
    model_family: str
    quantization: str
    model_size_mb: float
    src_lang: str
    tgt_lang: str
    is_multilingual: bool
    parameters: Dict[str, Any] = field(default_factory=dict)


class MTEngine(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Loads model weights and tokenizers into memory."""
        pass

    @abstractmethod
    def translate(
        self,
        text: str,
        beam_size: int = 1,
        max_decoding_length: int = 256
    ) -> TranslationResult:
        """Translates a single source text."""
        pass

    @abstractmethod
    def translate_batch(
        self,
        texts: List[str],
        beam_size: int = 1,
        max_decoding_length: int = 256
    ) -> List[TranslationResult]:
        """Translates a batch of source texts."""
        pass

    @abstractmethod
    def get_model_info(self) -> MTModelInfo:
        """Returns metadata about the engine and underlying model."""
        pass
