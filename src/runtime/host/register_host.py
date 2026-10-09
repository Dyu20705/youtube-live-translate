#!/usr/bin/env python3
"""Register a verified runtime for one actual Chrome extension ID."""
import json
import os
from pathlib import Path
import re
import sys


def register(runtime, browser_config, extension_id):
    if not re.fullmatch(r'[a-p]{32}', extension_id):
        raise ValueError('Expected the actual 32-character Chrome extension ID')
    runtime, config = Path(runtime).resolve(), Path(browser_config).resolve()
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
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(manifest, indent=2) + '\n')
        os.replace(temporary, path)
    (runtime / 'installation.json').write_text(json.dumps({'registrations': [str(p) for p in paths]}, indent=2) + '\n')
    return paths


if __name__ == '__main__':
    register(*sys.argv[1:])
