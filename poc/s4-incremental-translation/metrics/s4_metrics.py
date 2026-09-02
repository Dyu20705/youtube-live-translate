"""
s4_metrics.py - Telemetry, stability metrics, and latency analysis for Stage S4.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import re

try:
    from ..policy.state_model import SubtitleState
    from ..policy.agreement import tokenize_words, longest_common_prefix_tokens
except (ImportError, ValueError):
    from policy.state_model import SubtitleState
    from policy.agreement import tokenize_words, longest_common_prefix_tokens


def analyze_s4_session_stability(states_stream: List[SubtitleState]) -> Dict[str, Any]:
    """
    Analyzes an incremental streaming session of SubtitleState emissions.
    Explicitly separates three distinct stability concepts:
    A. Committed Prefix Stability (Hard invariant: revisions == 0)
    B. Provisional Suffix Revisions (Expected and allowed revisable tail)
    C. Whole-Display Destructive Revisions & Complete Rewrites (S3-comparable visual stability)
    """
    if not states_stream:
        return {
            "total_states": 0,
            "committed_prefix_revisions": 0,
            "provisional_revisions": 0,
            "provisional_revision_rate": 0.0,
            "frontier_advancements": 0,
            "display_tps": 1.0,
            "display_revision_count": 0,
            "display_complete_rewrite_count": 0,
            "commit_delay_steps": 0,
            "policy_overhead_p50_ms": 0.0,
            "policy_overhead_p95_ms": 0.0,
        }

    committed_prefix_revisions = 0
    provisional_revisions = 0
    provisional_opportunities = 0
    frontier_advancements = 0
    
    first_commit_step: Optional[int] = None
    first_input_step: Optional[int] = None
    
    display_texts: List[str] = []
    policy_overheads: List[float] = []

    for i, state in enumerate(states_stream):
        display_texts.append(state.display_text)
        
        ov = state.metrics.get("policy_overhead_ms")
        if ov is not None:
            policy_overheads.append(ov)

        if state.source_text and first_input_step is None:
            first_input_step = i

        if state.committed_text and first_commit_step is None:
            first_commit_step = i

        if i > 0:
            prev_state = states_stream[i - 1]
            
            # Check within the same segment
            if state.segment_id == prev_state.segment_id and not prev_state.is_final:
                # 1. Committed prefix immutability check
                prev_committed = prev_state.committed_text
                curr_committed = state.committed_text
                
                # curr_committed MUST start with prev_committed and be >= in length
                if not curr_committed.startswith(prev_committed) or len(curr_committed) < len(prev_committed):
                    committed_prefix_revisions += 1

                if state.frontier_position > prev_state.frontier_position:
                    frontier_advancements += 1

                # 2. Provisional suffix revision check
                if prev_state.provisional_text or state.provisional_text:
                    provisional_opportunities += 1
                    if state.provisional_text != prev_state.provisional_text:
                        provisional_revisions += 1

    # Commit delay calculation
    if first_input_step is not None and first_commit_step is not None:
        commit_delay_steps = max(0, first_commit_step - first_input_step)
    else:
        commit_delay_steps = 0

    provisional_revision_rate = (
        round(provisional_revisions / provisional_opportunities, 4)
        if provisional_opportunities > 0
        else 0.0
    )

    # 3. User-visible display text TPS analysis (Concept C)
    tokenized_stream = [tokenize_words(t) for t in display_texts if t.strip()]
    tps_values = []
    display_destructive_revisions = 0
    display_complete_rewrites = 0

    for j in range(1, len(tokenized_stream)):
        prev_toks = tokenized_stream[j - 1]
        curr_toks = tokenized_stream[j]
        if not prev_toks:
            continue
        
        lcp = longest_common_prefix_tokens(prev_toks, curr_toks)
        tps = len(lcp) / len(prev_toks)
        tps_values.append(tps)
        
        if len(lcp) < len(prev_toks):
            display_destructive_revisions += 1
        if len(lcp) == 0 and len(prev_toks) > 0:
            display_complete_rewrites += 1

    avg_display_tps = round(float(np.mean(tps_values)), 4) if tps_values else 1.0

    p50_overhead = 0.0
    p95_overhead = 0.0
    if policy_overheads:
        p50_overhead = round(float(np.percentile(policy_overheads, 50)), 3)
        p95_overhead = round(float(np.percentile(policy_overheads, 95)), 3)

    return {
        "total_states": len(states_stream),
        "committed_prefix_revisions": committed_prefix_revisions,
        "provisional_revisions": provisional_revisions,
        "provisional_revision_rate": provisional_revision_rate,
        "frontier_advancements": frontier_advancements,
        "display_tps": avg_display_tps,
        "average_tps": avg_display_tps,  # Backward compatibility alias
        "display_revision_count": display_destructive_revisions,
        "destructive_revisions": display_destructive_revisions,  # Backward compatibility alias
        "display_complete_rewrite_count": display_complete_rewrites,
        "complete_rewrites": display_complete_rewrites,  # Backward compatibility alias
        "commit_delay_steps": commit_delay_steps,
        "policy_overhead_p50_ms": p50_overhead,
        "policy_overhead_p95_ms": p95_overhead,
    }

