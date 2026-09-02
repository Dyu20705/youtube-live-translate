"""
test_agreement.py - Unit tests for tokenization and Local Agreement Tracker.
"""

import pytest
from policy.agreement import (
    tokenize_words,
    detokenize_words,
    longest_common_prefix_tokens,
    LocalAgreementTracker,
)


def test_tokenize_words_contractions_and_punctuation():
    text = "Hello, I'm going to Tokyo! What's up?"
    tokens = tokenize_words(text)
    assert tokens == ["Hello", ",", "I'm", "going", "to", "Tokyo", "!", "What's", "up", "?"]


def test_detokenize_words_spacing():
    tokens = ["Hello", ",", "I'm", "going", "to", "Tokyo", "!"]
    detok = detokenize_words(tokens)
    assert detok == "Hello, I'm going to Tokyo!"


def test_longest_common_prefix_tokens():
    t1 = ["I", "went", "to", "the", "park"]
    t2 = ["I", "went", "to", "Tokyo", "yesterday"]
    lcp = longest_common_prefix_tokens(t1, t2)
    assert lcp == ["I", "went", "to"]


def test_local_agreement_tracker_k2():
    tracker = LocalAgreementTracker(k=2)

    # 1st update: not enough history for K=2
    tracker.add_hypothesis(["I", "think"])
    assert tracker.get_agreement_prefix() == []

    # 2nd update with common prefix "I"
    tracker.add_hypothesis(["I", "went", "to", "Tokyo"])
    assert tracker.get_agreement_prefix() == ["I"]

    # 3rd update with common prefix "I went to"
    tracker.add_hypothesis(["I", "went", "to", "Tokyo", "station"])
    # Compares last 2 hypotheses: ["I", "went", "to", "Tokyo"] vs ["I", "went", "to", "Tokyo", "station"]
    assert tracker.get_agreement_prefix() == ["I", "went", "to", "Tokyo"]


def test_local_agreement_tracker_k3():
    tracker = LocalAgreementTracker(k=3)

    tracker.add_hypothesis(["I", "am"])
    assert tracker.get_agreement_prefix() == []

    tracker.add_hypothesis(["I", "am", "happy"])
    assert tracker.get_agreement_prefix() == []

    tracker.add_hypothesis(["I", "am", "very", "happy"])
    # Last 3: ["I", "am"], ["I", "am", "happy"], ["I", "am", "very", "happy"] -> common is ["I", "am"]
    assert tracker.get_agreement_prefix() == ["I", "am"]


def test_local_agreement_tracker_divergence_resets_agreement():
    tracker = LocalAgreementTracker(k=2)

    tracker.add_hypothesis(["She", "is", "a", "doctor"])
    tracker.add_hypothesis(["She", "is", "a", "teacher"])
    assert tracker.get_agreement_prefix() == ["She", "is", "a"]

    # Divergent rewrite
    tracker.add_hypothesis(["He", "is", "a", "teacher"])
    assert tracker.get_agreement_prefix() == []


def test_local_agreement_tracker_reset():
    tracker = LocalAgreementTracker(k=2)
    tracker.add_hypothesis(["A", "B"])
    tracker.add_hypothesis(["A", "B", "C"])
    assert tracker.get_agreement_prefix() == ["A", "B"]

    tracker.reset()
    assert tracker.get_agreement_prefix() == []
