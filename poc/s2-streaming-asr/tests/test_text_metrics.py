import pytest
from metrics.text_metrics import (
    levenshtein_distance,
    normalize_text_en,
    normalize_text_ja,
    compute_wer,
    compute_cer,
    evaluate_accuracy
)


def test_levenshtein_distance_exact_matches():
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("hello", "hello") == 0
    assert levenshtein_distance(["a", "b"], ["a", "b"]) == 0


def test_levenshtein_distance_empty_strings():
    assert levenshtein_distance("", "abc") == 3
    assert levenshtein_distance("abc", "") == 3
    assert levenshtein_distance([], ["a", "b"]) == 2


def test_levenshtein_distance_substitutions_insertions_deletions():
    assert levenshtein_distance("cat", "cats") == 1
    assert levenshtein_distance("cats", "cat") == 1
    assert levenshtein_distance("cat", "bat") == 1
    seq1 = ["the", "quick", "brown", "fox"]
    seq2 = ["the", "fast", "brown", "dog"]
    assert levenshtein_distance(seq1, seq2) == 2


def test_levenshtein_unicode_japanese():
    assert levenshtein_distance("持ち主", "こち主") == 1
    assert levenshtein_distance("秋葉原", "あきはばら") == 5


def test_text_normalization_en():
    raw = "Hello, WORLD!! This is... a test (123)."
    expected = "hello world this is a test 123"
    assert normalize_text_en(raw) == expected


def test_text_normalization_ja():
    raw = "昨日は、友達と一緒に！『秋葉原』に行きました。"
    expected = "昨日は友達と一緒に秋葉原に行きました"
    assert normalize_text_ja(raw) == expected


def test_compute_wer():
    ref = "the quick brown fox"
    hyp_perfect = "the quick brown fox"
    assert compute_wer(ref, hyp_perfect) == 0.0

    hyp_1_error = "the fast brown fox"
    assert compute_wer(ref, hyp_1_error) == 0.25

    assert compute_wer("", "") == 0.0
    assert compute_wer("hello", "") == 1.0


def test_compute_cer():
    ref = "こんにちは世界"
    hyp_perfect = "こんにちは世界"
    assert compute_cer(ref, hyp_perfect) == 0.0

    # こ(ん)に(ち)は vs こ(ん)ば(ん)わ -> 3 substitutions (に->ば, ち->ん, は->わ) out of 7 chars
    hyp_3_error = "こんばんわ世界"
    cer = compute_cer(ref, hyp_3_error)
    assert abs(cer - (3.0 / 7.0)) < 1e-4

    # 1 substitution: こんにちは世界 vs こんにちわ世界 (は->わ) -> 1 / 7
    hyp_1_error = "こんにちわ世界"
    cer_1 = compute_cer(ref, hyp_1_error)
    assert abs(cer_1 - (1.0 / 7.0)) < 1e-4


def test_evaluate_accuracy():
    res_en = evaluate_accuracy("Hello world", "hello world", language="en")
    assert res_en["primary_error_metric"] == "WER"
    assert res_en["wer"] == 0.0
    assert res_en["word_accuracy"] == 1.0

    res_ja = evaluate_accuracy("東京都", "京都", language="ja")
    assert res_ja["primary_error_metric"] == "CER"
    assert res_ja["cer"] == pytest.approx(1.0 / 3.0, 0.001)
