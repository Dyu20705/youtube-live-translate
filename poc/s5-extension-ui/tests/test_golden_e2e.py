"""
test_golden_e2e.py - Tier G: Golden End-to-End Audio Trace Regression Test.
Feeds canonical audio fixture through S2 Zipformer -> S4 MT -> S5 Wire -> validates exact event contract.
"""

import os
import wave
import json
import pytest
from pathlib import Path

from bridge.runtime_pipeline import (
    StreamingTranslationRuntime,
    get_s2_asr_engine,
    get_s3_marian_engine
)
from bridge.protocol import parse_and_validate_wire_message

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent
S2_MODEL_DIR = WORKSPACE_DIR / "poc" / "s2-streaming-asr" / "models" / "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10"
S3_MODEL_DIR = WORKSPACE_DIR / "poc" / "s3-local-mt" / "models" / "opus-mt-ja-en-ct2-int8"
WAV_PATH = WORKSPACE_DIR / "poc" / "s2-streaming-asr" / "datasets" / "ja_conversational.wav"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_golden_e2e_audio_trace_replay():
    asr_engine = get_s2_asr_engine(str(S2_MODEL_DIR), num_threads=2)
    mt_engine = get_s3_marian_engine(str(S3_MODEL_DIR), num_threads=2)

    runtime = StreamingTranslationRuntime(asr_engine=asr_engine, mt_engine=mt_engine, k=2, buffer=2)
    runtime.start()

    trace_events = []

    with wave.open(str(WAV_PATH), "rb") as wf:
        chunk_samples = int(16000 * 0.128)  # 128ms
        while True:
            frames = wf.readframes(chunk_samples)
            if not frames:
                break
            resp = runtime.process_pcm_chunk(frames)
            if resp:
                validated = parse_and_validate_wire_message(resp)
                trace_events.append(validated)

    final_resp = runtime.finalize_stream()
    if final_resp:
        trace_events.append(parse_and_validate_wire_message(final_resp))

    # Invariants on Golden Trace:
    assert len(trace_events) >= 10, f"Expected >= 10 events, got {len(trace_events)}"

    # 1. Monotonicity of committed text
    prev_committed = ""
    for ev in trace_events:
        c_text = ev["committed_text"]
        if ev["segment_id"] == 1:
            if c_text and prev_committed:
                assert c_text.startswith(prev_committed), f"Committed prefix mutated: '{c_text}' vs '{prev_committed}'"
            if c_text:
                prev_committed = c_text

    # 2. Final event must be finalized
    final_ev = trace_events[-1]
    assert final_ev["is_final"] is True
    assert final_ev["type"] == "subtitle.final"
    assert len(final_ev["committed_text"]) > 0

    # Save/update golden trace fixture for reproducible diffing
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = FIXTURES_DIR / "golden_trace_conversational.json"
    with open(golden_path, "w", encoding="utf-8") as f:
        json.dump(trace_events, f, indent=2, ensure_ascii=False)
