"""
partial_stability.py - Benchmarks partial prefix robustness, unpunctuated translation, and Translation Prefix Stability (TPS).
"""

from typing import List, Dict, Any

try:
    from ..engines.base import MTEngine
    from ..metrics.stability_metrics import analyze_translation_stability
    from ..metrics.quality_metrics import compute_sentence_metrics
except (ImportError, ValueError):
    from engines.base import MTEngine
    from metrics.stability_metrics import analyze_translation_stability
    from metrics.quality_metrics import compute_sentence_metrics


def run_partial_stability_benchmark(
    engine: MTEngine,
    corpus_items: List[Dict[str, Any]],
    partial_variants: List[Dict[str, Any]],
    beam_size: int = 1
) -> Dict[str, Any]:
    """
    Evaluates:
    1. Condition-level metrics (FULL, UNPUNCTUATED, PARTIAL_25, PARTIAL_50, PARTIAL_75, PARTIAL_100)
    2. Utterance-level progressive streaming sequence stability (TPS, destructive revisions, rewrites)
    """
    # 1. Condition evaluation
    condition_results: Dict[str, Dict[str, Any]] = {
        "FULL": {"latencies": [], "outputs": []},
        "UNPUNCTUATED": {"latencies": [], "outputs": []},
        "PARTIAL_25": {"latencies": [], "outputs": []},
        "PARTIAL_50": {"latencies": [], "outputs": []},
        "PARTIAL_75": {"latencies": [], "outputs": []},
        "PARTIAL_100": {"latencies": [], "outputs": []}
    }

    for variant in partial_variants:
        cond = variant["condition"]
        src = variant["source_text"]
        ref = variant["reference_en"]
        res = engine.translate(src, beam_size=beam_size)
        
        sent_m = compute_sentence_metrics(src, res.target_text, ref)
        if cond in condition_results:
            condition_results[cond]["latencies"].append(res.total_time_ms)
            condition_results[cond]["outputs"].append({
                "parent_id": variant["parent_id"],
                "source": src,
                "hypothesis": res.target_text,
                "latency_ms": res.total_time_ms,
                "metrics": sent_m
            })

    condition_summary = {}
    for cond, data in condition_results.items():
        lats = data["latencies"]
        avg_lat = round(sum(lats) / len(lats), 2) if lats else 0.0
        p50_lat = round(float(sorted(lats)[len(lats) // 2]), 2) if lats else 0.0
        avg_chrf = round(sum(o["metrics"]["sentence_chrf_pp"] for o in data["outputs"]) / len(data["outputs"]), 2) if data["outputs"] else 0.0
        
        condition_summary[cond] = {
            "count": len(lats),
            "avg_latency_ms": avg_lat,
            "p50_latency_ms": p50_lat,
            "avg_chrf_pp": avg_chrf
        }

    # 2. Sequential Streaming Prefix Progression (25% -> 50% -> 75% -> 100%)
    utterance_stability_results = []
    all_tps_scores = []
    total_destructive_revisions = 0
    total_complete_rewrites = 0
    all_revision_sizes = []

    for item in corpus_items:
        item_id = item["id"]
        # Find 25, 50, 75, 100 variants for this item
        item_variants = [v for v in partial_variants if v["parent_id"] == item_id and v["condition"].startswith("PARTIAL_")]
        # Sort by prefix ratio
        item_variants.sort(key=lambda x: x.get("prefix_ratio", 0))

        stream_hypotheses = []
        for v in item_variants:
            res = engine.translate(v["source_text"], beam_size=beam_size)
            stream_hypotheses.append(res.target_text)

        stability = analyze_translation_stability(stream_hypotheses)
        all_tps_scores.append(stability["average_tps"])
        total_destructive_revisions += stability["destructive_revisions"]
        total_complete_rewrites += stability["complete_rewrites"]
        if stability["average_revision_size"] > 0:
            all_revision_sizes.append(stability["average_revision_size"])

        utterance_stability_results.append({
            "id": item_id,
            "category": item["category"],
            "asr_full": item["asr_ja"],
            "stream_hypotheses": stream_hypotheses,
            "stability": stability
        })

    overall_avg_tps = round(sum(all_tps_scores) / len(all_tps_scores), 4) if all_tps_scores else 1.0
    overall_avg_rev_size = round(sum(all_revision_sizes) / len(all_revision_sizes), 2) if all_revision_sizes else 0.0

    return {
        "condition_summary": condition_summary,
        "overall_stability": {
            "average_tps": overall_avg_tps,
            "total_destructive_revisions": total_destructive_revisions,
            "total_complete_rewrites": total_complete_rewrites,
            "average_revision_size": overall_avg_rev_size,
            "total_utterances_evaluated": len(corpus_items)
        },
        "utterance_details": utterance_stability_results
    }
