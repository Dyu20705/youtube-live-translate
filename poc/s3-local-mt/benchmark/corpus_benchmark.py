"""
corpus_benchmark.py - Evaluates latency distributions, input-length scaling, and translation quality (Clean vs ASR).
"""

import time
import os
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from ..engines.base import MTEngine
    from ..metrics.latency_tracker import LatencyTracker, compute_distribution_stats
    from ..metrics.quality_metrics import evaluate_translation_quality, compute_sentence_metrics
except (ImportError, ValueError):
    from engines.base import MTEngine
    from metrics.latency_tracker import LatencyTracker, compute_distribution_stats
    from metrics.quality_metrics import evaluate_translation_quality, compute_sentence_metrics


def run_latency_benchmark(
    engine: MTEngine,
    corpus_items: List[Dict[str, Any]],
    measurements_per_item: int = 100,
    warmup_runs: int = 10,
    beam_size: int = 1
) -> Dict[str, Any]:
    """
    Measures cold-start, warm-start, p50, p90, p95, p99, max latencies and phase breakdown.
    """
    model_info = engine.get_model_info()
    tracker = LatencyTracker()

    # 1. Cold start measurement (first translation on clean instance)
    cold_start_text = "こんにちは。"
    t0 = time.perf_counter()
    res_cold = engine.translate(cold_start_text, beam_size=beam_size)
    cold_duration_ms = (time.perf_counter() - t0) * 1000.0
    tracker.set_cold_start(cold_duration_ms)

    # 2. Warm-up runs
    for _ in range(warmup_runs):
        engine.translate("テストの文章です。", beam_size=beam_size)

    # 3. Benchmark across corpus items
    per_bucket_latencies: Dict[str, List[float]] = {
        "1-10": [],
        "11-30": [],
        "31-60": [],
        "61-120": [],
        ">120": []
    }
    
    per_bucket_breakdown: Dict[str, Dict[str, List[float]]] = {
        b: {"tokenizer": [], "inference": [], "detokenizer": []}
        for b in per_bucket_latencies
    }

    # Group items by length bucket
    for item in corpus_items:
        bucket = item["length_bucket"]
        src_text = item["reference_ja"]
        
        # Collect measurements
        for _ in range(measurements_per_item):
            res = engine.translate(src_text, beam_size=beam_size)
            tracker.record_run(
                total_ms=res.total_time_ms,
                tok_ms=res.tokenizer_time_ms,
                infer_ms=res.inference_time_ms,
                detok_ms=res.detokenizer_time_ms
            )
            if bucket in per_bucket_latencies:
                per_bucket_latencies[bucket].append(res.total_time_ms)
                per_bucket_breakdown[bucket]["tokenizer"].append(res.tokenizer_time_ms)
                per_bucket_breakdown[bucket]["inference"].append(res.inference_time_ms)
                per_bucket_breakdown[bucket]["detokenizer"].append(res.detokenizer_time_ms)

    overall_stats = tracker.compute_summary()
    
    bucket_summary = {}
    for b, lat_list in per_bucket_latencies.items():
        if lat_list:
            bucket_summary[b] = {
                "total": compute_distribution_stats(lat_list),
                "tokenizer": compute_distribution_stats(per_bucket_breakdown[b]["tokenizer"]),
                "inference": compute_distribution_stats(per_bucket_breakdown[b]["inference"]),
                "detokenizer": compute_distribution_stats(per_bucket_breakdown[b]["detokenizer"])
            }

    return {
        "engine": model_info.engine_name,
        "model_name": model_info.model_name,
        "quantization": model_info.quantization,
        "parameters": model_info.parameters,
        "beam_size": beam_size,
        "overall_latency": overall_stats,
        "length_scaling": bucket_summary
    }


def run_quality_benchmark(
    engine: MTEngine,
    corpus_items: List[Dict[str, Any]],
    beam_size: int = 1
) -> Dict[str, Any]:
    """
    Evaluates translation quality for:
    Path A: Clean Japanese (reference_ja -> English)
    Path B: Realistic ASR (asr_ja -> English)
    """
    clean_srcs = [item["reference_ja"] for item in corpus_items]
    asr_srcs = [item["asr_ja"] for item in corpus_items]
    refs_en = [item["reference_en"] for item in corpus_items]

    # Path A: Clean
    clean_hyps = []
    clean_items_detail = []
    for item in corpus_items:
        res = engine.translate(item["reference_ja"], beam_size=beam_size)
        clean_hyps.append(res.target_text)
        sent_m = compute_sentence_metrics(item["reference_ja"], res.target_text, item["reference_en"])
        clean_items_detail.append({
            "id": item["id"],
            "category": item["category"],
            "source_clean": item["reference_ja"],
            "reference_en": item["reference_en"],
            "hypothesis_en": res.target_text,
            "metrics": sent_m
        })

    quality_clean = evaluate_translation_quality(clean_srcs, clean_hyps, refs_en)

    # Path B: Realistic ASR
    asr_hyps = []
    asr_items_detail = []
    for item in corpus_items:
        res = engine.translate(item["asr_ja"], beam_size=beam_size)
        asr_hyps.append(res.target_text)
        sent_m = compute_sentence_metrics(item["asr_ja"], res.target_text, item["reference_en"])
        asr_items_detail.append({
            "id": item["id"],
            "category": item["category"],
            "source_asr": item["asr_ja"],
            "reference_en": item["reference_en"],
            "hypothesis_en": res.target_text,
            "metrics": sent_m
        })

    quality_asr = evaluate_translation_quality(asr_srcs, asr_hyps, refs_en)

    return {
        "path_a_clean": {
            "aggregate_metrics": quality_clean,
            "sample_details": clean_items_detail
        },
        "path_b_realistic_asr": {
            "aggregate_metrics": quality_asr,
            "sample_details": asr_items_detail
        },
        "quality_delta": {
            "bleu_drop": round(quality_clean["bleu"] - quality_asr["bleu"], 2),
            "chrf_drop": round(quality_clean["chrf_plus_plus"] - quality_asr["chrf_plus_plus"], 2)
        }
    }
