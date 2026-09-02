"""
Unit tests for S3 quality and stability metrics.
"""

from metrics.quality_metrics import evaluate_translation_quality, compute_sentence_metrics
from metrics.stability_metrics import (
    tokenize_words,
    longest_common_prefix_tokens,
    analyze_translation_stability
)
from metrics.latency_tracker import compute_distribution_stats


def test_tokenize_words():
    tokens = tokenize_words("Hello, world! I am going to Tokyo.")
    assert "Hello" in tokens
    assert "," in tokens
    assert "world" in tokens
    assert "Tokyo" in tokens


def test_longest_common_prefix():
    a = ["I", "am", "going", "to", "school"]
    b = ["I", "am", "going", "to", "Tokyo"]
    lcp = longest_common_prefix_tokens(a, b)
    assert lcp == ["I", "am", "going", "to"]


def test_translation_stability_analysis():
    stream = ["I am", "I am going", "I am going to Tokyo"]
    res = analyze_translation_stability(stream)
    assert res["average_tps"] == 1.0
    assert res["destructive_revisions"] == 0
    assert res["complete_rewrites"] == 0


def test_destructive_revision_detection():
    stream = ["He is walking", "She runs fast"]
    res = analyze_translation_stability(stream)
    assert res["average_tps"] == 0.0
    assert res["destructive_revisions"] == 1
    assert res["complete_rewrites"] == 1


def test_quality_metrics_perfect_match():
    srcs = ["今日はとても天気が良くて暖かいですね。"]
    hyps = ["Today the weather is very nice and warm."]
    refs = ["Today the weather is very nice and warm."]
    res = evaluate_translation_quality(srcs, hyps, refs)
    assert res["bleu"] == 100.0
    assert res["chrf"] == 100.0
    if res["comet"] is not None:
        assert res["comet"] > 0.80


def test_distribution_stats():
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    stats = compute_distribution_stats(data)
    assert stats["min"] == 10.0
    assert stats["max"] == 50.0
    assert stats["p50"] == 30.0
