"""
test_fault_injection.py - Tier F: Fault injection, process crash recovery, reconnect storms, and security fuzzing.
"""

import pytest
import subprocess
import json
import time
import signal
import struct
from pathlib import Path

from bridge.protocol import parse_and_validate_wire_message

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent
HOST_RUNNER = WORKSPACE_DIR / "poc" / "s5-extension-ui" / "bridge" / "run_native_host.sh"


def test_fault_injection_process_sigkill_recovery():
    """Verifies that a SIGKILL (kill -9) on the native host process allows immediate clean restart."""
    # Start instance 1
    p1 = subprocess.Popen([str(HOST_RUNNER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Read initial prefix
    raw_len = p1.stdout.read(4)
    assert len(raw_len) == 4
    msg_len = struct.unpack("@I", raw_len)[0]
    _ = p1.stdout.read(msg_len)

    # Hard kill
    p1.kill()
    p1.wait()
    assert p1.poll() is not None

    # Immediate restart instance 2
    p2 = subprocess.Popen([str(HOST_RUNNER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        raw_len2 = p2.stdout.read(4)
        assert len(raw_len2) == 4
        msg_len2 = struct.unpack("@I", raw_len2)[0]
        init_json = json.loads(p2.stdout.read(msg_len2).decode("utf-8"))
        assert init_json.get("state") == "RUNNING"
    finally:
        p2.kill()
        p2.wait()


def test_security_fuzzing_malformed_and_adversarial_payloads():
    """Fuzzes protocol parser with adversarial and malformed wire messages."""
    adversarial_inputs = [
        # Missing fields
        json.dumps({}),
        json.dumps({"type": "subtitle.update"}),
        
        # Negative revision / segment
        json.dumps({"version": "1.0", "type": "subtitle.update", "segment_id": -1, "source_revision": 1, "committed_text": "A", "provisional_text": "B"}),
        json.dumps({"version": "1.0", "type": "subtitle.update", "segment_id": 1, "source_revision": -10, "committed_text": "A", "provisional_text": "B"}),

        # Unsupported version
        json.dumps({"version": "99.0", "type": "subtitle.update", "segment_id": 1, "source_revision": 1, "committed_text": "A", "provisional_text": "B"}),

        # Huge string injection
        json.dumps({"version": "1.0", "type": "subtitle.update", "segment_id": 1, "source_revision": 1, "committed_text": "X" * 200000, "provisional_text": ""}),

        # Non-JSON bytes
        "NON_JSON_CORRUPTED_STREAM",
        "\x00\x01\x02\x03\xff\xfe",
    ]

    rejected_count = 0
    for payload in adversarial_inputs:
        try:
            parse_and_validate_wire_message(payload)
        except (ValueError, TypeError, json.JSONDecodeError):
            rejected_count += 1

    # All adversarial inputs must be safely rejected
    assert rejected_count == len(adversarial_inputs), f"Expected all {len(adversarial_inputs)} adversarial inputs to be rejected, got {rejected_count}"
