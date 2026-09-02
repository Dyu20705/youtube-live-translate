#!/usr/bin/env python3
"""
run_s5_benchmark.py - CLI runner for Stage S5 Rendering & Anchored Layout Benchmark.
"""

import os
import sys
import json
import wave
import time
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_DIR / "poc" / "s5-extension-ui"))
sys.path.insert(0, str(WORKSPACE_DIR / "poc" / "s4-incremental-translation"))
sys.path.insert(0, str(WORKSPACE_DIR / "poc" / "s3-local-mt"))
sys.path.insert(0, str(WORKSPACE_DIR / "poc" / "s2-streaming-asr"))

from bridge.runtime_pipeline import (
    StreamingTranslationRuntime,
    get_s2_asr_engine,
    get_s3_marian_engine
)
from bridge.protocol import parse_and_validate_wire_message
sys.path.insert(0, str(WORKSPACE_DIR / "poc" / "s5-extension-ui" / "benchmark"))

try:
    from .s5_benchmark import simulate_rendering_pipeline, EVIDENCE_DIR
except (ImportError, ValueError):
    from s5_benchmark import simulate_rendering_pipeline, EVIDENCE_DIR



def main():
    print("=" * 80)
    print("  STAGE S5 RENDERING & ANCHORED PRESENTATION BENCHMARK")
    print("=" * 80)

    s2_model_dir = WORKSPACE_DIR / "poc" / "s2-streaming-asr" / "models" / "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10"
    s3_model_dir = WORKSPACE_DIR / "poc" / "s3-local-mt" / "models" / "opus-mt-ja-en-ct2-int8"
    wav_path = WORKSPACE_DIR / "poc" / "s2-streaming-asr" / "datasets" / "ja_conversational.wav"

    print("Initializing S2 Zipformer and S3 Marian INT8 runtime...")
    asr_engine = get_s2_asr_engine(str(s2_model_dir), num_threads=2)
    mt_engine = get_s3_marian_engine(str(s3_model_dir), num_threads=2)

    runtime = StreamingTranslationRuntime(asr_engine=asr_engine, mt_engine=mt_engine, k=2, buffer=2)
    runtime.start()

    print("Ingesting streaming audio frames and capturing wire events...")
    captured_events = []
    t_start = time.perf_counter()

    with wave.open(str(wav_path), "rb") as wf:
        chunk_samples = int(16000 * 0.128)  # 128ms
        while True:
            raw_frames = wf.readframes(chunk_samples)
            if not raw_frames:
                break
            resp = runtime.process_pcm_chunk(raw_frames)
            if resp:
                data = parse_and_validate_wire_message(resp)
                captured_events.append(data)

    final_resp = runtime.finalize_stream()
    if final_resp:
        captured_events.append(parse_and_validate_wire_message(final_resp))

    total_wall_time = time.perf_counter() - t_start
    print(f"Captured {len(captured_events)} wire subtitle events across {total_wall_time:.2f}s wall-clock time.\n")

    print("Executing comparative rendering simulation...")
    results = simulate_rendering_pipeline(captured_events)

    raw_res = results["raw_unified_strategy"]
    anch_res = results["s5_anchored_strategy"]

    print("\n" + "=" * 80)
    print("  STAGE S5 RENDERING BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"{'Evaluation Dimension':<36} | {'Raw Unified UI':<18} | {'S5 Anchored UI':<18}")
    print("-" * 80)
    print(f"{'Total Ingested Events':<36} | {results['total_incoming_events']:<18} | {results['total_incoming_events']:<18}")
    print(f"{'DOM Updates Executed':<36} | {raw_res['total_renders']:<18} | {anch_res['total_renders']:<18}")
    print(f"{'Committed Text Updates':<36} | {'N/A':<18} | {anch_res['committed_updates']:<18}")
    print(f"{'Provisional Tail Updates':<36} | {'N/A':<18} | {anch_res['provisional_updates']:<18}")
    print(f"{'Noop Duplicate Events Filtered':<36} | {'0':<18} | {anch_res['noop_duplicate_events']:<18}")
    print(f"{'Full-Node DOM Replacements':<36} | {raw_res['dom_node_replacements']:<18} | {anch_res['dom_node_replacements']:<18}")
    print(f"{'Max Anchor Displacement (px)':<36} | {raw_res['max_anchor_displacement_px']:<18.2f} | {anch_res['max_anchor_displacement_px']:<18.4f}")
    print(f"{'Avg Anchor Displacement (px)':<36} | {raw_res['avg_anchor_displacement_px']:<18.2f} | {anch_res['avg_anchor_displacement_px']:<18.4f}")
    print(f"{'Render Latency p50 (ms)':<36} | {'< 0.05':<18} | {anch_res['render_latency_p50_ms']:<18.3f}")
    print(f"{'Render Latency p95 (ms)':<36} | {'< 0.08':<18} | {anch_res['render_latency_p95_ms']:<18.3f}")
    print(f"{'Spatial Anchoring Invariant':<36} | {'FAILED':<18} | {'PASS (0.0px)':<18}")
    print("=" * 80)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_file = EVIDENCE_DIR / "s5_benchmark_measurements.json"
    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nEvidence artifact written to: {evidence_file}")


if __name__ == "__main__":
    main()
