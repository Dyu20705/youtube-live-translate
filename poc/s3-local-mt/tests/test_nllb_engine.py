"""
Unit tests for NllbCTranslate2Engine.
"""

import pytest
from pathlib import Path
from engines.nllb_engine import NllbCTranslate2Engine

MODELS_DIR = Path(__file__).parent.parent / "models"
NLLB_DIR = MODELS_DIR / "nllb-200-600m-ct2-int8"


@pytest.fixture(scope="module")
def nllb_engine():
    engine = NllbCTranslate2Engine(str(NLLB_DIR), num_threads=2)
    engine.initialize()
    return engine


def test_nllb_initialization(nllb_engine):
    info = nllb_engine.get_model_info()
    assert info.engine_name == "CTranslate2-NLLB"
    assert info.model_name == "nllb-200-distilled-600M"
    assert info.quantization == "int8"
    assert info.is_multilingual is True


def test_nllb_empty_input(nllb_engine):
    res = nllb_engine.translate("")
    assert res.target_text == ""
    assert res.src_tokens_count == 0


def test_nllb_simple_translation(nllb_engine):
    res = nllb_engine.translate("こんにちは。")
    assert len(res.target_text) > 0
    assert any(k in res.target_text.lower() for k in ["hey", "hello", "hi", "good"])
    assert res.total_time_ms > 0


def test_nllb_batch_translation(nllb_engine):
    texts = ["ありがとう。", "はい。"]
    results = nllb_engine.translate_batch(texts)
    assert len(results) == 2
    assert "thank" in results[0].target_text.lower()
    assert len(results[1].target_text) > 0
