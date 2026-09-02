"""
retranslation_cost.py - Quantifies the computational cost and redundancy of naive re-translation.
"""

from typing import List, Dict, Any

try:
    from ..engines.base import MTEngine
except (ImportError, ValueError):
    from engines.base import MTEngine


def evaluate_retranslation_cost(
    engine: MTEngine,
    corpus_items: List[Dict[str, Any]],
    simulated_chunks_per_utterance: int = 8,
    beam_size: int = 1
) -> Dict[str, Any]:
    """
    Simulates naive streaming re-translation where every ASR partial hypothesis triggers an MT call.
    Measures:
    - Total MT calls
    - Total MT CPU time
    - Redundant translation rate
    - Average characters translated per utterance vs final length
    """
    total_calls = 0
    total_mt_time_ms = 0.0
    total_chars_translated = 0
    total_final_chars = 0
    per_utterance_data = []

    for item in corpus_items:
        asr_text = item["asr_ja"]
        final_len = len(asr_text)
        if final_len == 0:
            continue

        total_final_chars += final_len

        # Generate incremental slices representing chunk updates
        slice_steps = min(simulated_chunks_per_utterance, final_len)
        step_indices = [int(round((i + 1) * final_len / slice_steps)) for i in range(slice_steps)]
        # Ensure unique positive indices
        step_indices = sorted(list(set([idx for idx in step_indices if idx > 0])))

        utterance_calls = len(step_indices)
        utterance_time_ms = 0.0
        utterance_chars = 0

        for idx in step_indices:
            partial_str = asr_text[:idx]
            res = engine.translate(partial_str, beam_size=beam_size)
            utterance_time_ms += res.total_time_ms
            utterance_chars += len(partial_str)

        total_calls += utterance_calls
        total_mt_time_ms += utterance_time_ms
        total_chars_translated += utterance_chars

        redundancy_ratio = (utterance_chars - final_len) / final_len if final_len > 0 else 0.0

        per_utterance_data.append({
            "id": item["id"],
            "asr_text": asr_text,
            "final_len": final_len,
            "mt_calls": utterance_calls,
            "total_time_ms": round(utterance_time_ms, 2),
            "chars_translated": utterance_chars,
            "redundancy_ratio": round(redundancy_ratio, 2),
            "avg_time_per_call_ms": round(utterance_time_ms / utterance_calls, 2)
        })

    avg_calls = round(total_calls / len(corpus_items), 1) if corpus_items else 0
    avg_cpu_time = round(total_mt_time_ms / len(corpus_items), 2) if corpus_items else 0.0
    avg_chars = round(total_chars_translated / len(corpus_items), 1) if corpus_items else 0
    overall_redundancy = round((total_chars_translated - total_final_chars) / total_final_chars, 2) if total_final_chars > 0 else 0.0

    return {
        "engine_name": engine.get_model_info().engine_name,
        "total_utterances": len(corpus_items),
        "total_mt_calls": total_calls,
        "avg_calls_per_utterance": avg_calls,
        "avg_total_cpu_time_per_utterance_ms": avg_cpu_time,
        "avg_chars_translated_per_utterance": avg_chars,
        "overall_redundant_translation_ratio": overall_redundancy,
        "feasibility_assessment": {
            "naive_streaming_feasible": (avg_cpu_time / (avg_calls * 128.0) <= 0.6) if avg_calls > 0 else True,
            "architectural_recommendation": (
                "Naive re-translation is computationally viable" if avg_cpu_time < 200 else
                "Event-driven / Wait-k throttling required to prevent CPU saturation"
            )
        },
        "utterance_data": per_utterance_data
    }
