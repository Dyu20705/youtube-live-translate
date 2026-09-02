"""
stability_metrics.py - Translation Prefix Stability (TPS) and streaming revision metrics.
"""

from typing import List, Dict, Any, Tuple
import re


def tokenize_words(text: str) -> List[str]:
    """Tokenizes English text into words and punctuation tokens."""
    return re.findall(r"\w+|[^\w\s]", text, re.UNICODE)


def longest_common_prefix_tokens(tokens_a: List[str], tokens_b: List[str]) -> List[str]:
    """Returns the longest common prefix between two token lists."""
    min_len = min(len(tokens_a), len(tokens_b))
    prefix = []
    for i in range(min_len):
        if tokens_a[i] == tokens_b[i]:
            prefix.append(tokens_a[i])
        else:
            break
    return prefix


def analyze_translation_stability(hypotheses_stream: List[str]) -> Dict[str, Any]:
    """
    Analyzes streaming stability across a series of consecutive translation hypotheses:
    - Translation Prefix Stability (TPS) = stable_output_prefix_tokens / previous_output_tokens
    - Destructive revisions
    - Complete rewrites
    - Average revision size (tokens modified)
    - Output length progression
    """
    if not hypotheses_stream:
        return {
            "total_updates": 0,
            "average_tps": 1.0,
            "destructive_revisions": 0,
            "complete_rewrites": 0,
            "average_revision_size": 0.0,
            "step_details": []
        }

    tokenized_stream = [tokenize_words(h) for h in hypotheses_stream]
    step_details = []
    
    tps_values: List[float] = []
    destructive_revisions = 0
    complete_rewrites = 0
    revision_sizes: List[int] = []

    for i in range(1, len(tokenized_stream)):
        prev_tokens = tokenized_stream[i - 1]
        curr_tokens = tokenized_stream[i]

        if not prev_tokens:
            # First non-empty update
            step_details.append({
                "step": i,
                "prev_text": hypotheses_stream[i - 1],
                "curr_text": hypotheses_stream[i],
                "tps": 1.0,
                "is_destructive": False,
                "is_rewrite": False,
                "revision_size": 0,
                "common_prefix": " ".join(curr_tokens)
            })
            continue

        lcp = longest_common_prefix_tokens(prev_tokens, curr_tokens)
        stable_prefix_len = len(lcp)
        prev_len = len(prev_tokens)

        tps = stable_prefix_len / prev_len if prev_len > 0 else 1.0
        tps_values.append(tps)

        is_destructive = stable_prefix_len < prev_len
        is_rewrite = (stable_prefix_len == 0 and prev_len > 0)
        revision_size = prev_len - stable_prefix_len

        if is_destructive:
            destructive_revisions += 1
            revision_sizes.append(revision_size)

        if is_rewrite:
            complete_rewrites += 1

        step_details.append({
            "step": i,
            "prev_text": hypotheses_stream[i - 1],
            "curr_text": hypotheses_stream[i],
            "tps": round(tps, 4),
            "is_destructive": is_destructive,
            "is_rewrite": is_rewrite,
            "revision_size": revision_size,
            "common_prefix": " ".join(lcp)
        })

    avg_tps = round(sum(tps_values) / len(tps_values), 4) if tps_values else 1.0
    avg_rev_size = round(sum(revision_sizes) / len(revision_sizes), 2) if revision_sizes else 0.0

    return {
        "total_updates": len(hypotheses_stream),
        "average_tps": avg_tps,
        "destructive_revisions": destructive_revisions,
        "complete_rewrites": complete_rewrites,
        "average_revision_size": avg_rev_size,
        "step_details": step_details
    }
