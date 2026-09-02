# Chrome Web Store Listing & Metadata

> **Extension Name:** YouTube Live Translate
> **Short Name:** Live Translate
> **Version:** 1.0.0
> **Category:** Accessibility / Productivity
> **Language:** English (United States)
> **Last Updated:** 2026-09-02

---

## 1. Store Listing Copy

### 1.1 Summary / Short Description (Max 132 characters)
Local real-time Japanese speech translation to English subtitles for YouTube videos and live streams using on-device AI.

### 1.2 Detailed Description
YouTube Live Translate delivers real-time Japanese speech-to-English subtitle translation directly inside the YouTube video player.

Powered entirely by local on-device AI inference (Sherpa-ONNX streaming Zipformer ASR and Helsinki-NLP Marian MT running on your CPU), this extension provides private, low-latency live subtitles with zero cloud translation fees, zero mandatory subscription accounts, and zero audio data sent to remote servers.

#### Key Features:
- **Real-Time Live Translation:** Translates live Japanese audio into natural, accurate English as speech is being delivered.
- **Anchored Stable Presentation:** Dual-layer subtitle rendering guarantees that already-translated committed words remain spatially fixed on screen ($0\text{px}$ anchor displacement), eliminating visual flicker while displaying provisional words in real-time.
- **100% On-Device & Private:** Audio capture, speech recognition, and translation all execute strictly on your local CPU. No voice recordings or text ever leave your computer.
- **YouTube Optimized:** Seamlessly integrates with standard YouTube videos, live streams, theater mode, and full-screen playback. Subtitles automatically pause during ads and reset across video navigation.
- **Customizable Appearance:** Easily adjust subtitle font size, vertical screen offset, and provisional text opacity to match your viewing preferences.

#### Requirements:
- Google Chrome on Linux x86_64.
- Installed companion local AI runtime (available via the open-source installer).

---

## 2. Permissions Justifications

| Permission | Purpose & Technical Justification |
| :--- | :--- |
| `tabCapture` | Required to capture the audio output stream from the active YouTube video tab and route it to the local ASR engine for speech recognition. |
| `offscreen` | Required to process captured tab audio in an offscreen document context, downsampling 48kHz stereo stream to 16kHz mono linear PCM before local inference. |
| `storage` | Required to persist user subtitle preferences (font size, position offset, provisional opacity) across browser sessions using `chrome.storage.local`. |
| `nativeMessaging` | Required to communicate bidirectionally with the local Python/C++ inference runtime host on `127.0.0.1` via standard input/output. |
| `activeTab` | Required to detect the active YouTube tab, verify player readiness, and mount the subtitle overlay when the user initiates translation. |
| Host Permissions (`*://*.youtube.com/*`, `*://youtube.com/*`) | Required to inject the subtitle overlay and content script into YouTube watch and live stream pages. |

---

## 3. Privacy & Data Use Disclosure

- **Single Purpose:** Translating spoken audio from YouTube videos into on-screen English subtitles.
- **Audio Data Handling:** Tab audio is captured ephemerally in RAM, streamed to the local native process on `127.0.0.1`, and immediately discarded after speech decoding. Audio is never stored permanently or transmitted over the internet.
- **User Data Collected:** None. No personal data, browsing history, authentication tokens, or telemetry are collected or transmitted.
- **Third-Party Services:** Zero commercial cloud translation APIs or external analytics services are used.

---

## 4. Version History

### Version 1.0.0 (2026-09-02)
- Initial production release.
- Local Japanese-to-English live translation on CPU.
- Anchored subtitle presentation with zero anchor displacement.
- Native Messaging host integration for Linux x86_64.
- YouTube SPA navigation and fullscreen player support.
