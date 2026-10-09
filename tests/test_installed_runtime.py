"""Real installed launcher protocol and speech inference, without PoC imports."""
import base64
import json
import os
from pathlib import Path
import queue
import struct
import subprocess
import threading
import time
from math import gcd

import numpy as np
import pytest
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]


def exercise_installed_host(runtime, environment=None):
    runtime = Path(runtime).resolve()
    launcher = runtime / 'bin/youtube-live-translate-host'
    assert launcher.is_file()
    # The launcher itself must isolate Python; callers deliberately keep hostile PYTHONPATH.
    environment = dict(os.environ) if environment is None else environment
    process = subprocess.Popen([str(launcher)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=environment, cwd=runtime)
    messages = queue.Queue()
    diagnostics = []

    def receive():
        try:
            while True:
                header = process.stdout.read(4)
                if not header:
                    return
                assert len(header) == 4
                length = struct.unpack('@I', header)[0]
                assert 0 < length <= 1024 * 1024
                messages.put(json.loads(process.stdout.read(length)))
        except BaseException as error:
            messages.put(error)

    receiver = threading.Thread(target=receive, daemon=True)
    receiver.start()
    stderr_reader = threading.Thread(target=lambda: diagnostics.append(process.stderr.read().decode()), daemon=True)
    stderr_reader.start()

    def send(message):
        encoded = json.dumps(message).encode()
        process.stdin.write(struct.pack('@I', len(encoded)) + encoded)
        process.stdin.flush()

    def until(predicate, timeout=60):
        deadline = time.monotonic() + timeout
        seen = []
        while time.monotonic() < deadline:
            message = messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if isinstance(message, BaseException):
                raise message
            assert message.get('type') != 'error', message
            seen.append(message)
            if predicate(message):
                return message, seen
        raise AssertionError(f'Expected response not received: {seen}')

    try:
        until(lambda message: message.get('state') == 'RUNNING')
        audio, rate = sf.read(ROOT / 'poc/s2-streaming-asr/datasets/ja_conversational.wav', dtype='float32')
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if rate != 16000:
            divisor = gcd(rate, 16000)
            audio = resample_poly(audio, 16000 // divisor, rate // divisor)
        pcm = (np.clip(audio, -1, 1) * 32767).astype('<i2')
        for start in range(0, len(pcm), 2048):
            send({'type': 'audio_chunk', 'data': base64.b64encode(pcm[start:start+2048].tobytes()).decode()})
        send({'type': 'control.flush'})
        final, seen = until(lambda message: message.get('type') == 'subtitle.final')
        assert final.get('committed_text', '').strip(), final
        assert any(message.get('type') == 'subtitle.update' for message in seen)
        send({'type': 'control.ping'})
        until(lambda message: message.get('state') == 'HEALTHY')
        send({'type': 'control.stop'})
        until(lambda message: message.get('state') == 'STOPPED')
        process.stdin.close()
        assert process.wait(timeout=10) == 0
        receiver.join(timeout=2)
        print('Installed speech translation:', final['committed_text'])
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        receiver.join(timeout=2)
        stderr_reader.join(timeout=2)


def test_installed_native_host_speech_and_lifecycle():
    configured = os.environ.get('YLT_TEST_RUNTIME')
    if not configured:
        pytest.fail('YLT_TEST_RUNTIME is required for production acceptance')
    exercise_installed_host(configured)


def test_installed_launcher_rejects_module_shadowing(tmp_path):
    configured = os.environ.get('YLT_TEST_RUNTIME')
    if not configured:
        pytest.fail('YLT_TEST_RUNTIME is required for production acceptance')
    # Would execute before installed site-packages with the old launcher.
    marker = tmp_path / 'shadow-imported'
    poison = f"from pathlib import Path\nPath({str(marker)!r}).write_text('unsafe')\nraise RuntimeError('inherited module shadowed runtime')\n"
    for name in ('numpy', 'sherpa_onnx', 'ctranslate2', 'transformers'):
        (tmp_path / f'{name}.py').write_text(poison)
    environment = dict(os.environ, PYTHONPATH=str(tmp_path))
    exercise_installed_host(configured, environment)
    assert not marker.exists()
