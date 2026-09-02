"""
conftest.py - Test fixtures and mock translation engines for Stage S4 tests.
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any, Optional

WORKSPACE_DIR = Path(__file__).parent.parent.parent.parent.resolve()
POC_S2_DIR = WORKSPACE_DIR / "poc" / "s2-streaming-asr"
POC_S3_DIR = WORKSPACE_DIR / "poc" / "s3-local-mt"
POC_S4_DIR = WORKSPACE_DIR / "poc" / "s4-incremental-translation"


class MockMTEngine:
    """
    Deterministic mock MT engine for unit testing policy edge cases without GPU/CTranslate2.
    """

    def __init__(self, mapping: Optional[Dict[str, str]] = None, default_prefix: str = "Translated: "):
        self.mapping = mapping or {}
        self.default_prefix = default_prefix
        self.call_count = 0
        self.last_query = ""

    def initialize(self) -> None:
        pass

    def translate(self, text: str, beam_size: int = 1, max_decoding_length: int = 256):
        self.call_count += 1
        self.last_query = text

        target = self.mapping.get(text, f"{self.default_prefix}{text}")

        class MockTranslationResult:
            def __init__(self, target_text, source_text):
                self.target_text = target_text
                self.source_text = source_text
                self.tokenizer_time_ms = 0.1
                self.inference_time_ms = 1.0
                self.detokenizer_time_ms = 0.1
                self.total_time_ms = 1.2
                self.src_tokens_count = len(source_text)
                self.tgt_tokens_count = len(target_text.split())
                self.raw_tokens = target_text.split()

        return MockTranslationResult(target, text)


@pytest.fixture
def mock_engine():
    return MockMTEngine()


@pytest.fixture
def marian_int8_engine():
    """
    Loads real Marian CTranslate2 INT8 engine if weights exist.
    """
    model_dir = POC_S3_DIR / "models" / "opus-mt-ja-en-ct2-int8"
    if not model_dir.exists():
        pytest.skip(f"Marian INT8 model not found at {model_dir}")

    from engines.marian_engine import MarianCTranslate2Engine
    engine = MarianCTranslate2Engine(str(model_dir), num_threads=2)
    engine.initialize()
    return engine
