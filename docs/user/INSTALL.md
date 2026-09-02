# Installation Guide — YouTube Live Translate

This guide walks you through installing the **YouTube Live Translate** Chrome Extension and Local Native Runtime on Linux.

---

## System Requirements

- **Operating System:** Linux x86_64 (Ubuntu 22.04+, Debian 12+, Fedora 38+, Arch Linux, etc.)
- **Browser:** Google Chrome (version 116+ recommended for Manifest V3 Offscreen API) or Chromium
- **Hardware:** Modern multi-core CPU (Intel Core i5/i7/i9 8th Gen+ or AMD Ryzen 3000+ recommended), at least 4 GB RAM available
- **Disk Space:** ~500 MB for models and runtime assets

---

## Step 1: Install the Local Native Runtime

1. Download the runtime archive: `youtube-live-translate-runtime-linux-x86_64-v1.0.0.tar.gz` (or use the packaged runtime folder in `dist/runtime/linux`).
2. Extract the archive into your preferred directory:
   ```bash
   tar -xzf youtube-live-translate-runtime-linux-x86_64-v1.0.0.tar.gz
   cd youtube-live-translate-runtime-linux-x86_64-v1.0.0
   ```
3. Run the automated installer:
   ```bash
   ./install.sh
   ```
   The installer will:
   - Verify Python environment and dependencies.
   - Verify or download the required local AI models (Sherpa-ONNX Japanese Zipformer ASR and Marian MT INT8).
   - Verify model SHA256 checksums.
   - Register the Native Messaging host manifest in Google Chrome / Chromium configuration directories (`~/.config/google-chrome/NativeMessagingHosts/`).
   - Run a self-test diagnostic check.

---

## Step 2: Install the Chrome Extension

1. Open **Google Chrome**.
2. Navigate to `chrome://extensions/` in your address bar.
3. Enable **Developer mode** using the toggle in the top-right corner.
4. Click **Load unpacked**.
5. Select the `dist/extension/youtube-live-translate` folder (or `src/extension` in the development release).
6. The **YouTube Live Translate** extension icon will appear in your Chrome toolbar.
7. (Recommended) Click the puzzle piece icon in Chrome toolbar and pin **YouTube Live Translate** for quick access.

---

## Step 3: Verify Installation

1. Click the **YouTube Live Translate** icon in your toolbar.
2. In the popup, verify that **Runtime Status** displays **Ready** (Local Runtime connected).
3. If the status shows *Not Installed* or *Disconnected*, consult [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Uninstallation

To remove the native runtime and registration:
```bash
cd youtube-live-translate-runtime-linux-x86_64-v1.0.0
./uninstall.sh
```
To remove the extension, go to `chrome://extensions/` and click **Remove** on YouTube Live Translate.
