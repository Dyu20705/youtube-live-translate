#!/usr/bin/env bash
# run_native_host.sh - Executable wrapper for Chrome Native Messaging Host

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$DIR/../../.." && pwd)"

VENV_PYTHON="$WORKSPACE/poc/s2-streaming-asr/.venv/bin/python"
HOST_SCRIPT="$DIR/native_messaging_host.py"

export PYTHONPATH="$WORKSPACE/poc/s5-extension-ui:$WORKSPACE/poc/s4-incremental-translation:$WORKSPACE/poc/s3-local-mt:$WORKSPACE/poc/s2-streaming-asr:$PYTHONPATH"

exec "$VENV_PYTHON" "$HOST_SCRIPT" "$@"
