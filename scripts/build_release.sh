#!/usr/bin/env bash
# build_release.sh - Deterministic Build & Packaging Script for YouTube Live Translate v1.0.0

set -e

echo "======================================================================"
echo "  Building YouTube Live Translate v1.0.0 Release Packages"
echo "======================================================================"

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$WORKSPACE_DIR/dist"
VERSION="1.0.0"

# Clean dist directory
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR/extension" "$DIST_DIR/runtime"

# 1. Package Chrome Extension
echo "[1/4] Packaging Chrome Extension..."
EXT_SRC="$WORKSPACE_DIR/src/extension"
EXT_DIST_UNPACKED="$DIST_DIR/extension/youtube-live-translate"
EXT_ZIP="$DIST_DIR/extension/youtube-live-translate-v${VERSION}.zip"

mkdir -p "$EXT_DIST_UNPACKED"
cp -r "$EXT_SRC"/* "$EXT_DIST_UNPACKED/"

# Ensure no junk files in extension
find "$EXT_DIST_UNPACKED" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$EXT_DIST_UNPACKED" -name "*.pyc" -delete 2>/dev/null || true
find "$EXT_DIST_UNPACKED" -name ".DS_Store" -delete 2>/dev/null || true

# Create Zip
(cd "$DIST_DIR/extension" && zip -r -q "youtube-live-translate-v${VERSION}.zip" "youtube-live-translate")
echo "  Created: $EXT_ZIP ($(du -h "$EXT_ZIP" | cut -f1))"

# 2. Package Linux Native Runtime
echo "[2/4] Packaging Linux Native Runtime..."
RUNTIME_SRC="$WORKSPACE_DIR/src/runtime"
RUNTIME_DIST_UNPACKED="$DIST_DIR/runtime/youtube-live-translate-runtime-linux-x86_64-v${VERSION}"
RUNTIME_TAR="$DIST_DIR/runtime/youtube-live-translate-runtime-linux-x86_64-v${VERSION}.tar.gz"

mkdir -p "$RUNTIME_DIST_UNPACKED"
cp -r "$RUNTIME_SRC"/* "$RUNTIME_DIST_UNPACKED/"

# Copy docs to runtime distribution
mkdir -p "$RUNTIME_DIST_UNPACKED/docs"
cp "$WORKSPACE_DIR/docs/user/"*.md "$RUNTIME_DIST_UNPACKED/docs/"
cp "$WORKSPACE_DIR/VERSION" "$RUNTIME_DIST_UNPACKED/"
cp "$WORKSPACE_DIR/CHANGELOG.md" "$RUNTIME_DIST_UNPACKED/"

# Ensure executable permissions
chmod +x "$RUNTIME_DIST_UNPACKED/bin/youtube-live-translate-host"
chmod +x "$RUNTIME_DIST_UNPACKED/host/native_messaging_host.py"
chmod +x "$RUNTIME_DIST_UNPACKED/install.sh"
chmod +x "$RUNTIME_DIST_UNPACKED/uninstall.sh"

# Ensure no pycache or development files
find "$RUNTIME_DIST_UNPACKED" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$RUNTIME_DIST_UNPACKED" -name "*.pyc" -delete 2>/dev/null || true
find "$RUNTIME_DIST_UNPACKED" -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
find "$RUNTIME_DIST_UNPACKED" -name "*.wav" -delete 2>/dev/null || true

# Create Tarball
(cd "$DIST_DIR/runtime" && tar -czf "youtube-live-translate-runtime-linux-x86_64-v${VERSION}.tar.gz" "youtube-live-translate-runtime-linux-x86_64-v${VERSION}")
echo "  Created: $RUNTIME_TAR ($(du -h "$RUNTIME_TAR" | cut -f1))"

# 3. Generate SHA256 Checksums and Release Manifest
echo "[3/4] Generating SHA256 Checksums and Release Manifest..."
python3 - << PY_EOF
import hashlib
import json
import time
from pathlib import Path

dist_dir = Path("$DIST_DIR")
ext_zip = dist_dir / "extension" / "youtube-live-translate-v${VERSION}.zip"
runtime_tar = dist_dir / "runtime" / "youtube-live-translate-runtime-linux-x86_64-v${VERSION}.tar.gz"

def get_hash(p: Path):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest(), p.stat().st_size

ext_hash, ext_size = get_hash(ext_zip)
rt_hash, rt_size = get_hash(runtime_tar)

manifest = {
    "product_name": "YouTube Live Translate",
    "version": "$VERSION",
    "build_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "target_platform": "linux-x86_64",
    "artifacts": {
        "extension_zip": {
            "file": ext_zip.name,
            "path": str(ext_zip.relative_to(dist_dir)),
            "size_bytes": ext_size,
            "sha256": ext_hash
        },
        "runtime_tarball": {
            "file": runtime_tar.name,
            "path": str(runtime_tar.relative_to(dist_dir)),
            "size_bytes": rt_size,
            "sha256": rt_hash
        }
    }
}

manifest_path = dist_dir / "release_manifest.json"
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print("  Release Manifest written to:", manifest_path)
print(f"  Extension SHA256: {ext_hash}")
print(f"  Runtime   SHA256: {rt_hash}")
PY_EOF

# 4. Final summary
echo "[4/4] Release packaging complete!"
echo "======================================================================"
echo "  Release Artifacts Summary:"
echo "  1. Extension: $EXT_ZIP"
echo "  2. Runtime:   $RUNTIME_TAR"
echo "  3. Manifest:  $DIST_DIR/release_manifest.json"
echo "======================================================================"
