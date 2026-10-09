#!/usr/bin/env bash
# Isolated Linux CPU runtime installer. Register only after verified inference.
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/share/youtube-live-translate"
BROWSER_CONFIG_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}"
EXTENSION_ID=""
DOWNLOAD_MODELS=1

usage() {
    echo "Usage: $0 --extension-id <32 letters a-p> [--target-dir DIR] [--browser-config-dir DIR] [--skip-download]"
}
while [[ $# -gt 0 ]]; do
    case "$1" in
        --extension-id|--target-dir|--browser-config-dir)
            if [[ $# -lt 2 || -z "$2" || "$2" == --* ]]; then
                usage >&2; exit 2
            fi
            case "$1" in
                --extension-id) EXTENSION_ID="$2" ;;
                --target-dir) TARGET_DIR="$2" ;;
                --browser-config-dir) BROWSER_CONFIG_DIR="$2" ;;
            esac
            shift 2 ;;
        --skip-download) DOWNLOAD_MODELS=0; shift ;;
        --help|-h) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done
if [[ ! "$EXTENSION_ID" =~ ^[a-p]{32}$ ]]; then
    echo "ERROR: --extension-id must be the actual 32-character ID from chrome://extensions/ (letters a-p)." >&2
    exit 2
fi
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
    echo "ERROR: Linux x86_64 is required." >&2; exit 1
fi
command -v python3 >/dev/null
python3 -c 'import sys; assert (3, 12) <= sys.version_info[:2] < (3, 14), "Python 3.12–3.13 is required"'
TARGET_DIR="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$TARGET_DIR")"
if [[ "$TARGET_DIR" == "$SOURCE_DIR" || "$TARGET_DIR" == "$SOURCE_DIR/"* || "$TARGET_DIR" == / ]]; then
    echo "ERROR: Install into a separate runtime directory." >&2; exit 2
fi

mkdir -p "$TARGET_DIR"
for directory in bin host engines policy models; do
    cp -R "$SOURCE_DIR/$directory" "$TARGET_DIR/"
done
cp "$SOURCE_DIR/requirements.txt" "$SOURCE_DIR/requirements-models.txt" "$SOURCE_DIR/uninstall.sh" "$TARGET_DIR/"
chmod +x "$TARGET_DIR/bin/youtube-live-translate-host" "$TARGET_DIR/uninstall.sh"
python3 -m venv "$TARGET_DIR/venv"
PYTHON_BIN="$TARGET_DIR/venv/bin/python"
"$PYTHON_BIN" -m pip install --disable-pip-version-check -r "$TARGET_DIR/requirements.txt"
"$PYTHON_BIN" -m pip check
if [[ "$DOWNLOAD_MODELS" == 1 ]]; then
    # PyTorch is needed for conversion only, not local CTranslate2 inference.
    if ! "$PYTHON_BIN" "$TARGET_DIR/models/model_manager.py" verify >/dev/null 2>&1; then
        "$PYTHON_BIN" -m pip install --disable-pip-version-check -r "$TARGET_DIR/requirements-models.txt"
        "$PYTHON_BIN" "$TARGET_DIR/models/model_manager.py" download
    fi
fi
"$PYTHON_BIN" "$TARGET_DIR/models/model_manager.py" verify
"$PYTHON_BIN" "$TARGET_DIR/models/model_manager.py" self-test

# A failed dependency install, acquisition, verification, or inference must never
# leave a newly registered host or print SUCCESS.
"$PYTHON_BIN" "$TARGET_DIR/host/register_host.py" "$TARGET_DIR" "$BROWSER_CONFIG_DIR" "$EXTENSION_ID"

echo "SUCCESS: Verified CPU runtime installed and registered for extension $EXTENSION_ID at $TARGET_DIR"
