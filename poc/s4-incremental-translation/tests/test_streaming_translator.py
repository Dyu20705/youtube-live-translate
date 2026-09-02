"""
test_streaming_translator.py - Unit test matrix for IncrementalTranslator state machine.
Covers items A through I:
A. Stable extension
B. Translation rewrite
C. Repeated agreement
D. Unstable sequence
E. Source-side rewrite / conflict handling
F. Endpoint / finalization
G. Empty input
H. Duplicate ASR revision deduplication
I. Multiple segment isolation
"""

import pytest
from policy.state_model import SegmentStatus, PolicyConfig
from policy.streaming_translator import IncrementalTranslator

try:
    from conftest import MockMTEngine
except ImportError:
    from .conftest import MockMTEngine




def test_matrix_a_stable_extension():
    """
    A. Stable extension:
    Source grows progressively, target hypotheses grow consistently, frontier advances.
    """
    mapping = {
        "東京に": "To Tokyo",
        "東京に行き": "I go to Tokyo",
        "東京に行きたい": "I want to go to Tokyo",
        "東京に行きたいです": "I want to go to Tokyo."
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=1)
    translator = IncrementalTranslator(engine, config)

    # Step 1: "東京に" -> "To Tokyo" (K=2, 1st update -> nothing committed yet)
    s1 = translator.update_partial("東京に")
    assert s1.committed_text == ""
    assert s1.provisional_text == "To Tokyo"
    assert s1.display_text == "To Tokyo"

    # Step 2: "東京に行き" -> "I go to Tokyo"
    s2 = translator.update_partial("東京に行き")
    # LCP between "To Tokyo" and "I go to Tokyo" is empty -> still nothing committed
    assert s2.committed_text == ""
    assert s2.provisional_text == "I go to Tokyo"

    # Step 3: "東京に行きたい" -> "I want to go to Tokyo"
    s3 = translator.update_partial("東京に行きたい")
    # LCP between "I go to Tokyo" and "I want to go to Tokyo" is "I"
    # With buffer 1, can commit "I"
    assert "I" in s3.display_text

    # Step 4: "東京に行きたいです" -> "I want to go to Tokyo."
    s4 = translator.update_partial("東京に行きたいです")
    assert len(s4.committed_text) >= len(s3.committed_text)
    assert s4.committed_text.startswith(s3.committed_text)


def test_matrix_b_translation_rewrite():
    """
    B. Translation rewrite:
    Candidate translation changes -> provisional suffix updates -> committed prefix remains unchanged.
    """
    mapping = {
        "今日": "Today I",
        "今日は": "Today I will",
        "今日は雨": "Today it will rain"
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2)
    translator = IncrementalTranslator(engine, config)

    s1 = translator.update_partial("今日")
    s2 = translator.update_partial("今日は")
    # LCP of "Today I" and "Today I will" is "Today I". With buffer 2 (len 3 - 2 = 1), commits "Today"
    assert s2.committed_text == "Today"
    assert s2.provisional_text == "I will"

    # Now hypothesis changes to "Today it will rain"
    s3 = translator.update_partial("今日は雨")
    # Committed prefix MUST remain "Today"
    assert s3.committed_text == "Today"
    assert s3.provisional_text == "it will rain"
    assert s3.display_text == "Today it will rain"
    assert translator.session_metrics.committed_prefix_revision_count == 0


def test_matrix_c_repeated_agreement():
    """
    C. Repeated agreement:
    Same candidate prefix observed across K consecutive updates -> frontier advances.
    """
    mapping = {
        "U1": "The weather is very nice today",
        "U2": "The weather is very nice today and warm",
        "U3": "The weather is very nice today and warm outside"
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2, accelerate_on_punctuation=False)
    translator = IncrementalTranslator(engine, config)

    # U1
    s1 = translator.update_partial("U1")
    assert s1.committed_text == ""

    # U2 (2nd consecutive update agreeing on "The weather is very nice today")
    s2 = translator.update_partial("U2")
    # Candidate len = 8 ("The weather is very nice today and warm"), buffer = 2 -> commits up to 6 tokens ("The weather is very nice today")
    assert s2.committed_text == "The weather is very nice today"
    assert s2.provisional_text == "and warm"

    # U3 (3rd update)
    s3 = translator.update_partial("U3")
    # Candidate len = 9, buffer = 2 -> safe commit = 7 tokens ("The weather is very nice today and")
    assert s3.committed_text == "The weather is very nice today and"
    assert s3.provisional_text == "warm outside"
    assert s3.display_text == "The weather is very nice today and warm outside"
    assert s3.committed_text.startswith(s2.committed_text)



def test_matrix_d_unstable_sequence():
    """
    D. Unstable sequence:
    Fluctuating hypotheses (A -> AB -> AX -> ABX) must NOT prematurely commit unstable content.
    """
    mapping = {
        "U1": "She likes apples",
        "U2": "He likes apples",
        "U3": "She likes apples again",
        "U4": "They like apples"
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=1)
    translator = IncrementalTranslator(engine, config)

    s1 = translator.update_partial("U1")  # She likes apples
    s2 = translator.update_partial("U2")  # He likes apples (LCP empty)
    assert s2.committed_text == ""

    s3 = translator.update_partial("U3")  # She likes apples again (LCP with U2 is empty)
    assert s3.committed_text == ""

    s4 = translator.update_partial("U4")  # They like apples (LCP empty)
    assert s4.committed_text == ""


def test_matrix_e_source_side_rewrite():
    """
    E. Source-side rewrite:
    ASR hypothesis rewrites earlier tokens -> committed prefix MUST NOT mutate, conflict is tracked.
    """
    mapping = {
        "S1": "I am traveling to Japan",
        "S2": "I am traveling to Japan tomorrow",
        "S3_REWRITE": "We are going to Kyoto"  # Drastic ASR correction
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=1)
    translator = IncrementalTranslator(engine, config)

    translator.update_partial("S1")
    s2 = translator.update_partial("S2")
    # Committed: "I am traveling to Japan"
    committed_before = s2.committed_text
    assert "I am traveling to Japan" in committed_before

    # Now ASR rewrites completely
    s3 = translator.update_partial("S3_REWRITE")
    
    # Invariant: committed_text is immutable
    assert s3.committed_text == committed_before
    assert translator.session_metrics.commit_conflict_count > 0
    assert translator.session_metrics.committed_prefix_revision_count == 0


def test_matrix_f_endpoint_finalization():
    """
    F. Endpoint / finalization:
    Final ASR -> final MT -> remaining provisional output committed -> state transitions to FLUSHED.
    """
    mapping = {
        "S1": "Hello",
        "S2": "Hello world",
        "S_FINAL": "Hello world, nice to meet you."
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2)
    translator = IncrementalTranslator(engine, config)

    translator.update_partial("S1")
    translator.update_partial("S2")
    
    # Finalize segment
    final_state = translator.finalize_segment("S_FINAL")
    assert final_state.is_final is True
    assert final_state.provisional_text == ""
    assert final_state.committed_text == "Hello world, nice to meet you."
    assert final_state.display_text == "Hello world, nice to meet you."
    assert translator.segment_status == SegmentStatus.FLUSHED


def test_matrix_g_empty_input():
    """
    G. Empty input:
    No crash, no bogus commit, returns empty state safely.
    """
    engine = MockMTEngine()
    translator = IncrementalTranslator(engine)

    s1 = translator.update_partial("")
    assert s1.committed_text == ""
    assert s1.provisional_text == ""
    assert s1.display_text == ""
    assert s1.mt_calls_count == 0

    s2 = translator.update_partial("   ")
    assert s2.display_text == ""
    assert s2.mt_calls_count == 0


def test_matrix_h_duplicate_asr_revision_deduplication():
    """
    H. Duplicate ASR revision:
    Identical ASR update triggers no redundant MT call.
    """
    mapping = {"東京": "Tokyo"}
    engine = MockMTEngine(mapping)
    translator = IncrementalTranslator(engine)

    s1 = translator.update_partial("東京")
    assert engine.call_count == 1
    assert s1.mt_calls_count == 1

    # Identical ASR text
    s2 = translator.update_partial("東京")
    assert engine.call_count == 1  # No new MT call!
    assert s2.mt_calls_count == 1
    assert s2.display_text == s1.display_text
    assert translator.session_metrics.mt_call_reduction_ratio == 0.5  # 1 MT call for 2 updates = 50% reduction


def test_matrix_i_multiple_segments_isolation():
    """
    I. Multiple segments:
    State from segment N does not leak into segment N+1.
    """
    mapping = {
        "Seg1_partial": "This is segment one",
        "Seg1_final": "This is segment one.",
        "Seg2_partial": "Here begins segment two",
        "Seg2_final": "Here begins segment two."
    }
    engine = MockMTEngine(mapping)
    translator = IncrementalTranslator(engine)

    # Segment 1
    translator.update_partial("Seg1_partial")
    f1 = translator.finalize_segment("Seg1_final")
    assert f1.segment_id == 1
    assert f1.is_final is True
    assert f1.committed_text == "This is segment one."

    # Segment 2 starts
    s2_1 = translator.update_partial("Seg2_partial")
    assert s2_1.segment_id == 2
    assert s2_1.committed_text == ""  # Zero leakage from segment 1!
    assert s2_1.provisional_text == "Here begins segment two"

    f2 = translator.finalize_segment("Seg2_final")
    assert f2.segment_id == 2
    assert f2.is_final is True
    assert f2.committed_text == "Here begins segment two."
