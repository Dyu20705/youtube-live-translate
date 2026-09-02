"""
test_state_model.py - Unit tests for S4 data models, contracts, and lifecycle status.
"""

import pytest
from policy.state_model import SegmentStatus, PolicyConfig, SubtitleState, SessionMetrics


def test_policy_config_defaults():
    config = PolicyConfig()
    assert config.agreement_k == 2
    assert config.unstable_buffer_tokens == 2
    assert config.max_wait_updates == 10
    assert config.accelerate_on_punctuation is True
    assert config.enable_mt_deduplication is True


def test_subtitle_state_serialization():
    state = SubtitleState(
        segment_id=1,
        committed_text="I went to",
        provisional_text="Tokyo yesterday",
        display_text="I went to Tokyo yesterday",
        is_final=False,
        source_text="東京に行った",
        source_revision=2,
        frontier_position=3,
        mt_calls_count=2,
        metrics={"policy_overhead_ms": 0.45}
    )

    d = state.to_dict()
    assert d["segment_id"] == 1
    assert d["committed_text"] == "I went to"
    assert d["provisional_text"] == "Tokyo yesterday"
    assert d["display_text"] == "I went to Tokyo yesterday"
    assert d["is_final"] is False
    assert d["frontier_position"] == 3
    assert d["mt_calls_count"] == 2
    assert d["metrics"]["policy_overhead_ms"] == 0.45


def test_session_metrics_overhead_percentiles():
    metrics = SessionMetrics(
        source_updates=10,
        translation_updates=6,
        mt_calls=6,
        policy_overhead_times_ms=[0.5, 0.8, 1.2, 2.0, 0.6, 0.7, 1.0, 1.5, 3.0, 0.4]
    )

    d = metrics.to_dict()
    assert d["source_updates"] == 10
    assert d["mt_calls"] == 6
    assert d["mt_call_reduction_ratio"] == 0.4  # 1 - (6/10) = 0.4
    assert d["policy_overhead_p50_ms"] > 0.0
    assert d["policy_overhead_p95_ms"] >= d["policy_overhead_p50_ms"]
