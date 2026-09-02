"""
Integration tests for End-to-End S2 ASR -> S3 MT streaming pipeline.
"""

import pytest
from pathlib import Path
import sys

POC_DIR = Path(__file__).parent.parent.resolve()
WORKSPACE_DIR = POC_DIR.parent.parent.resolve()
S2_DIR = WORKSPACE_DIR / "poc" / "s2-streaming-asr"

from engines.marian_engine import MarianCTranslate2Engine
from benchmark.e2e_s2_s3_runner import run_e2e_streaming_pipeline, get_s2_sherpa_engine_class

MODELS_DIR = POC_DIR / "models"
S2_MODELS_DIR = S2_DIR / "models"
S2_DATASETS_DIR = S2_DIR / "datasets"


def test_e2e_streaming_pipeline_marian():
    ja_asr_model = S2_MODELS_DIR / "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10"
    marian_model = MODELS_DIR / "opus-mt-ja-en-ct2-int8"
    wav_path = S2_DATASETS_DIR / "ja_conversational.wav"

    assert ja_asr_model.exists()
    assert marian_model.exists()
    assert wav_path.exists()

    SherpaOnnxStreamingEngine = get_s2_sherpa_engine_class()
    asr_engine = SherpaOnnxStreamingEngine(str(ja_asr_model), language="multilingual", num_threads=2)
    asr_engine.initialize()

    mt_engine = MarianCTranslate2Engine(str(marian_model), num_threads=2)
    mt_engine.initialize()

    res = run_e2e_streaming_pipeline(
        asr_engine=asr_engine,
        mt_engine=mt_engine,
        wav_path=str(wav_path),
        reference_ja="持ち主とはぐれた傘が風で舞い看板もなぎ倒されてしまったようです。",
        reference_en="An umbrella separated from its owner blew in the wind, and signboards also seem to have been knocked down.",
        chunk_ms=256
    )

    assert res["audio_duration_sec"] > 0
    assert len(res["timeline_events"]) > 0
    assert res["real_time_factor"] < 0.50
    assert len(res["transcripts"]["mt_final_en"]) > 0
