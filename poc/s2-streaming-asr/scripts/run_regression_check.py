#!/usr/bin/env python3
"""
run_regression_check.py - Automated regression test & baseline gate for S2 streaming ASR.
Asserts that correctness tests, latency, throughput, accuracy, and memory remain within s2_performance_contract_v1.
"""

import sys
import os
import json
import subprocess
import numpy as np
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.sherpa_onnx_engine import SherpaOnnxStreamingEngine
from benchmark.replay import run_deterministic_stream_benchmark

POC_DIR = Path(__file__).parent.parent
MODELS_DIR = POC_DIR / "models"
DATASETS_DIR = POC_DIR / "datasets"
CONTRACT_PATH = POC_DIR / "s2_performance_contract_v1.json"


def load_contract():
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(f"Contract file not found at {CONTRACT_PATH}")
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_unit_tests():
    print("\n[Gate 0/3] Executing Unit & Integration Tests via Pytest...")
    test_dir = str(POC_DIR / "tests")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(POC_DIR)
    
    cmd = [sys.executable, "-m", "pytest", test_dir, "-q"]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if res.returncode != 0:
        print("FAIL: Unit tests failed!")
        print(res.stdout)
        print(res.stderr)
        return False, ["Unit test suite failed"]
    
    print("PASS: All unit tests passed.")
    return True, []


def run_regression_gates():
    print("=" * 66)
    print("  STAGE S2 REGRESSION PROTECTION & PERFORMANCE GATE (CONTRACT v1) ")
    print("=" * 66)

    contract = load_contract()
    thresh = contract["thresholds"]

    failures = []

    # Gate 0: Correctness
    tests_ok, test_fails = run_unit_tests()
    if not tests_ok:
        failures.extend(test_fails)

    en_model_dir = str(MODELS_DIR / "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17")
    ja_model_dir = str(MODELS_DIR / "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10")

    # Gate 1: English Zipformer
    print("\n[Gate 1/3] Checking English Zipformer (EN-20M)...")
    engine_en = SherpaOnnxStreamingEngine(en_model_dir, language="en", num_threads=thresh["resource"]["max_cpu_threads"])
    engine_en.initialize()

    res_en = run_deterministic_stream_benchmark(
        engine=engine_en,
        wav_path=str(DATASETS_DIR / "en_clean_speech.wav"),
        reference_text="AFTER EARLY NIGHTFALL THE YELLOW LAMPS WOULD LIGHT UP HERE AND THERE THE SQUALID QUARTER OF THE BROTHELS",
        language="en",
        chunk_ms=128
    )

    en_ttft = res_en["realtime_metrics"]["ttft_ms"]
    en_rtf = res_en["realtime_metrics"]["rtf"]
    en_wer = res_en["accuracy_metrics"]["wer"]
    en_spr = res_en["stability_metrics"]["average_stable_prefix_ratio"]
    en_rev = res_en["stability_metrics"]["revision_count"]

    max_en_ttft = thresh["latency"]["en_ttft_p95_max_ms"]
    max_en_rtf = thresh["throughput"]["en_rtf_max"]
    max_en_wer = thresh["accuracy_fixtures"]["en_clean_wer_max"]
    min_spr = thresh["stability"]["stable_prefix_ratio_min"]
    max_rev = thresh["stability"]["destructive_revisions_allowed"]

    print(f"  Measured: TTFT={en_ttft:.1f}ms (Limit: <{max_en_ttft}ms), RTF={en_rtf:.4f} (Limit: <{max_en_rtf}), WER={en_wer:.2f} (Limit: <{max_en_wer}), SPR={en_spr:.2f}, Rev={en_rev}")

    if en_ttft > max_en_ttft:
        failures.append(f"EN TTFT regression: {en_ttft:.1f}ms > {max_en_ttft}ms")
    if en_rtf > max_en_rtf:
        failures.append(f"EN RTF regression: {en_rtf:.4f} > {max_en_rtf}")
    if en_wer > max_en_wer:
        failures.append(f"EN WER regression: {en_wer:.2f} > {max_en_wer}")
    if en_spr < min_spr:
        failures.append(f"EN SPR regression: {en_spr:.2f} < {min_spr}")
    if en_rev > max_rev:
        failures.append(f"EN destructive revisions: {en_rev} > {max_rev}")

    # Gate 2: Japanese Multilingual Zipformer
    print("\n[Gate 2/3] Checking Japanese Multilingual Zipformer...")
    engine_ja = SherpaOnnxStreamingEngine(ja_model_dir, language="multilingual", num_threads=thresh["resource"]["max_cpu_threads"])
    engine_ja.initialize()

    res_ja = run_deterministic_stream_benchmark(
        engine=engine_ja,
        wav_path=str(DATASETS_DIR / "ja_conversational.wav"),
        reference_text="持ち主とはぐれた傘が風で舞い看板もなぎ倒されてしまったようです",
        language="ja",
        chunk_ms=128
    )

    ja_ttft = res_ja["realtime_metrics"]["ttft_ms"]
    ja_rtf = res_ja["realtime_metrics"]["rtf"]
    ja_cer = res_ja["accuracy_metrics"]["cer"]
    ja_spr = res_ja["stability_metrics"]["average_stable_prefix_ratio"]
    ja_rev = res_ja["stability_metrics"]["revision_count"]

    max_ja_ttft = thresh["latency"]["ja_ttft_p95_max_ms"]
    max_ja_rtf = thresh["throughput"]["ja_rtf_max"]
    max_ja_cer = thresh["accuracy_fixtures"]["ja_news_cer_max"]

    print(f"  Measured: TTFT={ja_ttft:.1f}ms (Limit: <{max_ja_ttft}ms), RTF={ja_rtf:.4f} (Limit: <{max_ja_rtf}), CER={ja_cer:.2f} (Limit: <{max_ja_cer}), SPR={ja_spr:.2f}, Rev={ja_rev}")

    if ja_ttft > max_ja_ttft:
        failures.append(f"JA TTFT regression: {ja_ttft:.1f}ms > {max_ja_ttft}ms")
    if ja_rtf > max_ja_rtf:
        failures.append(f"JA RTF regression: {ja_rtf:.4f} > {max_ja_rtf}")
    if ja_cer > max_ja_cer:
        failures.append(f"JA CER regression: {ja_cer:.2f} > {max_ja_cer}")
    if ja_spr < min_spr:
        failures.append(f"JA SPR regression: {ja_spr:.2f} < {min_spr}")
    if ja_rev > max_rev:
        failures.append(f"JA destructive revisions: {ja_rev} > {max_rev}")

    # Gate 3: Memory & Resource Bounds
    print("\n[Gate 3/3] Checking Memory & Resource Bounds...")
    process = psutil.Process(os.getpid())
    current_rss_mb = process.memory_info().rss / (1024 * 1024)
    max_rss = thresh["resource"]["peak_rss_max_mb"]
    print(f"  Measured RSS: {current_rss_mb:.1f} MB (Limit: <{max_rss} MB)")

    if current_rss_mb > max_rss:
        failures.append(f"Peak RSS breach: {current_rss_mb:.1f} MB > {max_rss} MB")

    print("\n" + "=" * 66)
    if failures:
        print("  REGRESSION GATE RESULT: FAILED (Violations Detected)")
        for f in failures:
            print(f"  ❌ {f}")
        print("=" * 66)
        sys.exit(1)
    else:
        print("  REGRESSION GATE RESULT: ALL CONTRACT GATES PASSED (PASS)")
        print("=" * 66)
        sys.exit(0)


if __name__ == "__main__":
    run_regression_gates()
