"""
test_adversarial_fixtures.py - Adversarial streaming fixtures testing edge cases:
1. Japanese clause-final disambiguation
2. Late particle changes
3. Late punctuation
4. ASR correction of an earlier source token
5. Source insertion
6. Source deletion
7. Source middle rewrite
8. Repeated identical ASR hypothesis
9. Endpoint immediately after unstable revision
10. Multiple sequential segments
"""

import pytest
from policy.state_model import SegmentStatus, PolicyConfig
from policy.streaming_translator import IncrementalTranslator
try:
    from conftest import MockMTEngine
except ImportError:
    from .conftest import MockMTEngine



def test_adversarial_1_clause_final_disambiguation():
    """
    1. Japanese clause-final disambiguation:
    Meaning inverts at the very end of the sentence.
    """
    mapping = {
        "東京に行く": "I go to Tokyo",
        "東京に行くつもり": "I intend to go to Tokyo",
        "東京に行くつもりだった": "I had intended to go to Tokyo",
        "東京に行くつもりだったがやめた": "I had intended to go to Tokyo, but decided not to."
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2)
    translator = IncrementalTranslator(engine, config)

    s1 = translator.update_partial("東京に行く")
    s2 = translator.update_partial("東京に行くつもり")
    s3 = translator.update_partial("東京に行くつもりだった")
    s4 = translator.finalize_segment("東京に行くつもりだったがやめた")

    # Committed prefix must never mutate
    assert translator.session_metrics.committed_prefix_revision_count == 0
    assert s4.is_final is True
    assert s4.display_text == "I had intended to go to Tokyo, but decided not to."


def test_adversarial_2_late_particle_changes():
    """
    2. Late particle changes:
    Conditional particle 'たら' changes statement into conditional clause.
    """
    mapping = {
        "本を読む": "I read books",
        "本を読んだ": "I read the book",
        "本を読んだら": "If you read the book,",
        "本を読んだら分かります": "If you read the book, you will understand."
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2)
    translator = IncrementalTranslator(engine, config)

    translator.update_partial("本を読む")
    translator.update_partial("本を読んだ")
    s3 = translator.update_partial("本を読んだら")
    s4 = translator.finalize_segment("本を読んだら分かります")

    assert translator.session_metrics.committed_prefix_revision_count == 0
    assert s4.is_final is True


def test_adversarial_3_late_punctuation():
    """
    3. Late punctuation:
    Unpunctuated stream followed by sudden question mark.
    """
    mapping = {
        "これ": "This",
        "これは本当": "This is real",
        "これは本当ですか": "Is this real",
        "これは本当ですか？": "Is this real?"
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=1)
    translator = IncrementalTranslator(engine, config)

    translator.update_partial("これ")
    s2 = translator.update_partial("これは本当")
    # "This" was committed
    assert s2.committed_text == "This"

    s3 = translator.update_partial("これは本当ですか")
    # Question particle "ですか" changes candidate to "Is this real" -> conflict occurs!
    assert s3.committed_text == "This"
    assert translator.session_metrics.commit_conflict_count > 0

    s4 = translator.finalize_segment("これは本当ですか？")
    assert translator.session_metrics.committed_prefix_revision_count == 0
    assert s4.committed_text.startswith("This")
    assert s4.is_final is True



def test_adversarial_4_asr_earlier_token_correction():
    """
    4. ASR correction of an earlier source token:
    ASR changes '今日' (Today) -> '昨日' (Yesterday) after tokens were committed.
    Committed prefix must remain immutable, conflict must be tracked.
    """
    mapping = {
        "今日東京": "Today in Tokyo",
        "今日東京に行き": "Today in Tokyo I went",
        "昨日東京に行きました": "Yesterday in Tokyo I went"  # ASR corrected first word
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=1)
    translator = IncrementalTranslator(engine, config)

    translator.update_partial("今日東京")
    s2 = translator.update_partial("今日東京に行き")
    # Committed should have "Today in"
    committed_before = s2.committed_text
    assert len(committed_before) > 0

    # Upstream ASR rewrites 'Today' to 'Yesterday'
    s3 = translator.update_partial("昨日東京に行きました")

    # Invariant: committed text is NOT mutated
    assert s3.committed_text == committed_before
    assert translator.session_metrics.commit_conflict_count > 0
    assert translator.session_metrics.committed_prefix_revision_count == 0


def test_adversarial_5_source_insertion():
    """
    5. Source insertion:
    ASR inserts an adverb in the middle of the sentence.
    """
    mapping = {
        "私は行きます": "I will go",
        "私は東京に行きます": "I will go to Tokyo",
        "私は明日東京に行きます": "I will go to Tokyo tomorrow"
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=1)
    translator = IncrementalTranslator(engine, config)

    translator.update_partial("私は行きます")
    s2 = translator.update_partial("私は東京に行きます")
    s3 = translator.update_partial("私は明日東京に行きます")
    s4 = translator.finalize_segment("私は明日東京に行きます。")

    assert translator.session_metrics.committed_prefix_revision_count == 0
    assert s4.is_final is True


def test_adversarial_6_source_deletion():
    """
    6. Source deletion:
    ASR drops trailing words unexpectedly.
    """
    mapping = {
        "東京に行きますと": "When I go to Tokyo",
        "東京に行きます": "I go to Tokyo",
        "東京に": "To Tokyo"
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=1)
    translator = IncrementalTranslator(engine, config)

    translator.update_partial("東京に行きますと")
    translator.update_partial("東京に行きます")
    s3 = translator.update_partial("東京に")

    assert translator.session_metrics.committed_prefix_revision_count == 0


def test_adversarial_7_source_middle_rewrite():
    """
    7. Source middle rewrite:
    ASR replaces noun '雨' (rain) -> '雪' (snow).
    """
    mapping = {
        "外は雨が": "Outside rain is",
        "外は雨が降って": "Outside rain is falling",
        "外は雪が降っています": "Outside snow is falling"
    }
    engine = MockMTEngine(mapping)
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=1)
    translator = IncrementalTranslator(engine, config)

    translator.update_partial("外は雨が")
    s2 = translator.update_partial("外は雨が降って")
    s3 = translator.update_partial("外は雪が降っています")
    s4 = translator.finalize_segment("外は雪が降っています。")

    assert translator.session_metrics.committed_prefix_revision_count == 0
    assert s4.is_final is True


def test_adversarial_8_repeated_identical_asr():
    """
    8. Repeated identical ASR hypothesis:
    Duplicate updates must skip MT calls and maintain consistent state.
    """
    mapping = {"東京": "Tokyo"}
    engine = MockMTEngine(mapping)
    translator = IncrementalTranslator(engine)

    s1 = translator.update_partial("東京")
    assert engine.call_count == 1
    assert s1.mt_calls_count == 1

    # Repeat 5 times
    for _ in range(5):
        s_rep = translator.update_partial("東京")
        assert s_rep.display_text == s1.display_text

    assert engine.call_count == 1  # 0 new MT calls
    assert translator.session_metrics.mt_calls == 1
    assert translator.session_metrics.source_updates == 6
    assert translator.session_metrics.mt_call_reduction_ratio == round(5 / 6, 4)


def test_adversarial_9_endpoint_immediately_after_unstable_revision():
    """
    9. Endpoint immediately after unstable revision:
    Flushes all candidate tokens into committed state immediately.
    """
    mapping = {
        "A": "Alpha",
        "B_UNSTABLE": "Beta fluctuating wildly",
        "B_FINAL": "Beta stabilized."
    }
    engine = MockMTEngine(mapping)
    translator = IncrementalTranslator(engine)

    translator.update_partial("A")
    translator.update_partial("B_UNSTABLE")
    final_state = translator.finalize_segment("B_FINAL")

    assert final_state.is_final is True
    assert final_state.committed_text == "Beta stabilized."
    assert final_state.provisional_text == ""
    assert translator.segment_status == SegmentStatus.FLUSHED


def test_adversarial_10_multiple_sequential_segments():
    """
    10. Multiple sequential segments:
    3 consecutive conversational turns, zero cross-segment state leakage.
    """
    mapping = {
        "S1_part": "Hello", "S1_fin": "Hello everyone.",
        "S2_part": "Welcome", "S2_fin": "Welcome to the stream.",
        "S3_part": "Today", "S3_fin": "Today we are playing games."
    }
    engine = MockMTEngine(mapping)
    translator = IncrementalTranslator(engine)

    # Segment 1
    translator.update_partial("S1_part")
    f1 = translator.finalize_segment("S1_fin")
    assert f1.segment_id == 1
    assert f1.committed_text == "Hello everyone."

    # Segment 2
    s2_1 = translator.update_partial("S2_part")
    assert s2_1.segment_id == 2
    assert s2_1.committed_text == ""  # Zero leakage
    f2 = translator.finalize_segment("S2_fin")
    assert f2.segment_id == 2
    assert f2.committed_text == "Welcome to the stream."

    # Segment 3
    s3_1 = translator.update_partial("S3_part")
    assert s3_1.segment_id == 3
    assert s3_1.committed_text == ""  # Zero leakage
    f3 = translator.finalize_segment("S3_fin")
    assert f3.segment_id == 3
    assert f3.committed_text == "Today we are playing games."

    assert translator.session_metrics.committed_prefix_revision_count == 0
