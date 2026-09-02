"""
test_protocol.py - Unit tests for Stage S5 versioned wire protocol.
"""

import pytest
import json
import time
from bridge.protocol import (
    PROTOCOL_VERSION,
    SubtitleUpdateMessage,
    SubtitleFinalMessage,
    StatusMessage,
    ErrorMessage,
    serialize_wire_message,
    parse_and_validate_wire_message
)


def test_protocol_subtitle_update_serialization():
    msg = SubtitleUpdateMessage(
        segment_id=1,
        source_revision=2,
        committed_text="I want to",
        provisional_text="go home",
        display_text="I want to go home",
        is_final=False
    )
    raw = serialize_wire_message(msg)
    data = json.loads(raw)

    assert data["version"] == PROTOCOL_VERSION
    assert data["type"] == "subtitle.update"
    assert data["segment_id"] == 1
    assert data["source_revision"] == 2
    assert data["committed_text"] == "I want to"
    assert data["provisional_text"] == "go home"
    assert data["is_final"] is False
    assert "timestamp_ms" in data


def test_protocol_subtitle_final_serialization():
    msg = SubtitleFinalMessage(
        segment_id=1,
        source_revision=3,
        committed_text="I want to go home.",
        provisional_text="",
        display_text="I want to go home.",
        is_final=True
    )
    raw = serialize_wire_message(msg)
    data = json.loads(raw)

    assert data["type"] == "subtitle.final"
    assert data["is_final"] is True
    assert data["committed_text"] == "I want to go home."


def test_protocol_validation_success():
    payload = json.dumps({
        "version": "1.0",
        "type": "subtitle.update",
        "segment_id": 2,
        "source_revision": 1,
        "committed_text": "Hello",
        "provisional_text": "world",
        "display_text": "Hello world",
        "is_final": False,
        "timestamp_ms": int(time.time() * 1000)
    })
    validated = parse_and_validate_wire_message(payload)
    assert validated["type"] == "subtitle.update"
    assert validated["committed_text"] == "Hello"


def test_protocol_validation_rejects_missing_fields():
    # Missing committed_text
    payload = json.dumps({
        "version": "1.0",
        "type": "subtitle.update",
        "segment_id": 2,
        "source_revision": 1
    })
    with pytest.raises(ValueError, match="Missing required field"):
        parse_and_validate_wire_message(payload)


def test_protocol_validation_rejects_bad_version():
    payload = json.dumps({
        "version": "99.0",
        "type": "subtitle.update",
        "segment_id": 1,
        "source_revision": 1,
        "committed_text": "A",
        "provisional_text": "B"
    })
    with pytest.raises(ValueError, match="Unsupported protocol version"):
        parse_and_validate_wire_message(payload)


def test_protocol_validation_rejects_malformed_json():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_and_validate_wire_message("NOT_JSON")
