"""
Unit tests for MarianCTranslate2Engine.
"""

import pytest
from pathlib import Path
from engines.marian_engine import MarianCTranslate2Engine

MODELS_DIR = Path(__file__).parent.parent / "models"
MARIAN_DIR = MODELS_DIR / "opus-mt-ja-en-ct2-int8"


@pytest.fixture(scope="module")
def marian_engine():
    engine = MarianCTranslate2Engine(str(MARIAN_DIR), num_threads=2)
    engine.initialize()
    return engine


def test_marian_initialization(marian_engine):
    info = marian_engine.get_model_info()
    assert info.engine_name == "CTranslate2-Marian"
    assert info.model_name == "opus-mt-ja-en"
    assert info.quantization == "int8"
    assert info.model_size_mb > 0


def test_marian_empty_input(marian_engine):
    res = marian_engine.translate("")
    assert res.target_text == ""
    assert res.src_tokens_count == 0


def test_marian_simple_translation(marian_engine):
    res = marian_engine.translate("こんにちは。")
    assert len(res.target_text) > 0
    assert any(k in res.target_text.lower() for k in ["hi", "hello", "good afternoon"])
    assert res.total_time_ms > 0
    assert res.src_tokens_count > 0
    assert res.tgt_tokens_count > 0


def test_marian_batch_translation(marian_engine):
    texts = ["ありがとう。", "はい。"]
    results = marian_engine.translate_batch(texts)
    assert len(results) == 2
    assert "thank" in results[0].target_text.lower()
    assert len(results[1].target_text) > 0
