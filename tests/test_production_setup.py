"""Production acquisition, packaging and installer failure contracts."""
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('production_models', ROOT / 'src/runtime/models/model_manager.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def acquisition(tmp_path, monkeypatch):
    archive = tmp_path / 'source.tar.bz2'
    with tarfile.open(archive, 'w:bz2') as handle:
        member = tarfile.TarInfo('test-model/model.bin')
        data = b'verified official model fixture'
        member.size = len(data)
        handle.addfile(member, io.BytesIO(data))
    info = {'name': 'test-model', 'source': {'type': 'archive', 'url': 'https://example.invalid/model',
            'sha256': module.compute_sha256(archive)}, 'required_files': ['model.bin']}
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'models': {'asr': info}}))
    def fetch(url, destination):
        Path(destination).write_bytes(archive.read_bytes())
    monkeypatch.setattr(module.urllib.request, 'urlretrieve', fetch)
    return module.ModelManager(tmp_path / 'installed', manifest), info, manifest, archive


def test_verified_acquisition_and_corruption_detection(acquisition):
    manager, _, _, _ = acquisition
    manager.download_model('asr')
    assert manager.verify_model('asr') == (True, [])
    # A valid installation reuses assets without reacquiring them.
    original = (manager.get_model_path('asr') / 'integrity.json').read_bytes()
    manager.download_model('asr')
    assert (manager.get_model_path('asr') / 'integrity.json').read_bytes() == original
    (manager.get_model_path('asr') / 'model.bin').write_bytes(b'corrupt')
    assert not manager.verify_model('asr')[0]
    with pytest.raises(ValueError, match='overwrite unverified'):
        manager.download_model('asr')


def test_bad_archive_digest_never_installs(acquisition):
    manager, _, _, archive = acquisition
    archive.write_bytes(b'bad download')
    with pytest.raises(ValueError, match='checksum mismatch'):
        manager.download_model('asr')
    assert not manager.get_model_path('asr').exists()


def test_manifest_change_invalidates_receipt(acquisition):
    manager, info, _, _ = acquisition
    manager.download_model('asr')
    info['source']['url'] = 'https://example.invalid/other'
    manager.manifest['models']['asr'] = info
    assert not manager.verify_model('asr')[0]


def test_missing_receipt_and_added_file_rejected(acquisition):
    manager, _, _, _ = acquisition
    assert not manager.verify_model('asr')[0]
    manager.download_model('asr')
    (manager.get_model_path('asr') / 'unexpected.bin').write_bytes(b'extra')
    assert not manager.verify_model('asr')[0]


@pytest.mark.parametrize('arguments', [[], ['--extension-id', 'youtube-live-translate-v1'],
                                      ['--extension-id', 'z' * 32], ['--extension-id'], ['--unknown']])
def test_invalid_installer_arguments_have_no_side_effects(tmp_path, arguments):
    target = tmp_path / 'runtime'
    browser = tmp_path / 'browser'
    result = subprocess.run(['bash', str(ROOT / 'src/runtime/install.sh'), *arguments,
                             '--target-dir', str(target), '--browser-config-dir', str(browser)],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert not target.exists()
    assert not browser.exists()
    assert 'SUCCESS' not in result.stdout


def test_production_manifest_is_versioned_and_packaged():
    path = 'src/runtime/models/model_manifest.json'
    assert subprocess.run(['git', 'check-ignore', '--no-index', path], cwd=ROOT, capture_output=True).returncode == 1
    manifest = json.loads((ROOT / path).read_text())
    assert len(manifest['models']['asr']['source']['sha256']) == 64
    release = json.loads((Path(os.environ.get('YLT_DIST_DIR', ROOT / 'dist')) / 'release_manifest.json').read_text())
    for artifact in release['artifacts'].values():
        content = (Path(os.environ.get('YLT_DIST_DIR', ROOT / 'dist')) / artifact['path']).read_bytes()
        assert hashlib.sha256(content).hexdigest() == artifact['sha256']
    with tarfile.open(Path(os.environ.get('YLT_DIST_DIR', ROOT / 'dist')) / release['artifacts']['runtime_tarball']['path']) as archive:
        names = archive.getnames()
        for suffix in ['/models/model_manifest.json', '/requirements.txt', '/requirements-models.txt']:
            assert any(name.endswith(suffix) for name in names)
        assert not any('/.venv/' in name or '/venv/' in name for name in names)


def test_registration_exact_origin_and_safe_uninstall(tmp_path):
    spec = importlib.util.spec_from_file_location('registration', ROOT / 'src/runtime/host/register_host.py')
    registration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registration)
    runtime = tmp_path / "runtime"
    launcher = runtime / "bin/youtube-live-translate-host"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/sh\nexit 0\n")
    launcher.chmod(0o755)
    extension_id = "abcdefghijklmnop" * 2
    paths = registration.register(runtime, tmp_path / "browser", extension_id)
    for path in paths:
        assert json.loads(path.read_text())["allowed_origins"] == [f"chrome-extension://{extension_id}/"]
    # Repeated installation is idempotent for this runtime.
    assert registration.register(runtime, tmp_path / "browser", extension_id) == paths
    # Never clobber someone else's registration.
    replacement = json.loads(paths[0].read_text())
    replacement["path"] = "/other/runtime/host"
    paths[0].write_text(json.dumps(replacement))
    with pytest.raises(ValueError, match="different registered"):
        registration.register(runtime, tmp_path / "browser", extension_id)
    import shutil
    shutil.copyfile(ROOT / "src/runtime/uninstall.sh", runtime / "uninstall.sh")
    subprocess.run(["bash", str(runtime / "uninstall.sh")], check=True)
    assert paths[0].exists()
    assert not paths[1].exists()


@pytest.mark.parametrize('algorithm', ['sha256', 'git_blob_sha1'])
def test_marian_source_hash_is_checked_before_conversion(tmp_path, monkeypatch, algorithm):
    import huggingface_hub
    corrupted = tmp_path / 'config.json'
    corrupted.write_bytes(b'changed source')
    monkeypatch.setattr(huggingface_hub, 'hf_hub_download', lambda *args, **kwargs: str(corrupted))
    manager = module.ModelManager(tmp_path / 'models')
    info = {'source': {'repository': 'Helsinki-NLP/opus-mt-ja-en', 'revision': 'a' * 40,
                      'quantization': 'int8', 'files': {'config.json': {
                          'size_bytes': corrupted.stat().st_size, algorithm: '0' * (64 if algorithm == 'sha256' else 40)}}},
            'source_files': ['config.json']}
    staging = tmp_path / 'conversion' / 'model'
    staging.mkdir(parents=True)
    with pytest.raises(ValueError, match='checksum mismatch'):
        manager._convert_marian(info, staging)
    assert not (staging / 'model.bin').exists()
