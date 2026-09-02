"""
test_frontier.py - Unit tests for Adaptive Frontier decision logic and conflict detection.
"""

import pytest
from policy.state_model import PolicyConfig
from policy.frontier import AdaptiveFrontierController


def test_frontier_unstable_buffer_protection():
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2, accelerate_on_punctuation=False)
    controller = AdaptiveFrontierController(config)

    committed = []
    candidate = ["I", "went", "to", "the", "store"]
    agreement = ["I", "went", "to", "the", "store"]

    # Candidate len = 5, buffer = 2 -> safe boundary = 5 - 2 = 3 ("I went to")
    new_idx, is_conflict, did_advance = controller.decide_frontier(
        committed_tokens=committed,
        candidate_tokens=candidate,
        agreement_tokens=agreement,
        source_text="店に行っ",
        is_final=False
    )

    assert not is_conflict
    assert did_advance
    assert new_idx == 3  # commits ["I", "went", "to"]


def test_frontier_punctuation_acceleration():
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2, accelerate_on_punctuation=True)
    controller = AdaptiveFrontierController(config)

    committed = ["I", "went"]
    candidate = ["I", "went", "to", "Tokyo", ",", "and", "bought", "books"]
    agreement = ["I", "went", "to", "Tokyo", ",", "and", "bought"]

    # Even with buffer 2 (which would commit up to index 7-2=5), punctuation "," is at index 4 (1-indexed slice 5)
    new_idx, is_conflict, did_advance = controller.decide_frontier(
        committed_tokens=committed,
        candidate_tokens=candidate,
        agreement_tokens=agreement,
        source_text="東京に行って本を買った",
        is_final=False
    )

    assert not is_conflict
    assert did_advance
    assert new_idx >= 5  # includes "I went to Tokyo,"


def test_frontier_japanese_sentence_final_acceleration():
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2, accelerate_on_punctuation=True)
    controller = AdaptiveFrontierController(config)

    committed = ["I", "understand"]
    candidate = ["I", "understand", "completely", "."]
    agreement = ["I", "understand", "completely", "."]

    # Source ends with "ました。" -> accelerate up to agreement length
    new_idx, is_conflict, did_advance = controller.decide_frontier(
        committed_tokens=committed,
        candidate_tokens=candidate,
        agreement_tokens=agreement,
        source_text="分かりました。",
        is_final=False
    )

    assert not is_conflict
    assert did_advance
    assert new_idx == 4  # commits all 4 tokens


def test_frontier_conflict_detection_preserves_committed():
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2)
    controller = AdaptiveFrontierController(config)

    committed = ["She", "went"]
    # Upstream ASR rewrote source, candidate is now "He went to Tokyo"
    candidate = ["He", "went", "to", "Tokyo"]
    agreement = ["He", "went"]

    new_idx, is_conflict, did_advance = controller.decide_frontier(
        committed_tokens=committed,
        candidate_tokens=candidate,
        agreement_tokens=agreement,
        source_text="彼が行った",
        is_final=False
    )

    assert is_conflict
    assert not did_advance
    assert new_idx == 2  # keeps original committed len 2 without truncating


def test_frontier_finalization_flushes_all():
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2)
    controller = AdaptiveFrontierController(config)

    committed = ["I", "went"]
    candidate = ["I", "went", "to", "Tokyo", "."]
    agreement = ["I", "went", "to"]

    new_idx, is_conflict, did_advance = controller.decide_frontier(
        committed_tokens=committed,
        candidate_tokens=candidate,
        agreement_tokens=agreement,
        source_text="東京に行った。",
        is_final=True
    )

    assert not is_conflict
    assert did_advance
    assert new_idx == len(candidate)  # commits all remaining tokens
