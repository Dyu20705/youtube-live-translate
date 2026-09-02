"""
protocol.py - Versioned wire protocol schemas and validators for YouTube Live Translate.
Version: 1.0
"""

from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass, asdict
import json
import time

PROTOCOL_VERSION = "1.0"

MessageType = Literal[
    "subtitle.update",
    "subtitle.final",
    "status",
    "error",
    "control.start",
    "control.stop",
    "control.ping",
    "control.flush"
]

RuntimeState = Literal[
    "NOT_INSTALLED",
    "READY",
    "STARTING",
    "RUNNING",
    "DEGRADED",
    "RECOVERING",
    "STOPPED",
    "ERROR"
]


@dataclass(frozen=True)
class SubtitleUpdateMessage:
    version: str = PROTOCOL_VERSION
    type: Literal["subtitle.update"] = "subtitle.update"
    segment_id: int = 1
    source_revision: int = 1
    committed_text: str = ""
    provisional_text: str = ""
    display_text: str = ""
    is_final: bool = False
    timestamp_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d["timestamp_ms"]:
            d["timestamp_ms"] = int(time.time() * 1000)
        return d


@dataclass(frozen=True)
class SubtitleFinalMessage:
    version: str = PROTOCOL_VERSION
    type: Literal["subtitle.final"] = "subtitle.final"
    segment_id: int = 1
    source_revision: int = 1
    committed_text: str = ""
    provisional_text: str = ""
    display_text: str = ""
    is_final: bool = True
    timestamp_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d["timestamp_ms"]:
            d["timestamp_ms"] = int(time.time() * 1000)
        return d


@dataclass(frozen=True)
class StatusMessage:
    version: str = PROTOCOL_VERSION
    type: Literal["status"] = "status"
    state: RuntimeState = "READY"
    message: str = ""
    metrics: Optional[Dict[str, Any]] = None
    timestamp_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d["timestamp_ms"]:
            d["timestamp_ms"] = int(time.time() * 1000)
        return d


@dataclass(frozen=True)
class ErrorMessage:
    version: str = PROTOCOL_VERSION
    type: Literal["error"] = "error"
    error_code: str = "GENERIC_ERROR"
    message: str = ""
    timestamp_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d["timestamp_ms"]:
            d["timestamp_ms"] = int(time.time() * 1000)
        return d


def serialize_wire_message(msg: Any) -> str:
    """Serializes a dataclass message or dictionary to a JSON string."""
    if hasattr(msg, "to_dict"):
        data = msg.to_dict()
    elif isinstance(msg, dict):
        data = msg
    else:
        raise ValueError(f"Unsupported message type: {type(msg)}")
    return json.dumps(data, ensure_ascii=False)


def parse_and_validate_wire_message(raw_json: str) -> Dict[str, Any]:
    """
    Parses and strictly validates incoming wire messages against Version 1.0 schema.
    Raises ValueError on malformed payloads or unknown types.
    """
    if len(raw_json) > 65536:
        raise ValueError("Payload exceeds maximum size limit (64 KiB)")

    try:
        data = json.loads(raw_json)
    except Exception as e:
        raise ValueError(f"Invalid JSON payload: {e}")

    if not isinstance(data, dict):
        raise ValueError("Payload must be a JSON object")

    msg_type = data.get("type")
    if not msg_type:
        raise ValueError("Missing required field 'type'")

    version = data.get("version", PROTOCOL_VERSION)
    if version != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported protocol version: {version} (expected {PROTOCOL_VERSION})")

    if msg_type == "subtitle.update":
        required_fields = ["segment_id", "source_revision", "committed_text", "provisional_text"]
        for f in required_fields:
            if f not in data:
                raise ValueError(f"Missing required field '{f}' for subtitle.update")
        if not isinstance(data["segment_id"], int) or not isinstance(data["source_revision"], int):
            raise ValueError("segment_id and source_revision must be integers")
        if data["segment_id"] < 0 or data["source_revision"] < 0:
            raise ValueError("segment_id and source_revision must be non-negative")

    elif msg_type == "subtitle.final":
        required_fields = ["segment_id", "source_revision", "committed_text"]
        for f in required_fields:
            if f not in data:
                raise ValueError(f"Missing required field '{f}' for subtitle.final")
        if not isinstance(data["segment_id"], int) or not isinstance(data["source_revision"], int):
            raise ValueError("segment_id and source_revision must be integers")
        if data["segment_id"] < 0 or data["source_revision"] < 0:
            raise ValueError("segment_id and source_revision must be non-negative")

    elif msg_type == "status":
        if "state" not in data:
            raise ValueError("Missing required field 'state' for status message")
        valid_states = {"NOT_INSTALLED", "READY", "STARTING", "RUNNING", "DEGRADED", "RECOVERING", "STOPPED", "ERROR"}
        if data["state"] not in valid_states:
            raise ValueError(f"Invalid runtime state: {data['state']}")

    elif msg_type == "error":
        if "error_code" not in data or "message" not in data:
            raise ValueError("Missing 'error_code' or 'message' for error message")

    elif msg_type in ("control.start", "control.stop", "control.ping", "control.flush"):
        pass

    else:
        raise ValueError(f"Unknown message type: {msg_type}")

    return data
