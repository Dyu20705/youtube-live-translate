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
unset PYTHONPATH PYTHONHOME
command -v python3 >/dev/null
python3 -I -c 'import sys; assert (3, 12) <= sys.version_info[:2] < (3, 14), "Python 3.12–3.13 is required"'
ARGS=(--source "$SOURCE_DIR" --target "$TARGET_DIR" --browser-config "$BROWSER_CONFIG_DIR" --extension-id "$EXTENSION_ID")
if [[ "$DOWNLOAD_MODELS" == 0 ]]; then
    ARGS+=(--skip-download)
fi
exec python3 -I "$SOURCE_DIR/host/install_runtime.py" "${ARGS[@]}"
