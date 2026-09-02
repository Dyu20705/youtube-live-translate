#!/usr/bin/env python3
"""
model_manager.py - Manages on-device model discovery, SHA256 integrity verification,
disk space checking, and model diagnostics for YouTube Live Translate.
"""

import os
import sys
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional

MANIFEST_PATH = Path(__file__).resolve().parent / "model_manifest.json"


def compute_sha256(file_path: Path) -> str:
    """Computes SHA256 hex digest of a file in 1MB chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


class ModelManager:
    def __init__(self, models_root: Optional[Path] = None):
        self.models_root = Path(models_root) if models_root else Path(__file__).resolve().parent
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)

        # Workspace fallback for development environment
        self.workspace_root = Path(__file__).resolve().parent.parent.parent.parent

    def get_model_path(self, model_type: str) -> Path:
        """Returns the directory path for a model type ('asr' or 'mt')."""
        model_info = self.manifest["models"].get(model_type)
        if not model_info:
            raise ValueError(f"Unknown model type: {model_type}")

        model_name = model_info["name"]
        
        # 1. Check direct subdirectory under models_root
        candidate = self.models_root / model_name
        if candidate.exists() and candidate.is_dir():
            return candidate

        # 2. Check type subdirectory (e.g. models/asr/...)
        candidate = self.models_root / model_type / model_name
        if candidate.exists() and candidate.is_dir():
            return candidate

        # 3. Check installed ~/.local/share/youtube-live-translate/models/...
        local_share = Path.home() / ".local" / "share" / "youtube-live-translate" / "models" / model_name
        if local_share.exists() and local_share.is_dir():
            return local_share

        # 4. Check workspace POC directories (Development fallback)
        if model_type == "asr":
            ws_cand = self.workspace_root / "poc" / "s2-streaming-asr" / "models" / model_name
            if ws_cand.exists() and ws_cand.is_dir():
                return ws_cand
        elif model_type == "mt":
            ws_cand = self.workspace_root / "poc" / "s3-local-mt" / "models" / model_name
            if ws_cand.exists() and ws_cand.is_dir():
                return ws_cand

        return self.models_root / model_name

    def check_disk_space(self, target_dir: Optional[Path] = None, required_mb: float = 500.0) -> bool:
        """Verifies sufficient disk space exists in target directory."""
        target = target_dir or self.models_root
        target.mkdir(parents=True, exist_ok=True)
        total, used, free = shutil.disk_usage(str(target))
        free_mb = free / (1024 * 1024)
        return free_mb >= required_mb

    def verify_model(self, model_type: str) -> Tuple[bool, List[str]]:
        """
        Verifies all files for a model against the manifest (existence, size, SHA256).
        Returns (is_valid, list_of_errors).
        """
        model_info = self.manifest["models"].get(model_type)
        if not model_info:
            return False, [f"Unknown model type: {model_type}"]

        model_dir = self.get_model_path(model_type)
        if not model_dir.exists() or not model_dir.is_dir():
            return False, [f"Model directory missing: {model_dir}"]

        errors = []
        for filename, spec in model_info["files"].items():
            file_path = model_dir / filename
            if not file_path.exists():
                errors.append(f"Missing file: {filename}")
                continue

            actual_size = file_path.stat().st_size
            expected_size = spec["size_bytes"]
            if actual_size != expected_size:
                errors.append(f"Size mismatch on {filename}: expected {expected_size}, got {actual_size}")
                continue

            actual_sha = compute_sha256(file_path)
            expected_sha = spec["sha256"]
            if actual_sha != expected_sha:
                errors.append(f"Corrupt file {filename}: checksum mismatch (expected {expected_sha[:8]}..., got {actual_sha[:8]}...)")

        return len(errors) == 0, errors

    def verify_all(self) -> Tuple[bool, Dict[str, List[str]]]:
        """Verifies both ASR and MT models."""
        all_errors = {}
        all_valid = True
        for m_type in ["asr", "mt"]:
            is_valid, errors = self.verify_model(m_type)
            if not is_valid:
                all_valid = False
                all_errors[m_type] = errors
        return all_valid, all_errors


def main():
    import argparse
    parser = argparse.ArgumentParser(description="YouTube Live Translate Model Manager")
    parser.add_argument("action", choices=["verify", "info", "check-disk"], help="Action to perform")
    parser.add_argument("--models-dir", type=str, default=None, help="Custom models root directory")
    args = parser.parse_args()

    models_dir = Path(args.models_dir) if args.models_dir else None
    mgr = ModelManager(models_dir)

    if args.action == "verify":
        print(f"Verifying models for YouTube Live Translate...")
        valid, errors = mgr.verify_all()
        if valid:
            print(f"PASS: All required ASR and MT models are installed and integrity verified (100% valid).")
            print(f"  ASR: {mgr.get_model_path('asr')}")
            print(f"  MT:  {mgr.get_model_path('mt')}")
            sys.exit(0)
        else:
            print("FAIL: Model verification failed:")
            for m_type, errs in errors.items():
                print(f"  [{m_type.upper()} Errors]:")
                for e in errs:
                    print(f"    - {e}")
            sys.exit(1)

    elif args.action == "info":
        print(json.dumps(mgr.manifest, indent=2))

    elif args.action == "check-disk":
        has_space = mgr.check_disk_space(mgr.models_root)
        print(f"Disk space check: {'PASS' if has_space else 'INSUFFICIENT SPACE'}")
        sys.exit(0 if has_space else 1)


if __name__ == "__main__":
    main()
