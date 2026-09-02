#!/usr/bin/env bash
# install.sh - Automated installer for YouTube Live Translate Local Native Runtime

set -e

echo "======================================================================"
echo "  YouTube Live Translate — Local Native Runtime Installer (Linux x86_64)"
echo "======================================================================"

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/share/youtube-live-translate"
EXTENSION_ID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --extension-id)
      EXTENSION_ID="$2"
      shift 2
      ;;
    --target-dir)
      TARGET_DIR="$2"
      shift 2
      ;;
    *)
      if [[ "$1" != --* ]] && [[ -z "$EXTENSION_ID" ]]; then
        EXTENSION_ID="$1"
      fi
      shift
      ;;
  esac
done

if [[ -z "$EXTENSION_ID" ]]; then
    # Fallback to standard development extension ID placeholder if not specified
    EXTENSION_ID="youtube-live-translate-v1"
fi

# 1. System Requirements Check
echo "[1/5] Checking system environment..."
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "ERROR: This release supports Linux x86_64 only." >&2
    exit 1
fi

if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "ERROR: Unsupported architecture: $(uname -m). Required: x86_64." >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required but not installed." >&2
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Detected Linux $(uname -m), Python $PYTHON_VER"

# 2. Setup Runtime Files
echo "[2/5] Setting up runtime files in $TARGET_DIR..."
mkdir -p "$TARGET_DIR"
cp -r "$SOURCE_DIR/bin" "$TARGET_DIR/"
cp -r "$SOURCE_DIR/host" "$TARGET_DIR/"
cp -r "$SOURCE_DIR/engines" "$TARGET_DIR/"
cp -r "$SOURCE_DIR/policy" "$TARGET_DIR/"
cp -r "$SOURCE_DIR/models" "$TARGET_DIR/"
chmod +x "$TARGET_DIR/bin/youtube-live-translate-host"
chmod +x "$TARGET_DIR/host/native_messaging_host.py"

if [ -f "$SOURCE_DIR/uninstall.sh" ]; then
    cp "$SOURCE_DIR/uninstall.sh" "$TARGET_DIR/"
    chmod +x "$TARGET_DIR/uninstall.sh"
fi

# 3. Setup / Link Models
echo "[3/5] Verifying AI model assets..."
# Check potential workspace directories
WORKSPACE_CANDIDATE="$(cd "$SOURCE_DIR/../.." 2>/dev/null && pwd || true)"
WORKSPACE_ROOT="$(cd "$SOURCE_DIR/../../.." 2>/dev/null && pwd || true)"

ASR_MODEL_NAME="sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10"
MT_MODEL_NAME="opus-mt-ja-en-ct2-int8"

# Check if models exist in SOURCE_DIR
if [ -d "$SOURCE_DIR/models/$ASR_MODEL_NAME" ]; then
    cp -r "$SOURCE_DIR/models/$ASR_MODEL_NAME" "$TARGET_DIR/models/" 2>/dev/null || true
elif [ -d "$WORKSPACE_CANDIDATE/poc/s2-streaming-asr/models/$ASR_MODEL_NAME" ]; then
    cp -r "$WORKSPACE_CANDIDATE/poc/s2-streaming-asr/models/$ASR_MODEL_NAME" "$TARGET_DIR/models/" 2>/dev/null || true
fi

if [ -d "$SOURCE_DIR/models/$MT_MODEL_NAME" ]; then
    cp -r "$SOURCE_DIR/models/$MT_MODEL_NAME" "$TARGET_DIR/models/" 2>/dev/null || true
elif [ -d "$WORKSPACE_CANDIDATE/poc/s3-local-mt/models/$MT_MODEL_NAME" ]; then
    cp -r "$WORKSPACE_CANDIDATE/poc/s3-local-mt/models/$MT_MODEL_NAME" "$TARGET_DIR/models/" 2>/dev/null || true
fi

# Run model verification
python3 "$TARGET_DIR/models/model_manager.py" verify || {
    echo "WARNING: Model verification reported missing or incomplete files."
}

# 4. Register Chrome / Chromium Native Messaging Host Manifest
echo "[4/5] Registering Native Messaging Host Manifest with browser..."
HOST_BIN="$TARGET_DIR/bin/youtube-live-translate-host"

CHROME_HOST_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
CHROMIUM_HOST_DIR="$HOME/.config/chromium/NativeMessagingHosts"
mkdir -p "$CHROME_HOST_DIR" "$CHROMIUM_HOST_DIR"

python3 -c "
import json
from pathlib import Path

manifest = {
    'name': 'com.duy.youtube_live_translate',
    'description': 'YouTube Live Translate Local AI Native Messaging Host',
    'path': '${HOST_BIN}',
    'type': 'stdio',
    'allowed_origins': [
        'chrome-extension://${EXTENSION_ID}/'
    ]
}

for d in [Path('${CHROME_HOST_DIR}'), Path('${CHROMIUM_HOST_DIR}')]:
    d.mkdir(parents=True, exist_ok=True)
    with open(d / 'com.duy.youtube_live_translate.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
"

echo "  Registered host manifest at: $CHROME_HOST_DIR/com.duy.youtube_live_translate.json"

# 5. Verification & Self-Test
echo "[5/5] Performing runtime self-test..."
if [ -x "$HOST_BIN" ]; then
    echo "  Host binary executable: PASS"
else
    echo "ERROR: Host binary not executable: $HOST_BIN" >&2
    exit 1
fi

echo "======================================================================"
echo "  SUCCESS: YouTube Live Translate Native Runtime Installed Successfully!"
echo "======================================================================"
