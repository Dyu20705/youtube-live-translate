# ADR-001: Manifest V3 Tab Audio Capture & Offscreen Document Architecture

**Status:** Accepted (Reconstructed from Stage S1 Implementation)
**Date:** 2026-09-01
**Deciders:** Core Engineering Team
**Consulted:** Stage S1 Research Report ([`docs/research/s1-audio-capture.md`](../research/s1-audio-capture.md))

---

## 1. Context and Problem Statement

Under Google Chrome Manifest V3, background scripts execute as ephemeral service workers without DOM or Web Audio API access. Direct invocation of deprecated APIs such as `chrome.tabCapture.capture()` inside service workers is disallowed. Furthermore, web page content scripts cannot access raw audio streams from YouTube HTML5 `<video>` elements due to cross-origin isolation and DRM protection.

We required a robust, native browser mechanism to capture audio from active YouTube video and live stream tabs without requiring users to configure virtual audio loopback devices (e.g. PulseAudio/PipeWire loopback, VB-Audio Cable).

---

## 2. Decision: tabCapture Stream ID + Offscreen Document Pipeline

We adopted the official Manifest V3 dual-context architecture:

1. **Service Worker (`background.js`):**
   - Calls `chrome.tabCapture.getMediaStreamId({ targetTabId: tabId })` to obtain an opaque stream token for the active YouTube tab.
   - Spawns and manages a singleton `Offscreen Document` (`offscreen.html`) with reason `USER_MEDIA`.

2. **Offscreen Document (`offscreen.js`):**
   - Consumes the stream ID via `navigator.mediaDevices.getUserMedia({ audio: { mandatory: { chromeMediaSource: 'tab', chromeMediaSourceId: streamId } } })`.
   - Creates an `AudioContext` and connects the source node to `audioContext.destination` to ensure the audio remains completely audible to the user.
   - Attaches an `AudioWorkletNode` for real-time downsampling.

---

## 3. Considered Alternatives & Trade-Offs

| Option | Architectural Assessment | Decision |
| :--- | :--- | :--- |
| **A. Native System Loopback Driver** | Requires users to install PulseAudio modules or virtual audio cables; fragile OS dependency. | **Rejected** |
| **B. DOM `<audio>` Element Interception** | Blocked by YouTube iframe isolation, CORS policies, and DRM video protection. | **Rejected** |
| **C. Deprecated MV2 Background Audio** | Incompatible with Manifest V3 and Chrome Web Store publishing standards. | **Rejected** |
| **D. tabCapture + Offscreen Document** | Fully compliant with Manifest V3; zero OS driver setup; clean Web Audio API access. | **Accepted** |

---

## 4. Consequences

### Positive
- Fully supported under Chrome Manifest V3 with long-term platform stability.
- Zero external driver dependencies or OS-level audio reconfiguration required from users.
- YouTube audio remains audible during translation without attenuation or distortion.

### Negative / Trade-offs
- Tab audio capture requires explicit user gesture/interaction via extension popup action.
- Offscreen document lifecycle must be managed to avoid memory leaks when translation stops.
