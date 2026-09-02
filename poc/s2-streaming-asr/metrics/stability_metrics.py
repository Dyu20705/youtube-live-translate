from typing import List, Dict, Any
from .text_metrics import levenshtein_distance


def longest_common_prefix_len(str1: str, str2: str) -> int:
    min_len = min(len(str1), len(str2))
    for i in range(min_len):
        if str1[i] != str2[i]:
            return i
    return min_len


def analyze_stream_stability(hypotheses_timeline: List[Dict[str, Any]], final_text: str) -> Dict[str, Any]:
    if not hypotheses_timeline:
        return {
            "total_hypotheses": 0,
            "revision_count": 0,
            "pure_append_count": 0,
            "revision_magnitude": 0,
            "average_stable_prefix_ratio": 1.0,
            "final_divergence": 0,
            "revisions_per_second": 0.0
        }

    total_hyps = len(hypotheses_timeline)
    revision_count = 0
    pure_append_count = 0
    total_revision_magnitude = 0
    stable_prefix_ratios = []

    prev_text = ""
    final_text_stripped = final_text.strip()

    for item in hypotheses_timeline:
        curr_text = item["text"].strip()
        if not curr_text or curr_text == prev_text:
            continue

        if prev_text:
            if curr_text.startswith(prev_text):
                pure_append_count += 1
            else:
                revision_count += 1
                total_revision_magnitude += levenshtein_distance(prev_text, curr_text)

        if final_text_stripped:
            lcp = longest_common_prefix_len(curr_text, final_text_stripped)
            stable_prefix_ratios.append(lcp / len(curr_text))

        prev_text = curr_text

    avg_spr = sum(stable_prefix_ratios) / len(stable_prefix_ratios) if stable_prefix_ratios else 1.0

    start_ms = hypotheses_timeline[0]["timestamp_ms"]
    end_ms = hypotheses_timeline[-1]["timestamp_ms"]
    duration_sec = max(0.1, (end_ms - start_ms) / 1000.0)
    rev_per_sec = revision_count / duration_sec

    return {
        "total_hypotheses": total_hyps,
        "revision_count": revision_count,
        "pure_append_count": pure_append_count,
        "revision_magnitude": total_revision_magnitude,
        "average_stable_prefix_ratio": round(avg_spr, 4),
        "revisions_per_second": round(rev_per_sec, 2),
        "final_divergence": levenshtein_distance(prev_text, final_text_stripped) if prev_text else 0
    }
