"""Real dependency/model/promotion failures must preserve the installed runtime."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
ID = 'abcdefghijklmnop' * 2


@pytest.fixture(scope='module')
def working_runtime(tmp_path_factory):
    configured = os.environ.get('YLT_TEST_RUNTIME')
    if not configured:
        pytest.fail('YLT_TEST_RUNTIME is required for upgrade acceptance')
    root = tmp_path_factory.mktemp('upgrade')
    runtime = root / 'active'
    # An actual installed generation, including dependencies and verified models.
    shutil.copytree(Path(configured).resolve(), runtime, symlinks=True)
    registry = root / 'registry'
    registration = ROOT / 'src/runtime/host/register_host.py'
    subprocess.run([str(runtime / 'venv/bin/python'), '-I', str(registration), str(runtime), str(registry), ID], check=True)
    return root, runtime, registry


def snapshot(runtime, registry):
    paths = [runtime / 'bin/youtube-live-translate-host', runtime / 'host/native_messaging_host.py',
             runtime / 'requirements.txt', runtime / 'installation.json', runtime / 'venv/pyvenv.cfg']
    paths += list((runtime / 'venv/lib').glob('python*/site-packages/numpy/__init__.py'))
    paths += list(registry.rglob('com.duy.youtube_live_translate.json'))
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def assert_healthy(runtime):
    python = runtime / 'venv/bin/python'
    manager = runtime / 'models/model_manager.py'
    subprocess.run([str(python), '-I', str(manager), 'verify'], check=True)
    subprocess.run([str(python), '-I', str(manager), 'self-test'], check=True)
    # Actual native host handshake/ping/stop; no substituted engine or protocol.
    import json, queue, struct, threading
    process = subprocess.Popen([str(runtime / 'bin/youtube-live-translate-host')],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    messages = queue.Queue()
    def reader():
        while True:
            header = process.stdout.read(4)
            if not header:
                return
            messages.put(json.loads(process.stdout.read(struct.unpack('@I', header)[0])))
    threading.Thread(target=reader, daemon=True).start()
    try:
        assert messages.get(timeout=30).get('state') == 'RUNNING'
        for request, state in [('control.ping', 'HEALTHY'), ('control.stop', 'STOPPED')]:
            data = json.dumps({'type': request}).encode()
            process.stdin.write(struct.pack('@I', len(data)) + data)
            process.stdin.flush()
            assert messages.get(timeout=30).get('state') == state
        process.stdin.close()
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)


@pytest.mark.parametrize('failure', ['dependency', 'model', 'registration'])
def test_failed_upgrade_preserves_working_installation(working_runtime, tmp_path, failure):
    _, runtime, registry = working_runtime
    before = snapshot(runtime, registry)
    old_generation = runtime.resolve()
    source = tmp_path / 'package'
    shutil.copytree(ROOT / 'src/runtime', source, ignore=shutil.ignore_patterns('__pycache__'))
    test_registry = registry
    if failure == 'dependency':
        # Real pip failure after a separate candidate venv has been initialized.
        (source / 'requirements.txt').write_text('--no-index\nnumpy==0.0.0\n')
    elif failure == 'model':
        manifest = json.loads((source / 'models/model_manifest.json').read_text())
        name = manifest['models']['asr']['name']
        broken = source / 'models' / name
        broken.mkdir()
        (broken / 'tokens.txt').write_bytes(b'damaged candidate assets')
    else:
        # Real filesystem error after the first registration write. The old
        # profile is untouched; the partially written new profile must roll back.
        test_registry = tmp_path / 'bad-registry'
        test_registry.mkdir()
        (test_registry / 'chromium').write_text('not a directory')
    result = subprocess.run(['bash', str(source / 'install.sh'), '--extension-id', ID,
                             '--target-dir', str(runtime), '--browser-config-dir', str(test_registry),
                             '--skip-download'], capture_output=True, text=True, timeout=240)
    assert result.returncode != 0, result.stdout
    assert 'SUCCESS' not in result.stdout
    assert snapshot(runtime, registry) == before
    assert runtime.resolve() == old_generation
    if failure == 'registration':
        assert not (test_registry / 'google-chrome/NativeMessagingHosts/com.duy.youtube_live_translate.json').exists()
    assert_healthy(runtime)


def test_successful_upgrade_promotes_verified_generation(working_runtime):
    _, runtime, registry = working_runtime
    previous = runtime.resolve()
    subprocess.run(['bash', str(ROOT / 'src/runtime/install.sh'), '--extension-id', ID,
                    '--target-dir', str(runtime), '--browser-config-dir', str(registry),
                    '--skip-download'], check=True, timeout=240)
    assert runtime.is_symlink()
    assert runtime.resolve() != previous
    assert (runtime.resolve() / 'venv/bin/python').exists()
    for path in registry.rglob('com.duy.youtube_live_translate.json'):
        assert json.loads(path.read_text())['path'] == str(runtime / 'bin/youtube-live-translate-host')
    assert_healthy(runtime)


def test_failed_registration_after_symlink_upgrade_preserves_active(working_runtime, tmp_path):
    assert working_runtime[1].is_symlink()
    test_failed_upgrade_preserves_working_installation(working_runtime, tmp_path, 'registration')
