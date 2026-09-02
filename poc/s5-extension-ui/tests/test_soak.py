"""
test_soak.py - Tier G: Long-running Soak & Memory Stability Test.
Simulates continuous multi-segment live stream audio translation and monitors RSS memory stability.
"""

import os
import psutil
import time
import wave
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


def get_current_rss_mb() -> float:
    proc = psutil.Process(os.getpid())
    return proc.memory_info().rss / (1024.0 * 1024.0)


def test_sustained_streaming_soak_memory_stability():
    asr_engine = get_s2_asr_engine(str(S2_MODEL_DIR), num_threads=2)
    mt_engine = get_s3_marian_engine(str(S3_MODEL_DIR), num_threads=2)

    runtime = StreamingTranslationRuntime(asr_engine=asr_engine, mt_engine=mt_engine, k=2, buffer=2)
    runtime.start()

    with wave.open(str(WAV_PATH), "rb") as wf:
        audio_bytes = wf.readframes(wf.getnframes())

    chunk_size = int(16000 * 2 * 0.128)  # 128ms in 16-bit PCM bytes
    iterations = 15  # 15 segments of full speech replay

    initial_rss = get_current_rss_mb()
    total_events = 0
    t_start = time.perf_counter()

    for it in range(iterations):
        offset = 0
        while offset < len(audio_bytes):
            chunk = audio_bytes[offset:offset + chunk_size]
            resp = runtime.process_pcm_chunk(chunk)
            if resp:
                _ = parse_and_validate_wire_message(resp)
                total_events += 1
            offset += chunk_size

        final_resp = runtime.finalize_stream()
        if final_resp:
            _ = parse_and_validate_wire_message(final_resp)
            total_events += 1

    total_time = time.perf_counter() - t_start
    final_rss = get_current_rss_mb()
    rss_delta = final_rss - initial_rss

    print(f"\n[Soak Test Summary] Iterations: {iterations} | Total Events: {total_events} | Total Time: {total_time:.2f}s")
    print(f"Initial RSS: {initial_rss:.2f} MB | Final RSS: {final_rss:.2f} MB | Delta: {rss_delta:+.2f} MB")

    # RSS growth over 15 iterations must be bounded (< 80 MB variance)
    assert rss_delta < 80.0, f"Unbounded memory growth detected: +{rss_delta:.2f} MB"
    assert total_events > 100, f"Expected > 100 events, got {total_events}"
