"""
test_e2e_streaming.py - Full end-to-end integration test from audio WAV -> S2 ASR -> S4 MT -> S5 Wire format.
"""

import os
import pytest
import wave
import json
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


@pytest.mark.skipif(not S2_MODEL_DIR.exists() or not S3_MODEL_DIR.exists() or not WAV_PATH.exists(),
                    reason="Model directories or audio test fixture missing")
def test_s5_e2e_streaming_audio_pipeline():
    asr_engine = get_s2_asr_engine(str(S2_MODEL_DIR), num_threads=2)
    mt_engine = get_s3_marian_engine(str(S3_MODEL_DIR), num_threads=2)

    runtime = StreamingTranslationRuntime(asr_engine=asr_engine, mt_engine=mt_engine, k=2, buffer=2)
    runtime.start()

    emitted_messages = []

    with wave.open(str(WAV_PATH), "rb") as wf:
        chunk_samples = int(16000 * 0.128)  # 128ms chunks
        while True:
            raw_frames = wf.readframes(chunk_samples)
            if not raw_frames:
                break
            resp = runtime.process_pcm_chunk(raw_frames)
            if resp:
                validated = parse_and_validate_wire_message(resp)
                emitted_messages.append(validated)

    # Flush segment at endpoint
    final_resp = runtime.finalize_stream()
    if final_resp:
        validated = parse_and_validate_wire_message(final_resp)
        emitted_messages.append(validated)

    # Must have produced valid wire protocol messages
    assert len(emitted_messages) > 0

    # Validate message structure and monotonicity
    prev_committed = ""
    for msg in emitted_messages:
        assert msg["version"] == "1.0"
        assert msg["type"] in ("subtitle.update", "subtitle.final")
        assert "committed_text" in msg
        assert "provisional_text" in msg

        # Invariant: committed_text must start with previous committed_text within segment 1
        if msg["segment_id"] == 1:
            curr_committed = msg["committed_text"]
            if curr_committed and prev_committed:
                assert curr_committed.startswith(prev_committed), f"Committed mutated: '{curr_committed}' vs '{prev_committed}'"
            if curr_committed:
                prev_committed = curr_committed

    final_msg = emitted_messages[-1]
    assert final_msg["is_final"] is True
    assert len(final_msg["committed_text"]) > 0
