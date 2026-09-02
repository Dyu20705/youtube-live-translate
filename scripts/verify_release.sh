#!/usr/bin/env bash
# verify_release.sh - Comprehensive Automated Release Verification Gate for V1

set -e

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$WORKSPACE_DIR/poc/s2-streaming-asr/.venv/bin/python"
PYTEST_BIN="$WORKSPACE_DIR/poc/s2-streaming-asr/.venv/bin/pytest"
DIST_DIR="$WORKSPACE_DIR/dist"

echo "======================================================================"
echo "  YouTube Live Translate v1.0.0 — Automated Release Verification Gate"
echo "======================================================================"

# 1. Ensure fresh release build
echo "[Gate 1/7] Building & packaging release artifacts..."
"$WORKSPACE_DIR/scripts/build_release.sh" > /dev/null
echo "  PASS: Build packages generated successfully."

# 2. Release Package Audit & Checksum Verification
echo "[Gate 2/7] Auditing release artifacts and checksums..."
python3 - << PY_EOF
import os
import json
import tarfile
import zipfile
import hashlib
from pathlib import Path

dist_dir = Path("$DIST_DIR")
manifest_path = dist_dir / "release_manifest.json"
assert manifest_path.exists(), "release_manifest.json missing"

with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

# Verify SHA256
for key, spec in manifest["artifacts"].items():
    file_path = dist_dir / spec["path"]
    assert file_path.exists(), f"Artifact file {file_path} does not exist"
    
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    actual_sha = h.hexdigest()
    assert actual_sha == spec["sha256"], f"SHA256 mismatch for {key}: expected {spec['sha256']}, got {actual_sha}"

# Audit Extension Zip contents
ext_zip = dist_dir / manifest["artifacts"]["extension_zip"]["path"]
with zipfile.ZipFile(ext_zip, "r") as z:
    names = z.namelist()
    assert any("manifest.json" in n for n in names), "manifest.json missing from extension zip"
    assert any("icons/icon-128.png" in n for n in names), "icons missing from extension zip"
    assert not any("__pycache__" in n for n in names), "Extension zip contains __pycache__"
    assert not any(".pyc" in n for n in names), "Extension zip contains .pyc files"

# Audit Runtime Tarball contents
rt_tar = dist_dir / manifest["artifacts"]["runtime_tarball"]["path"]
with tarfile.open(rt_tar, "r:gz") as t:
    names = t.getnames()
    assert any("install.sh" in n for n in names), "install.sh missing from runtime tarball"
    assert any("bin/youtube-live-translate-host" in n for n in names), "launcher binary missing"
    assert not any("__pycache__" in n for n in names), "Runtime tarball contains __pycache__"
    assert not any(".pytest_cache" in n for n in names), "Runtime tarball contains .pytest_cache"
    assert not any(".venv" in n for n in names), "Runtime tarball contains dev venv"
    assert not any("nllb" in n.lower() for n in names), "Runtime tarball contains S3 NLLB weights"
    assert not any(".wav" in n for n in names), "Runtime tarball contains test wav fixtures"

print("  PASS: All release package integrity and hygiene audits passed 100%.")
PY_EOF

# 3. Model Integrity Verification
echo "[Gate 3/7] Verifying Model Manager and SHA256 integrity..."
python3 "$WORKSPACE_DIR/src/runtime/models/model_manager.py" verify
echo "  PASS: Model integrity verification passed."

# 4. S2 Frozen Performance Contract Gate
echo "[Gate 4/7] Executing Stage S2 Frozen Performance Contract Gate..."
PYTHONPATH="$WORKSPACE_DIR/poc/s2-streaming-asr" \
"$PYTHON_BIN" "$WORKSPACE_DIR/poc/s2-streaming-asr/scripts/run_regression_check.py"
echo "  PASS: S2 Frozen Performance Contract passed."

# 5. S3 & S4 Regression Tests
echo "[Gate 5/7] Executing Stage S3 MT & Stage S4 Incremental Translation tests..."
PYTHONPATH="$WORKSPACE_DIR/poc/s3-local-mt" \
"$PYTEST_BIN" "$WORKSPACE_DIR/poc/s3-local-mt/tests" -q

PYTHONPATH="$WORKSPACE_DIR/poc/s4-incremental-translation:$WORKSPACE_DIR/poc/s3-local-mt:$WORKSPACE_DIR/poc/s2-streaming-asr" \
"$PYTEST_BIN" "$WORKSPACE_DIR/poc/s4-incremental-translation/tests" -q
echo "  PASS: S3 and S4 test suites passed."

# 6. Install & Register Canonical V1 Runtime
echo "[Gate 6/7] Installing & registering canonical V1 runtime in ~/.local/share/youtube-live-translate..."
"$WORKSPACE_DIR/src/runtime/install.sh" --extension-id "v1-production-extension-id" > /dev/null

# 7. S5 Presentation, Geometry & Integration Tests + Fresh-Install E2E
echo "[Gate 7/7] Executing S5 Renderer, Geometry & Real Native Messaging tests..."
node "$WORKSPACE_DIR/poc/s5-extension-ui/tests/test_renderer.mjs" > /dev/null
node "$WORKSPACE_DIR/poc/s5-extension-ui/tests/test_anchor_displacement.mjs" > /dev/null
node "$WORKSPACE_DIR/poc/s5-extension-ui/tests/test_browser_geometry.mjs" > /dev/null

PYTHONPATH="$WORKSPACE_DIR/poc/s5-extension-ui:$WORKSPACE_DIR/poc/s4-incremental-translation:$WORKSPACE_DIR/poc/s3-local-mt:$WORKSPACE_DIR/poc/s2-streaming-asr" \
"$PYTEST_BIN" \
  "$WORKSPACE_DIR/poc/s5-extension-ui/tests/test_protocol.py" \
  "$WORKSPACE_DIR/poc/s5-extension-ui/tests/test_runtime_pipeline.py" \
  "$WORKSPACE_DIR/poc/s5-extension-ui/tests/test_packaging_contract.py" \
  "$WORKSPACE_DIR/poc/s5-extension-ui/tests/test_native_messaging_real.py" \
  "$WORKSPACE_DIR/poc/s5-extension-ui/tests/test_fault_injection.py" \
  "$WORKSPACE_DIR/poc/s5-extension-ui/tests/test_e2e_streaming.py" -q

python3 - << PY_EOF
import os
import sys
import subprocess
import struct
import json
from pathlib import Path

installed_dir = Path.home() / ".local" / "share" / "youtube-live-translate"
host_bin = installed_dir / "bin" / "youtube-live-translate-host"
assert host_bin.exists() and os.access(host_bin, os.X_OK), "Installed host binary not executable"

env = os.environ.copy()
env["PYTHONPATH"] = f"{installed_dir}:{env.get('PYTHONPATH', '')}"

proc = subprocess.Popen(
    ["$PYTHON_BIN", str(installed_dir / "host" / "native_messaging_host.py")],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env,
    cwd=str(installed_dir)
)

def read_msg():
    raw_len = proc.stdout.read(4)
    if not raw_len: return None
    mlen = struct.unpack("@I", raw_len)[0]
    return json.loads(proc.stdout.read(mlen).decode("utf-8"))

def send_msg(msg):
    d = json.dumps(msg).encode("utf-8")
    proc.stdin.write(struct.pack("@I", len(d)) + d)
    proc.stdin.flush()

# Read init
init = read_msg()
assert init.get("state") == "RUNNING", f"Unexpected state: {init}"

# Ping
send_msg({"type": "control.ping"})
pong = read_msg()
assert pong.get("state") == "HEALTHY", f"Unexpected ping response: {pong}"

# Stop
send_msg({"type": "control.stop"})
stop = read_msg()
assert stop.get("state") == "STOPPED"

proc.stdin.close()
proc.wait(timeout=5.0)
assert proc.returncode == 0
print("  PASS: End-to-end native messaging lifecycle verified.")
PY_EOF

echo "======================================================================"
echo "  VERDICT: V1 RELEASE VERIFICATION GATE 100% PASSED (PASS)"
echo "======================================================================"
