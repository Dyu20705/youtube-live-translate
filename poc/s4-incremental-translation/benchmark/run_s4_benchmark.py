#!/usr/bin/env python3
"""
run_s4_benchmark.py - CLI runner for Stage S4 comparative benchmark and evidence artifact generation.
"""

import sys
import json
import time
from pathlib import Path

POC_S4_DIR = Path(__file__).parent.parent.resolve()
WORKSPACE_DIR = POC_S4_DIR.parent.parent.resolve()
POC_S3_DIR = WORKSPACE_DIR / "poc" / "s3-local-mt"
EVIDENCE_DIR = WORKSPACE_DIR / "docs" / "evidence" / "s4-incremental-translation"

if str(POC_S4_DIR) not in sys.path:
    sys.path.insert(0, str(POC_S4_DIR))
if str(POC_S3_DIR) not in sys.path:
    sys.path.insert(0, str(POC_S3_DIR))

from engines.marian_engine import MarianCTranslate2Engine
from benchmark.s4_benchmark import run_comparative_s4_benchmark


def main():
    print("=" * 76)
    print("  STAGE S4 COMPARATIVE BENCHMARK: S3 BASELINE vs S4 ADAPTIVE FRONTIER")
    print("=" * 76)

    manifest_path = POC_S3_DIR / "datasets" / "manifest.json"
    variants_path = POC_S3_DIR / "datasets" / "partial_variants.json"
    model_dir = POC_S3_DIR / "models" / "opus-mt-ja-en-ct2-int8"

    if not manifest_path.exists() or not variants_path.exists():
        print(f"Error: Dataset not found in {POC_S3_DIR / 'datasets'}")
        sys.exit(1)

    if not model_dir.exists():
        print(f"Error: Marian INT8 model not found at {model_dir}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        corpus_items = json.load(f)
    with open(variants_path, "r", encoding="utf-8") as f:
        partial_variants = json.load(f)

    print(f"Loaded {len(corpus_items)} corpus items and {len(partial_variants)} variants.")
    print("Initializing Marian CTranslate2 INT8 engine...")

    engine = MarianCTranslate2Engine(str(model_dir), num_threads=2)
    engine.initialize()
    print("Marian engine initialized successfully.\n")

    print("Executing benchmark across S3 baseline and S4 policies (K=1, K=2, K=3)...")
    results = run_comparative_s4_benchmark(
        mt_engine=engine,
        corpus_items=corpus_items,
        partial_variants=partial_variants,
        k_values=[1, 2, 3],
        unstable_buffer=2
    )

    # Print summary table
    print("\n" + "=" * 84)
    print("  EMPIRICAL BENCHMARK SUMMARY (SEPARATED STABILITY DIMENSIONS)")
    print("=" * 84)
    print(f"{'Metric':<36} | {'S3 Naive':<10} | {'S4 (K=1)':<10} | {'S4 (K=2)*':<10} | {'S4 (K=3)':<10}")
    print("-" * 84)

    b = results["baseline_s3_naive"]
    k1 = results["candidates_s4"]["s4_k1"]
    k2 = results["candidates_s4"]["s4_k2"]
    k3 = results["candidates_s4"]["s4_k3"]

    print(f"{'A. Committed Prefix Revisions':<36} | {'N/A':<10} | {k1['committed_prefix_revision_count']:<10} | {k2['committed_prefix_revision_count']:<10} | {k3['committed_prefix_revision_count']:<10}")
    print(f"{'B. Provisional Revisions (Count)':<36} | {'N/A':<10} | {k1['provisional_revision_count']:<10} | {k2['provisional_revision_count']:<10} | {k3['provisional_revision_count']:<10}")
    print(f"{'B. Provisional Revision Rate':<36} | {'N/A':<10} | {k1['provisional_revision_rate']:<10.2f} | {k2['provisional_revision_rate']:<10.2f} | {k3['provisional_revision_rate']:<10.2f}")
    print(f"{'C. Display Destructive Revisions':<36} | {b['destructive_revisions']:<10} | {k1['display_revision_count']:<10} | {k2['display_revision_count']:<10} | {k3['display_revision_count']:<10}")
    print(f"{'C. Display Complete Rewrites':<36} | {b['complete_rewrites']:<10} | {k1['display_complete_rewrite_count']:<10} | {k2['display_complete_rewrite_count']:<10} | {k3['display_complete_rewrite_count']:<10}")
    print(f"{'C. Display TPS (Prefix Agreement)':<36} | {b['average_tps']:<10.4f} | {k1['display_tps']:<10.4f} | {k2['display_tps']:<10.4f} | {k3['display_tps']:<10.4f}")
    print(f"{'Commit Conflicts Recorded':<36} | {'N/A':<10} | {k1['commit_conflict_count']:<10} | {k2['commit_conflict_count']:<10} | {k3['commit_conflict_count']:<10}")
    print(f"{'Frontier Advancements':<36} | {'N/A':<10} | {k1['frontier_advancement_count']:<10} | {k2['frontier_advancement_count']:<10} | {k3['frontier_advancement_count']:<10}")
    print(f"{'Avg Commit Delay (steps)':<36} | {'N/A':<10} | {k1['average_commit_delay_steps']:<10.2f} | {k2['average_commit_delay_steps']:<10.2f} | {k3['average_commit_delay_steps']:<10.2f}")
    print(f"{'p95 Commit Delay (steps)':<36} | {'N/A':<10} | {k1['p95_commit_delay_steps']:<10.2f} | {k2['p95_commit_delay_steps']:<10.2f} | {k3['p95_commit_delay_steps']:<10.2f}")
    print(f"{'Policy Overhead p50 (ms)':<36} | {'0.00':<10} | {k1['policy_overhead_p50_ms']:<10.3f} | {k2['policy_overhead_p50_ms']:<10.3f} | {k3['policy_overhead_p50_ms']:<10.3f}")
    print(f"{'Policy Overhead p95 (ms)':<36} | {'0.00':<10} | {k1['policy_overhead_p95_ms']:<10.3f} | {k2['policy_overhead_p95_ms']:<10.3f} | {k3['policy_overhead_p95_ms']:<10.3f}")
    print(f"{'Total Step Latency p50 (ms)':<36} | {b['step_latency_p50_ms']:<10.2f} | {k1['total_step_p50_ms']:<10.2f} | {k2['total_step_p50_ms']:<10.2f} | {k3['total_step_p50_ms']:<10.2f}")
    print(f"{'Final Quality (chrF++)':<36} | {'Baseline':<10} | {k1['average_final_chrf_pp']:<10.2f} | {k2['average_final_chrf_pp']:<10.2f} | {k3['average_final_chrf_pp']:<10.2f}")
    print("=" * 84)
    print("* S4 (K=2) is the recommended default configuration.\n")


    # 3. Audio Streaming Replay Benchmark
    s2_model_dir = WORKSPACE_DIR / "poc" / "s2-streaming-asr" / "models" / "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10"
    wav_path = WORKSPACE_DIR / "poc" / "s2-streaming-asr" / "datasets" / "ja_conversational.wav"

    if s2_model_dir.exists() and wav_path.exists():
        print("Executing live audio streaming replay (S2 Zipformer -> S4 K=2 -> S3 Marian)...")
        from tests.test_s4_integration import get_s2_sherpa_engine_class
        SherpaOnnxStreamingEngine = get_s2_sherpa_engine_class()
        asr_engine = SherpaOnnxStreamingEngine(str(s2_model_dir), language="multilingual", num_threads=2)
        asr_engine.initialize()

        from benchmark.s4_benchmark import run_streaming_audio_replay_benchmark
        audio_results = run_streaming_audio_replay_benchmark(
            asr_engine=asr_engine,
            mt_engine=engine,
            wav_path=str(wav_path),
            k=2,
            unstable_buffer=2,
            chunk_ms=128
        )
        results["streaming_audio_replay"] = audio_results

        print(f"Audio Duration: {audio_results['audio_duration_sec']}s, Wall-clock: {audio_results['total_wall_time_sec']}s, RTF: {audio_results['real_time_factor']}")
        print(f"Final ASR: {audio_results['final_asr_ja']}")
        print(f"Final Subtitle: {audio_results['final_subtitle_en']}")
        print(f"MT Call Reduction Ratio: {audio_results['session_metrics']['mt_call_reduction_ratio'] * 100:.1f}%")
        print(f"Committed Prefix Revisions: {audio_results['stability_analysis']['committed_prefix_revisions']}")
        print(f"Policy Overhead p50: {audio_results['stability_analysis']['policy_overhead_p50_ms']} ms\n")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_file = EVIDENCE_DIR / "s4_benchmark_measurements.json"
    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Evidence measurements saved to: {evidence_file}")


if __name__ == "__main__":
    main()

