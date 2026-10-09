#!/usr/bin/env python3
"""Stage, validate and promote an isolated Linux CPU runtime installation."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from register_host import register


def install(source, target, browser_config, extension_id, download=True):
    source = Path(source).resolve()
    target = Path(os.path.abspath(target))  # Keep the stable alias on reinstall.
    target.parent.mkdir(parents=True, exist_ok=True)
    if target == Path('/') or target == source or source in target.parents:
        raise ValueError('Install into a separate runtime directory')
    if target.exists() and not target.is_dir():
        raise ValueError('Existing runtime target must be a directory or directory symlink')
    versions = target.parent / f'.{target.name}.versions'
    versions.mkdir(mode=0o700, exist_ok=True)
    environment = dict(os.environ)
    for name in ('PYTHONPATH', 'PYTHONHOME'):
        environment.pop(name, None)
    environment['PYTHONNOUSERSITE'] = '1'

    # Serialize upgrades of this alias; no active files change during validation.
    with open(versions / 'install.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        candidate = Path(tempfile.mkdtemp(prefix='runtime-', dir=versions))
        link = versions / f'{candidate.name}.link'
        legacy = None
        previous_link = os.readlink(target) if target.is_symlink() else None
        promoted = False
        completed = False
        try:
            for directory in ('bin', 'host', 'engines', 'policy', 'models'):
                shutil.copytree(source / directory, candidate / directory)
            for name in ('requirements.txt', 'requirements-models.txt', 'uninstall.sh'):
                shutil.copy2(source / name, candidate / name)
            (candidate / 'bin/youtube-live-translate-host').chmod(0o755)
            (candidate / 'uninstall.sh').chmod(0o755)
            # Copy assets, never hardlink them: a failed validation must not alter
            # the previous generation. Always verify against the new manifest.
            if target.is_dir():
                manifest = json.loads((candidate / 'models/model_manifest.json').read_text())
                for info in manifest['models'].values():
                    old = target / 'models' / info['name']
                    new = candidate / 'models' / info['name']
                    if old.is_dir() and not new.exists():
                        shutil.copytree(old, new)
            subprocess.run([sys.executable, '-I', '-m', 'venv', str(candidate / 'venv')], check=True, env=environment)
            python = str(candidate / 'venv/bin/python')

            def run(*arguments):
                subprocess.run([python, '-I', *arguments], check=True, env=environment, cwd=candidate)

            run('-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(candidate / 'requirements.txt'))
            run('-m', 'pip', 'check')
            manager = str(candidate / 'models/model_manager.py')
            verified = subprocess.run([python, '-I', manager, 'verify'], env=environment,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            if not verified and download:
                run('-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(candidate / 'requirements-models.txt'))
                run(manager, 'download')
            run(manager, 'verify')
            run(manager, 'self-test')
            # The venv stays at its original generation path: moving it would
            # invalidate absolute shebangs. Retain old generations for recovery.
            link.symlink_to(candidate, target_is_directory=True)
            if target.is_dir() and not target.is_symlink():
                legacy = versions / f'{candidate.name}.previous'
                target.rename(legacy)
            os.replace(link, target)
            promoted = True
            try:
                register(target, browser_config, extension_id)
            except BaseException:
                if previous_link is not None:
                    link.symlink_to(previous_link, target_is_directory=True)
                    os.replace(link, target)
                else:
                    target.unlink()
                    if legacy is not None:
                        legacy.rename(target)
                promoted = False
                raise
            completed = True
            print(f'SUCCESS: Verified CPU runtime installed at {target} for extension {extension_id}')
        finally:
            if link.is_symlink():
                link.unlink()
            # Also recover a legacy directory if promotion itself failed.
            if not promoted and legacy is not None and legacy.exists() and not target.exists():
                legacy.rename(target)
            if not completed and not promoted:
                shutil.rmtree(candidate)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--browser-config', required=True)
    parser.add_argument('--extension-id', required=True)
    parser.add_argument('--skip-download', action='store_true')
    args = parser.parse_args()
    try:
        install(args.source, args.target, args.browser_config, args.extension_id, not args.skip_download)
    except Exception as error:
        print(f'FAIL: Installation not completed: {error}', file=sys.stderr)
        sys.exit(1)
