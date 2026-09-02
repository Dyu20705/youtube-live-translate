"""
test_runtime_pipeline.py - Tests for StreamingTranslationRuntime.
"""

import pytest
import json
from bridge.runtime_pipeline import StreamingTranslationRuntime
from bridge.protocol import parse_and_validate_wire_message


class MockMTEngine:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}

    def translate(self, text: str, beam_size: int = 1):
        target = self.mapping.get(text, text)
        class Result:
            def __init__(self, t):
                self.target_text = t
        return Result(target)




def test_runtime_pipeline_text_processing():
    mapping = {
        "東京に": "Tokyo to",
        "東京に行き": "I went to Tokyo",
        "東京に行きました。": "I went to Tokyo."
    }
    mt_engine = MockMTEngine(mapping)
    runtime = StreamingTranslationRuntime(mt_engine=mt_engine, k=2, buffer=1)
    runtime.start()

    # Step 1
    raw1 = runtime.process_text_partial("東京に", is_final=False)
    data1 = parse_and_validate_wire_message(raw1)
    assert data1["type"] == "subtitle.update"
    assert data1["segment_id"] == 1
    assert data1["source_revision"] == 1

    # Step 2
    raw2 = runtime.process_text_partial("東京に行き", is_final=False)
    data2 = parse_and_validate_wire_message(raw2)
    assert data2["source_revision"] == 2

    # Step 3 (Finalize)
    raw3 = runtime.process_text_partial("東京に行きました。", is_final=True)
    data3 = parse_and_validate_wire_message(raw3)
    assert data3["type"] == "subtitle.final"
    assert data3["is_final"] is True
    assert data3["committed_text"] == "I went to Tokyo."
