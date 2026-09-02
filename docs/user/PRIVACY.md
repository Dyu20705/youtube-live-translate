# Privacy Guarantee & Local AI Statement

YouTube Live Translate is designed from the ground up as a **100% local-first** application.

---

## Core Privacy Principles

1. **Zero Audio Uploads:**
   All tab audio captured from YouTube is processed strictly on your local machine CPU. No audio data, PCM frames, or speech recordings are ever transmitted across the internet.

2. **Zero Cloud Translation APIs:**
   Both Automatic Speech Recognition (ASR via Sherpa-ONNX Zipformer) and Machine Translation (MT via Helsinki-NLP Marian CTranslate2) run entirely offline inside the local native runtime process.

3. **Zero Telemetry or Tracking:**
   The extension contains no third-party tracking scripts, analytics SDKs, advertising beacons, or telemetry collectors.

4. **Local Settings Only:**
   User preferences (font size, subtitle position, display opacity) are stored locally in your browser's private `chrome.storage.local` area.

---

## Local Data Storage Summary

| Data Category | Stored Location | Purpose | Retention |
| :--- | :--- | :--- | :--- |
| **Audio Stream** | RAM (Circular buffer) | Real-time speech inference | Immediately discarded after processing |
| **Model Weights** | Local disk (`~/.local/share/youtube-live-translate/models/`) | Neural network weights | Stored until uninstalled |
| **User Settings** | `chrome.storage.local` | UI display preferences | Until extension removed or reset |
| **Logs** | Terminal / stderr | Diagnostic debugging only | Ephemeral process session |
