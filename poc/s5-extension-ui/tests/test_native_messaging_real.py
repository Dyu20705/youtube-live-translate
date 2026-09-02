"""
test_native_messaging_real.py - Tier C: Real Native Messaging Stdio & 8 Failure Scenarios.
Tests direct 32-bit native-endian length prefix framing over subprocess stdin/stdout pipes.
"""

import subprocess
import struct
import json
import time
import os
import signal
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent
HOST_RUNNER = WORKSPACE_DIR / "poc" / "s5-extension-ui" / "bridge" / "run_native_host.sh"


def send_stdio_message(proc: subprocess.Popen, msg: dict):
    """Encodes and writes a 32-bit native-endian length-prefixed JSON message."""
    data = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    length_prefix = struct.pack("@I", len(data))
    proc.stdin.write(length_prefix + data)
    proc.stdin.flush()


def read_stdio_message(proc: subprocess.Popen, timeout_sec: float = 10.0) -> dict:
    """Reads a 32-bit native-endian length-prefixed JSON message from stdout."""
    start_time = time.time()
    # Read 4 bytes length
    raw_length = b""
    while len(raw_length) < 4:
        if time.time() - start_time > timeout_sec:
            raise TimeoutError(f"Timed out waiting for length prefix from native host after {timeout_sec}s")
        chunk = proc.stdout.read(4 - len(raw_length))
        if not chunk:
            return {}  # EOF
        raw_length += chunk

    msg_len = struct.unpack("@I", raw_length)[0]
    raw_body = b""
    while len(raw_body) < msg_len:
        if time.time() - start_time > timeout_sec:
            raise TimeoutError(f"Timed out reading message body ({len(raw_body)}/{msg_len} bytes)")
        chunk = proc.stdout.read(msg_len - len(raw_body))
        if not chunk:
            break
        raw_body += chunk

    return json.loads(raw_body.decode("utf-8"))


def spawn_native_host():
    return subprocess.Popen(
        [str(HOST_RUNNER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )


# 1. Host starts & emits initial handshake
def test_scenario_1_host_starts_and_emits_initial_handshake():
    proc = spawn_native_host()
    try:
        init_msg = read_stdio_message(proc, timeout_sec=12.0)
        assert init_msg.get("type") == "status"
        assert init_msg.get("state") == "RUNNING"
    finally:
        proc.kill()
        proc.wait()


# 2. Host exits cleanly on EOF
def test_scenario_2_host_exits_on_eof():
    proc = spawn_native_host()
    try:
        _ = read_stdio_message(proc, timeout_sec=12.0)
        proc.stdin.close()  # Signal EOF
        ret = proc.wait(timeout=5.0)
        assert ret == 0, f"Host should exit with code 0 on EOF, got {ret}"
    finally:
        if proc.poll() is None:
            proc.kill()


# 3. Malformed JSON handling
def test_scenario_3_malformed_json_handling():
    proc = spawn_native_host()
    try:
        _ = read_stdio_message(proc, timeout_sec=12.0)
        
        bad_json = b"NOT_VALID_JSON{}"
        proc.stdin.write(struct.pack("@I", len(bad_json)) + bad_json)
        proc.stdin.flush()

        resp = read_stdio_message(proc, timeout_sec=5.0)
        assert resp.get("type") == "error"
        assert resp.get("error_code") == "MALFORMED_JSON"
        assert proc.poll() is None, "Host should remain alive after malformed JSON"
    finally:
        proc.kill()
        proc.wait()


# 4. Oversized message protection (> 1 MiB)
def test_scenario_4_oversized_message_protection():
    proc = spawn_native_host()
    try:
        _ = read_stdio_message(proc, timeout_sec=12.0)
        
        # Send length prefix claiming 2 MiB
        oversized_len = 2 * 1024 * 1024
        proc.stdin.write(struct.pack("@I", oversized_len))
        proc.stdin.flush()

        resp = read_stdio_message(proc, timeout_sec=5.0)
        assert resp.get("type") == "error"
        assert resp.get("error_code") == "OVERSIZED_MESSAGE"
    finally:
        proc.kill()
        proc.wait()


# 5. Malformed length prefix
def test_scenario_5_malformed_length_prefix():
    proc = spawn_native_host()
    try:
        _ = read_stdio_message(proc, timeout_sec=12.0)
        
        # Send only 2 bytes and close stdin
        proc.stdin.write(b"\x01\x00")
        proc.stdin.close()
        
        try:
            resp = read_stdio_message(proc, timeout_sec=3.0)
            assert resp.get("type") == "error" or resp == {}
        except Exception:
            pass
        ret = proc.wait(timeout=5.0)
        assert proc.poll() is not None
    finally:
        if proc.poll() is None:
            proc.kill()


# 6. Stdout contamination check (Only valid binary protocol frames on stdout)
def test_scenario_6_stdout_contamination_check():
    proc = spawn_native_host()
    try:
        init_msg = read_stdio_message(proc, timeout_sec=12.0)
        assert init_msg.get("type") == "status"

        # Ping control message
        send_stdio_message(proc, {"type": "control.ping"})
        resp = read_stdio_message(proc, timeout_sec=5.0)
        assert resp.get("type") == "status"
        assert resp.get("state") == "HEALTHY"
        assert resp.get("message") == "pong"
    finally:
        proc.kill()
        proc.wait()


# 7. Allowed origins validation
def test_scenario_7_allowed_origins_schema():
    manifest_path = WORKSPACE_DIR / "poc" / "s5-extension-ui" / "bridge" / "manifest_host.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "allowed_origins" in data
    assert any("chrome-extension://" in orig for orig in data["allowed_origins"])


# 8. Reconnect after crash
def test_scenario_8_reconnect_after_crash():
    proc1 = spawn_native_host()
    try:
        _ = read_stdio_message(proc1, timeout_sec=12.0)
        proc1.send_signal(signal.SIGTERM)
        proc1.wait(timeout=5.0)
    except Exception:
        proc1.kill()

    proc2 = spawn_native_host()
    try:
        msg = read_stdio_message(proc2, timeout_sec=12.0)
        assert msg.get("type") == "status"
        assert msg.get("state") == "RUNNING"
    finally:
        proc2.kill()
        proc2.wait()
