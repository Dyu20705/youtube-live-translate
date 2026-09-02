# Troubleshooting & Recovery Guide

Common issues and their resolutions for YouTube Live Translate.

---

## 1. "Local translation runtime is not installed or unreachable"

### Cause
Chrome Native Messaging cannot locate or execute the registered host binary.

### Fix
1. Ensure you ran `./install.sh` from the runtime directory.
2. Check that the manifest file exists:
   ```bash
   cat ~/.config/google-chrome/NativeMessagingHosts/com.duy.youtube_live_translate.json
   ```
3. Ensure the path inside the JSON points to the executable launcher `bin/youtube-live-translate-host` and has execute permissions (`chmod +x`).
4. Run the launcher directly from the terminal to test:
   ```bash
   echo '{"type":"control.ping"}' | /path/to/bin/youtube-live-translate-host
   ```
   If Python errors appear, check missing Python packages or run `./install.sh` again.

---

## 2. "Translation model is not installed or corrupt"

### Cause
The local model weights (Sherpa-ONNX ASR or Marian MT) are missing or incomplete.

### Fix
1. Run the model verification tool:
   ```bash
   python3 src/runtime/models/model_manager.py verify
   ```
2. If files are missing or checksums fail, download/repair them:
   ```bash
   python3 src/runtime/models/model_manager.py download
   ```

---

## 3. "Chrome did not allow tab audio capture"

### Cause
Audio capture permission was denied or interrupted.

### Fix
1. Click anywhere on the YouTube page to ensure the tab is active.
2. Open the extension popup and click **Start Live Translation**.
3. If an active capture was already running in another tab, stop it first.

---

## 4. No Subtitles Appearing on Video

### Checklist
- Is the video playing and unmuted?
- Is spoken Japanese present in the audio?
- Is the video an advertisement? (Subtitles automatically pause during ads).
- Did you refresh the page? Click **Start Live Translation** after page reloads.

---

## 5. Subtitle Positioning & Customization

You can adjust subtitle appearance directly in the Extension Popup under **Settings**:
- **Font Size:** Choose between Small (18px), Medium (22px), Large (26px), or Extra Large (32px).
- **Bottom Offset:** Adjust vertical distance from the video player controls.
- **Provisional Opacity:** Adjust how bright or dim unfinalized words appear.
