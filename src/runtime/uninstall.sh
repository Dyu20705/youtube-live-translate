#!/usr/bin/env bash
set -euo pipefail
RUNTIME_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 - "$RUNTIME_ROOT" <<'PY'
import json
from pathlib import Path
import sys
runtime = Path(sys.argv[1])
record = runtime / 'installation.json'
if record.exists():
    for name in json.loads(record.read_text())['registrations']:
        path = Path(name)
        if path.exists() and json.loads(path.read_text()).get('path') == str(runtime / 'bin/youtube-live-translate-host'):
            path.unlink()
print(f'Browser registrations removed. Runtime and models retained at {runtime}.')
PY
