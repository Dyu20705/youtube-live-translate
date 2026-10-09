#!/usr/bin/env bash
set -euo pipefail
RUNTIME_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -I - "$RUNTIME_ROOT" <<'PY'
import json
from pathlib import Path
import sys
runtime = Path(sys.argv[1])
record = runtime / 'installation.json'
if record.exists():
    installation = json.loads(record.read_text())
    launcher = installation.get('launcher', str(runtime / 'bin/youtube-live-translate-host'))
    if Path(launcher).parent.parent.resolve() != runtime.resolve():
        raise SystemExit('This generation is inactive; active registrations were preserved.')
    for name in installation['registrations']:
        path = Path(name)
        if path.exists() and json.loads(path.read_text()).get('path') == launcher:
            path.unlink()
print(f'Browser registrations removed. Runtime and models retained at {runtime}.')
PY
