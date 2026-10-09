#!/usr/bin/env python3
"""Provision verified CPU model assets and check their local integrity.

The tracked manifest describes trusted acquisition sources. An installation
receipt locks the resolved source revision and every resulting file digest.
Receipts detect subsequent corruption; they are not publisher signatures.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

MANIFEST_PATH = Path(__file__).resolve().parent / 'model_manifest.json'
RECEIPT_NAME = 'integrity.json'


def compute_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(value):
    # Output digests are checked independently below; the receipt also identifies
    # the acquisition recipe that generated them.
    recipe = {key: item for key, item in value.items() if key != 'files'}
    return hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()


class ModelManager:
    def __init__(self, models_root=None, manifest_path=None):
        self.models_root = Path(models_root) if models_root else MANIFEST_PATH.parent
        with open(manifest_path or MANIFEST_PATH, encoding='utf-8') as handle:
            self.manifest = json.load(handle)
        if self.manifest.get('schema_version') != 1:
            raise ValueError('Unsupported model manifest schema')
        for info in self.manifest['models'].values():
            for name in [info['name'], *info['required_files']]:
                if Path(name).name != name or name in ('', '.', '..'):
                    raise ValueError(f'Unsafe model path: {name!r}')

    def get_model_path(self, model_type):
        return self.models_root / self.manifest['models'][model_type]['name']

    def check_disk_space(self, target_dir=None, required_mb=3000.0):
        target = Path(target_dir or self.models_root)
        target.mkdir(parents=True, exist_ok=True)
        return shutil.disk_usage(target).free >= required_mb * 1024 * 1024

    def verify_model(self, model_type):
        info = self.manifest['models'][model_type]
        root = self.get_model_path(model_type)
        try:
            receipt = json.loads((root / RECEIPT_NAME).read_text())
            if receipt['manifest_sha256'] != fingerprint(info):
                return False, ['Model receipt does not match the acquisition manifest']
            files = receipt['files']
            if info.get('files') is not None and files != info['files']:
                return False, ['Model receipt differs from versioned output checksums']
            if not set(info['required_files']).issubset(files):
                return False, ['Model receipt is missing required file checksums']
            actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*')
                            if p.is_file() and p.name != RECEIPT_NAME}
            if actual_files != set(files):
                return False, ['Model file inventory differs from its receipt']
            errors = []
            for name, spec in files.items():
                path = root / name
                if (Path(name).is_absolute() or '..' in Path(name).parts
                        or path.is_symlink() or not path.is_file()
                        or not path.resolve().is_relative_to(root.resolve())):
                    errors.append(f'Missing or unsafe model file: {name}')
                elif path.stat().st_size != spec['size_bytes'] or compute_sha256(path) != spec['sha256']:
                    errors.append(f'Integrity mismatch: {name}')
            return not errors, errors
        except (OSError, ValueError, KeyError, TypeError) as error:
            return False, [f'Model is not provisioned with a valid integrity receipt: {error}']

    def verify_all(self):
        errors = {}
        for kind in ('asr', 'mt'):
            valid, messages = self.verify_model(kind)
            if not valid:
                errors[kind] = messages
        return not errors, errors

    def _download_archive(self, info, staging):
        source = info['source']
        archive_path = staging.parent / 'source.tar.bz2'
        urllib.request.urlretrieve(source['url'], archive_path)
        if compute_sha256(archive_path) != source['sha256']:
            raise ValueError('ASR archive checksum mismatch; refusing to extract')
        wanted = {f"{info['name']}/{name}": name for name in info['required_files']}
        # Read bzip2 once. Random member lookups repeatedly decompress hundreds
        # of megabytes; only these four verified model files are needed.
        with tarfile.open(archive_path, mode='r|bz2') as archive:
            for member in archive:
                if member.name not in wanted:
                    continue
                name = wanted.pop(member.name)
                if not member.isfile():
                    raise ValueError(f'Expected a regular archive member: {name}')
                with archive.extractfile(member) as incoming, open(staging / name, 'wb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
                if not wanted:
                    break
        if wanted:
            raise ValueError(f'Missing required archive members: {sorted(wanted)}')
        return {'archive_sha256': source['sha256'], 'url': source['url']}

    def _convert_marian(self, info, staging):
        os.environ.setdefault('HF_HOME', str(self.models_root.parent / '.cache' / 'huggingface'))
        # The standard HTTPS downloader works through the cloud egress proxy;
        # its source digests are still checked before conversion.
        os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
        os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT', '20')
        from huggingface_hub import hf_hub_download
        import ctranslate2
        from transformers import MarianTokenizer

        source = info['source']
        revision = source['revision']
        if not re.fullmatch(r'[0-9a-f]{40}', revision):
            raise ValueError('Marian acquisition requires an immutable source commit')
        source_dir = staging.parent / 'source'
        source_dir.mkdir()
        checksums = {}
        for name in info['source_files']:
            expected = source['files'][name]
            cached = Path(hf_hub_download(source['repository'], name, revision=revision,
                                         cache_dir=str(Path(os.environ['HF_HOME']) / 'hub')))
            if cached.stat().st_size != expected['size_bytes']:
                raise ValueError(f'Upstream source size mismatch: {name}')
            if 'sha256' in expected:
                if compute_sha256(cached) != expected['sha256']:
                    raise ValueError(f'Upstream LFS checksum mismatch: {name}')
            else:
                content = cached.read_bytes()
                actual = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
                if actual != expected['git_blob_sha1']:
                    raise ValueError(f'Upstream Git blob checksum mismatch: {name}')
            shutil.copyfile(cached, source_dir / name)
            checksums[name] = compute_sha256(cached)
        tokenizer = MarianTokenizer.from_pretrained(str(source_dir), local_files_only=True)
        converter = ctranslate2.converters.TransformersConverter(str(source_dir))
        converter.convert(str(staging), quantization=source['quantization'], force=True)
        tokenizer.save_pretrained(str(staging))
        return {'repository': source['repository'], 'revision': revision,
                'source_sha256': checksums, 'ctranslate2_version': ctranslate2.__version__}

    def download_model(self, model_type):
        valid, _ = self.verify_model(model_type)
        if valid:
            return
        target = self.get_model_path(model_type)
        if target.exists():
            raise ValueError(f'Refusing to overwrite unverified assets: {target}. Move them aside and retry.')
        if not self.check_disk_space():
            raise OSError('At least 3 GB free disk space is required for model provisioning')
        info = self.manifest['models'][model_type]
        with tempfile.TemporaryDirectory(prefix='.provision-', dir=self.models_root) as temporary:
            staging = Path(temporary) / 'model'
            staging.mkdir()
            if info['source']['type'] == 'archive':
                provenance = self._download_archive(info, staging)
            elif info['source']['type'] == 'huggingface_conversion':
                provenance = self._convert_marian(info, staging)
            else:
                raise ValueError('Unsupported acquisition source')
            missing = [name for name in info['required_files'] if not (staging / name).is_file()]
            if missing:
                raise ValueError(f'Model acquisition did not produce required files: {missing}')
            files = {p.relative_to(staging).as_posix(): {'size_bytes': p.stat().st_size, 'sha256': compute_sha256(p)}
                     for p in staging.rglob('*') if p.is_file()}
            if info.get('files') is not None and files != info['files']:
                raise ValueError('Acquired model files differ from versioned output checksums')
            (staging / RECEIPT_NAME).write_text(json.dumps({
                'manifest_sha256': fingerprint(info), 'source': provenance, 'files': files
            }, indent=2) + '\n')
            staging.rename(target)
        valid, errors = self.verify_model(model_type)
        if not valid:
            raise ValueError(f'Post-acquisition verification failed: {errors}')

    def self_test(self):
        valid, errors = self.verify_all()
        if not valid:
            raise ValueError(f'Model verification failed: {errors}')
        sys.path.insert(0, str(MANIFEST_PATH.parent.parent))
        from engines.asr_engine import SherpaOnnxStreamingEngine
        from engines.mt_engine import MarianCTranslate2Engine
        import numpy as np
        asr = SherpaOnnxStreamingEngine(str(self.get_model_path('asr')))
        asr.initialize()
        asr.start_stream()
        asr.push_audio(np.zeros(16000, dtype=np.int16))
        asr.finalize_segment()
        asr.stop_stream()
        mt = MarianCTranslate2Engine(str(self.get_model_path('mt')))
        mt.initialize()
        result = mt.translate('こんにちは。')
        if not result.target_text.strip():
            raise ValueError('Marian inference returned an empty translation')
        print('PASS: CPU ASR and Japanese → English MT inference self-test')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'download', 'info', 'check-disk', 'self-test'])
    parser.add_argument('--models-dir')
    parser.add_argument('--model', choices=['asr', 'mt', 'all'], default='all')
    args = parser.parse_args()
    try:
        manager = ModelManager(args.models_dir)
        if args.action == 'download':
            for kind in (('asr', 'mt') if args.model == 'all' else (args.model,)):
                manager.download_model(kind)
            print('PASS: Requested models provisioned and verified')
        elif args.action == 'verify':
            valid, errors = manager.verify_all()
            if not valid:
                raise ValueError(json.dumps(errors, indent=2))
            print('PASS: All required model files match their integrity receipts')
        elif args.action == 'self-test':
            manager.self_test()
        elif args.action == 'info':
            print(json.dumps(manager.manifest, indent=2))
        elif not manager.check_disk_space():
            raise OSError('Insufficient disk space')
    except Exception as error:
        message = re.sub(r'(https?://[^\s?\)]+)\?[^\s\)]+', r'\1?[redacted]', str(error))
        print(f'FAIL: {message}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
