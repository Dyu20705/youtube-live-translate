"""
test_packaging_contract.py - Tier B: Static packaging, manifest validity, and host discovery tests.
"""

import os
import json
import stat
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent
S5_DIR = WORKSPACE_DIR / "poc" / "s5-extension-ui"


def test_extension_manifest_contract():
    manifest_path = S5_DIR / "manifest.json"
    assert manifest_path.exists(), "manifest.json does not exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Manifest V3 validation
    assert manifest.get("manifest_version") == 3, "Must be Manifest V3"
    assert manifest.get("name") == "YouTube Live Translate S5"
    assert manifest.get("version") == "1.0.0"

    # 2. Service Worker validation
    background = manifest.get("background", {})
    sw_path = S5_DIR / background.get("service_worker", "")
    assert sw_path.exists(), f"Service worker not found at {sw_path}"
    assert background.get("type") == "module", "Service worker should be ES module"

    # 3. Content Scripts validation
    content_scripts = manifest.get("content_scripts", [])
    assert len(content_scripts) > 0, "Content scripts must be declared"
    for cs in content_scripts:
        for js_file in cs.get("js", []):
            assert (S5_DIR / js_file).exists(), f"Content script {js_file} does not exist"
        for css_file in cs.get("css", []):
            assert (S5_DIR / css_file).exists(), f"CSS file {css_file} does not exist"

    # 4. Offscreen and Core files validation
    assert (S5_DIR / "offscreen.html").exists(), "offscreen.html does not exist"
    assert (S5_DIR / "offscreen.js").exists(), "offscreen.js does not exist"
    assert (S5_DIR / "audio-processor.js").exists(), "audio-processor.js does not exist"

    # 5. Permissions validation (Minimum required)
    permissions = manifest.get("permissions", [])
    for req in ["tabCapture", "offscreen", "activeTab", "nativeMessaging"]:
        assert req in permissions, f"Missing required permission: {req}"

    # 6. Host permissions validation
    host_perms = manifest.get("host_permissions", [])
    assert any("youtube.com" in hp for hp in host_perms), "Host permissions must cover YouTube"


def test_native_messaging_host_manifest_contract():
    manifest_path = S5_DIR / "bridge" / "manifest_host.json"
    assert manifest_path.exists(), "manifest_host.json does not exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        host_manifest = json.load(f)

    assert host_manifest.get("name") == "com.duy.youtube_live_translate"
    assert host_manifest.get("type") == "stdio"

    exe_path = Path(host_manifest.get("path", ""))
    assert exe_path.exists(), f"Host binary not found at {exe_path}"
    assert exe_path.is_absolute(), "Host binary path must be absolute"

    # Check executable permission
    st = os.stat(exe_path)
    assert bool(st.st_mode & stat.S_IXUSR), f"Host binary {exe_path} is not executable (chmod +x required)"

    # Check allowed_origins
    allowed = host_manifest.get("allowed_origins", [])
    assert len(allowed) > 0, "allowed_origins must be defined"


def test_chrome_host_registration_discovery():
    chrome_host_dir = Path.home() / ".config" / "google-chrome" / "NativeMessagingHosts"
    target_manifest = chrome_host_dir / "com.duy.youtube_live_translate.json"

    assert target_manifest.exists(), f"Native host manifest not found in Chrome directory: {target_manifest}"

    with open(target_manifest, "r", encoding="utf-8") as f:
        registered = json.load(f)

    assert registered.get("name") == "com.duy.youtube_live_translate"
    assert Path(registered.get("path", "")).exists(), "Registered host binary path does not exist"
