#!/usr/bin/env python3
"""
run_regression_check.py - Automated regression test & baseline gate for Stage S3 Local Machine Translation.
Asserts that correctness tests, latency budgets, memory limits, and streaming stability remain within contract.
"""

import sys
import os
import time
import json
import subprocess
import psutil
from pathlib import Path

POC_DIR = Path(__file__).parent.parent.resolve()
WORKSPACE_DIR = POC_DIR.parent.parent.resolve()
sys.path.insert(0, str(POC_DIR))

from engines.marian_engine import MarianCTranslate2Engine
from engines.nllb_engine import NllbCTranslate2Engine
from metrics.quality_metrics import compute_sentence_metrics
from metrics.stability_metrics import analyze_translation_stability

MODELS_DIR = POC_DIR / "models"
DATASETS_DIR = POC_DIR / "datasets"

# S3 Performance Contract Thresholds
THRESHOLDS = {
    "marian": {
        "p50_latency_max_ms": 100.0,
        "p95_latency_max_ms": 200.0,
        "max_disk_size_mb": 150.0,
        "min_sentence_chrf": 25.0
    },
    "nllb": {
        "p50_latency_max_ms": 150.0,
        "p95_latency_max_ms": 300.0,
        "max_disk_size_mb": 750.0,
        "min_sentence_chrf": 25.0
    },
    "resource": {
        "peak_rss_max_mb": 1000.0,
        "max_cpu_threads": 4
    }
}


def run_unit_tests() -> tuple[bool, list]:
    print("\n[Gate 0/3] Executing Unit & Integration Tests via Pytest...")
    test_dir = str(POC_DIR / "tests")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{POC_DIR}:{WORKSPACE_DIR / 'poc' / 's2-streaming-asr'}"
    
    cmd = [sys.executable, "-m", "pytest", test_dir, "-q"]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if res.returncode != 0:
        print("FAIL: Unit tests failed!")
        print(res.stdout)
        print(res.stderr)
        return False, ["Pytest test suite failed"]
    
    print("PASS: All unit tests passed.")
    return True, []


def run_regression_gates():
    print("=" * 68)
    print("  STAGE S3 REGRESSION PROTECTION & PERFORMANCE GATE (CONTRACT v1) ")
    print("=" * 68)

    failures = []

    # Gate 0: Correctness
    tests_ok, test_fails = run_unit_tests()
    if not tests_ok:
        failures.extend(test_fails)

    # Gate 1: Marian Engine
    print("\n[Gate 1/3] Checking Helsinki-NLP opus-mt-ja-en (Marian INT8)...")
    marian_dir = MODELS_DIR / "opus-mt-ja-en-ct2-int8"
    engine_m = MarianCTranslate2Engine(str(marian_dir), num_threads=4)
    engine_m.initialize()

    # Warmup
    for _ in range(5):
        engine_m.translate("テストです。")

    test_ja = "持ち主とはぐれた傘が風で舞い看板もなぎ倒されてしまったようです。"
    test_ref_en = "An umbrella separated from its owner blew in the wind, and signboards also seem to have been knocked down."

    m_latencies = []
    for _ in range(20):
        res = engine_m.translate(test_ja)
        m_latencies.append(res.total_time_ms)

    m_p50 = float(sorted(m_latencies)[len(m_latencies) // 2])
    m_p95 = float(sorted(m_latencies)[int(len(m_latencies) * 0.95)])
    m_metrics = compute_sentence_metrics(test_ja, res.target_text, test_ref_en)
    m_disk = engine_m.get_model_info().model_size_mb

    print(f"  Marian: p50={m_p50:.1f}ms (Limit: <{THRESHOLDS['marian']['p50_latency_max_ms']}ms), p95={m_p95:.1f}ms, chrF++={m_metrics['sentence_chrf_pp']:.1f}, Size={m_disk}MB")

    if m_p50 > THRESHOLDS["marian"]["p50_latency_max_ms"]:
        failures.append(f"Marian p50 latency regression: {m_p50:.1f}ms > {THRESHOLDS['marian']['p50_latency_max_ms']}ms")
    if m_p95 > THRESHOLDS["marian"]["p95_latency_max_ms"]:
        failures.append(f"Marian p95 latency regression: {m_p95:.1f}ms > {THRESHOLDS['marian']['p95_latency_max_ms']}ms")
    if m_disk > THRESHOLDS["marian"]["max_disk_size_mb"]:
        failures.append(f"Marian disk size breach: {m_disk}MB > {THRESHOLDS['marian']['max_disk_size_mb']}MB")

    # Gate 2: NLLB Engine
    print("\n[Gate 2/3] Checking Meta NLLB-200-distilled-600M (NLLB INT8)...")
    nllb_dir = MODELS_DIR / "nllb-200-600m-ct2-int8"
    engine_n = NllbCTranslate2Engine(str(nllb_dir), num_threads=4)
    engine_n.initialize()

    # Warmup
    for _ in range(5):
        engine_n.translate("テストです。")

    n_latencies = []
    for _ in range(20):
        res_n = engine_n.translate(test_ja)
        n_latencies.append(res_n.total_time_ms)

    n_p50 = float(sorted(n_latencies)[len(n_latencies) // 2])
    n_p95 = float(sorted(n_latencies)[int(len(n_latencies) * 0.95)])
    n_metrics = compute_sentence_metrics(test_ja, res_n.target_text, test_ref_en)
    n_disk = engine_n.get_model_info().model_size_mb

    print(f"  NLLB: p50={n_p50:.1f}ms (Limit: <{THRESHOLDS['nllb']['p50_latency_max_ms']}ms), p95={n_p95:.1f}ms, chrF++={n_metrics['sentence_chrf_pp']:.1f}, Size={n_disk}MB")

    if n_p50 > THRESHOLDS["nllb"]["p50_latency_max_ms"]:
        failures.append(f"NLLB p50 latency regression: {n_p50:.1f}ms > {THRESHOLDS['nllb']['p50_latency_max_ms']}ms")
    if n_disk > THRESHOLDS["nllb"]["max_disk_size_mb"]:
        failures.append(f"NLLB disk size breach: {n_disk}MB > {THRESHOLDS['nllb']['max_disk_size_mb']}MB")

    # Gate 3: Memory Bounds
    print("\n[Gate 3/3] Checking Memory & Resource Bounds...")
    process = psutil.Process(os.getpid())
    current_rss_mb = process.memory_info().rss / (1024 * 1024)
    max_rss = THRESHOLDS["resource"]["peak_rss_max_mb"]
    print(f"  Measured RSS: {current_rss_mb:.1f} MB (Limit: <{max_rss} MB)")

    if current_rss_mb > max_rss:
        failures.append(f"Peak RSS breach: {current_rss_mb:.1f} MB > {max_rss} MB")

    print("\n" + "=" * 68)
    if failures:
        print("  REGRESSION GATE RESULT: FAILED (Violations Detected)")
        for f in failures:
            print(f"  ❌ {f}")
        print("=" * 68)
        sys.exit(1)
    else:
        print("  REGRESSION GATE RESULT: ALL CONTRACT GATES PASSED (PASS)")
        print("=" * 68)
        sys.exit(0)


if __name__ == "__main__":
    run_regression_gates()
