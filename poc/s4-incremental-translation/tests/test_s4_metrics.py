"""
test_s4_metrics.py - Unit tests for S4 session stability and latency metrics.
"""

import pytest
from policy.state_model import SubtitleState
from metrics.s4_metrics import analyze_s4_session_stability


def test_analyze_s4_session_stability_perfect_immutability():
    states = [
        SubtitleState(
            segment_id=1,
            committed_text="",
            provisional_text="I",
            display_text="I",
            is_final=False,
            source_text="私",
            source_revision=1,
            frontier_position=0,
            mt_calls_count=1,
            metrics={"policy_overhead_ms": 0.2}
        ),
        SubtitleState(
            segment_id=1,
            committed_text="I",
            provisional_text="went to Tokyo",
            display_text="I went to Tokyo",
            is_final=False,
            source_text="私は東京に行った",
            source_revision=2,
            frontier_position=1,
            mt_calls_count=2,
            metrics={"policy_overhead_ms": 0.3}
        ),
        SubtitleState(
            segment_id=1,
            committed_text="I went to Tokyo.",
            provisional_text="",
            display_text="I went to Tokyo.",
            is_final=True,
            source_text="私は東京に行きました。",
            source_revision=3,
            frontier_position=4,
            mt_calls_count=3,
            metrics={"policy_overhead_ms": 0.4}
        )
    ]

    analysis = analyze_s4_session_stability(states)
    assert analysis["total_states"] == 3
    assert analysis["committed_prefix_revisions"] == 0
    assert analysis["frontier_advancements"] == 2
    assert analysis["average_tps"] == 1.0  # Perfect prefix extension
    assert analysis["destructive_revisions"] == 0
    assert analysis["policy_overhead_p50_ms"] > 0.0
