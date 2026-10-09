#!/usr/bin/env bash
# Canonical production acceptance. Historical PoC suites are run separately.
set -euo pipefail
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_PYTHON="${YLT_TEST_PYTHON:-$WORKSPACE_DIR/poc/s2-streaming-asr/.venv/bin/python}"
TEST_SANDBOX="$(mktemp -d)"
trap 'rm -rf "$TEST_SANDBOX"' EXIT
unset PYTHONPATH PYTHONHOME
export YLT_DIST_DIR="$TEST_SANDBOX/dist"
export YLT_TEST_RUNTIME="$TEST_SANDBOX/runtime"
cd "$WORKSPACE_DIR"

echo '[1/4] Building local candidate packages (no release is uploaded)'
bash scripts/build_release.sh

echo '[2/4] Installing the extracted runtime with no source-tree model dependency'
mkdir "$TEST_SANDBOX/extracted"
"$TEST_PYTHON" -I - "$YLT_DIST_DIR" "$TEST_SANDBOX/extracted" <<'PY'
import json, sys, tarfile
from pathlib import Path
root, extracted = map(Path, sys.argv[1:])
manifest = json.loads((root / 'release_manifest.json').read_text())
with tarfile.open(root / manifest['artifacts']['runtime_tarball']['path']) as archive:
    archive.extractall(extracted, filter='data')
PY
# Synthetic origin only for the isolated stdio/installer checks. Real browser
# acceptance below obtains its ID from the actually loaded packaged extension.
EXTRACTED_RUNTIME="$TEST_SANDBOX/extracted/youtube-live-translate-runtime-linux-x86_64-v1.0.0"
bash "$EXTRACTED_RUNTIME/install.sh" --extension-id abcdefghijklmnopabcdefghijklmnop \
  --target-dir "$YLT_TEST_RUNTIME" --browser-config-dir "$TEST_SANDBOX/registry"
"$YLT_TEST_RUNTIME/venv/bin/python" -I "$YLT_TEST_RUNTIME/models/model_manager.py" verify
"$YLT_TEST_RUNTIME/venv/bin/python" -I "$YLT_TEST_RUNTIME/models/model_manager.py" self-test

echo '[3/4] Running canonical production tests (missing prerequisites fail, not skip)'
"$TEST_PYTHON" -m pytest tests/test_production_setup.py tests/test_installed_runtime.py tests/test_upgrade.py -q

echo '[4/4] Loading the packaged extension and checking actual tab and native messaging'
# A policy-blocked browser returns nonzero and is reported explicitly. A mocked
# Chrome API harness is not part of this production acceptance gate.
node tests/test_extension_loading.mjs

echo 'PASS: Canonical production package, installer, stdio and real-browser acceptance.'
echo 'Real YouTube audio capture, translation quality and long sessions still require product validation.'
