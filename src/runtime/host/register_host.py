#!/usr/bin/env python3
"""Register a validated runtime; restore all registrations if a write fails."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def register(runtime, browser_config, extension_id):
    if not re.fullmatch(r'[a-p]{32}', extension_id):
        raise ValueError('Expected the actual 32-character Chrome extension ID')
    runtime = Path(os.path.abspath(runtime))  # Registration must retain the alias.
    config = Path(browser_config).resolve()
    launcher = runtime / 'bin' / 'youtube-live-translate-host'
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise ValueError('Runtime launcher is missing or not executable')
    manifest = {'name': 'com.duy.youtube_live_translate',
                'description': 'YouTube Live Translate Local CPU Runtime',
                'path': str(launcher), 'type': 'stdio',
                'allowed_origins': [f'chrome-extension://{extension_id}/']}
    paths = [config / browser / 'NativeMessagingHosts' / 'com.duy.youtube_live_translate.json'
             for browser in ('google-chrome', 'chromium')]
    for path in paths:
        if path.exists() and json.loads(path.read_text()).get('path') != str(launcher):
            raise ValueError(f'Refusing to replace a different registered runtime: {path}')
    record = runtime / 'installation.json'
    snapshots = {path: path.read_bytes() if path.exists() else None for path in [*paths, record]}
    written = []
    try:
        for path in paths:
            atomic_write(path, (json.dumps(manifest, indent=2) + '\n').encode())
            written.append(path)
        atomic_write(record, (json.dumps({'registrations': [str(p) for p in paths],
                                          'launcher': str(launcher),
                                          'generation': str(runtime.resolve())}, indent=2) + '\n').encode())
        written.append(record)
    except BaseException:
        for path in reversed(written):
            content = snapshots[path]
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, content)
        raise
    return paths


if __name__ == '__main__':
    register(*sys.argv[1:])
