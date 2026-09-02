import pytest
from metrics.stability_metrics import (
    longest_common_prefix_len,
    analyze_stream_stability
)


def test_longest_common_prefix_len():
    assert longest_common_prefix_len("", "") == 0
    assert longest_common_prefix_len("hello", "") == 0
    assert longest_common_prefix_len("hello", "hello world") == 5
    assert longest_common_prefix_len("yesterday I", "yesterday you") == 10
    assert longest_common_prefix_len("apple", "banana") == 0


def test_analyze_stream_stability_monotonic_growth():
    timeline = [
        {"timestamp_ms": 100, "text": "Yesterday", "is_final": False},
        {"timestamp_ms": 200, "text": "Yesterday I", "is_final": False},
        {"timestamp_ms": 300, "text": "Yesterday I went", "is_final": False},
        {"timestamp_ms": 400, "text": "Yesterday I went there", "is_final": True}
    ]
    res = analyze_stream_stability(timeline, "Yesterday I went there")
    assert res["total_hypotheses"] == 4
    assert res["revision_count"] == 0
    assert res["pure_append_count"] == 3
    assert res["revision_magnitude"] == 0
    assert res["average_stable_prefix_ratio"] == 1.0


def test_analyze_stream_stability_destructive_revisions():
    timeline = [
        {"timestamp_ms": 100, "text": "Yesterday I saw", "is_final": False},
        {"timestamp_ms": 200, "text": "Yesterday I went", "is_final": False},
        {"timestamp_ms": 300, "text": "Yesterday I looked", "is_final": False},
        {"timestamp_ms": 400, "text": "Yesterday I went there", "is_final": True}
    ]
    res = analyze_stream_stability(timeline, "Yesterday I went there")
    assert res["total_hypotheses"] == 4
    assert res["revision_count"] > 0
    assert res["revision_magnitude"] > 0
    assert res["average_stable_prefix_ratio"] < 1.0


def test_analyze_stream_stability_empty_timeline():
    res = analyze_stream_stability([], "")
    assert res["total_hypotheses"] == 0
    assert res["revision_count"] == 0
    assert res["average_stable_prefix_ratio"] == 1.0
