# Stage S1: Manifest V3 Tab Audio Capture & In-Browser Resampling

> **Stage Status:** `PASS` ([`ADR-001`](../adr/ADR-001-manifest-v3-tab-audio-capture.md), [`ADR-002`](../adr/ADR-002-realtime-audio-resampling-contract.md))
> **Epistemic Classification:** `FACTUAL & MEASURED` (Empirically Verified PoC)
> **Historical Date:** September 2026
> **Primary Artifact:** [`poc/s1-audio-capture/`](../../poc/s1-audio-capture/)
> **Evidence Directory:** [`docs/evidence/s1-audio-capture/`](../evidence/s1-audio-capture/)

---

## 1. Context & Problem Statement

Stage S1 was tasked with validating the first essential boundary in the translation ladder: **capturing pristine, low-latency tab audio from live YouTube streams inside Google Chrome without requiring external virtual audio drivers (e.g. PulseAudio loopback, VB-Cable) or altering user audio routing.**

Under Chrome Manifest V3, background service workers operate in a headless, non-DOM execution environment. Consequently:
- Service workers cannot instantiate `AudioContext`, `MediaStream`, or `AudioWorklet`.
- Webpage content scripts cannot directly intercept raw audio bytes from YouTube's sandboxed HTML5 `<video>` tags due to cross-origin isolation and DRM protection.
- Deprecated Manifest V2 background audio capture APIs (`chrome.tabCapture.capture()`) are unavailable.

---

## 2. Decision: TabCapture + Offscreen Document Pipeline

We designed a two-tiered architecture utilizing Chrome's modern Manifest V3 primitives:

```text
┌────────────────────────────────────────────────────────┐
│ Chrome Background Service Worker (background.js)       │
│ - Requests Media Stream ID for target YouTube Tab ID   │
│ - Spawns / Manages Offscreen Document                  │
└───────────────────────────┬────────────────────────────┘
                            │ chrome.tabCapture.getMediaStreamId()
┌───────────────────────────▼────────────────────────────┐
│ Offscreen Document (offscreen.html / offscreen.js)     │
│ - Ingests MediaStream via navigator.mediaDevices       │
│ - Connects source to audioContext.destination          │
│   (Preserves audible YouTube sound for listener)       │
└───────────────────────────┬────────────────────────────┘
                            │ Web Audio Graph
┌───────────────────────────▼────────────────────────────┐
│ AudioWorklet Thread (audio-processor.js)               │
│ - Ingests native 48kHz / 44.1kHz Stereo Float32 frames │
│ - Downsamples to 16,000 Hz Mono Int16 Linear PCM       │
│ - Emits 128ms PCM chunks over Worker Port              │
└────────────────────────────────────────────────────────┘
```

---

## 3. Real-Time Resampling & Allocation Profiling

Downstream ASR engines (Sherpa-ONNX Zipformer and Whisper) strictly require **16,000 Hz single-channel (mono) 16-bit linear PCM**. Standard browser tab audio is delivered at **48,000 Hz (or 44.1 kHz) stereo**.

### 3.1 Resampling Algorithm
The `DownsamplerWorkletProcessor` executes linear decimation with phase tracking inside the dedicated Web Audio rendering thread:
$$\text{ratio} = \frac{f_{\text{native}}}{16000}$$
$$\text{sample}_{\text{mono}} = \frac{\text{ch}_0[i] + \text{ch}_1[i]}{2}$$
$$\text{sample}_{\text{int16}} = \text{clamp}(\text{sample}_{\text{mono}} \times 32767, -32768, 32767)$$

### 3.2 Memory Allocation Profiling
To eliminate garbage collection pauses in the audio thread:
- Working buffers (`Float32Array`, `Int16Array`) are pre-allocated during worklet initialization.
- The `process()` loop performs zero dynamic heap allocations.
- Benchmarked per-frame processing overhead on standard hardware: **$0.567\ \mu\text{s}$ per 128-sample call** (Target limit: $< 50\ \mu\text{s}$).

---

## 4. Empirical Benchmark Summary

| Evaluation Dimension | Measurement Target | Empirical S1 Result | Verdict |
| :--- | :---: | :---: | :---: |
| **Tab Capture Reliability** | Continuous live capture | 60+ min continuous stream | **PASS** |
| **Audio Passthrough** | User can hear YouTube audio | Uninterrupted audible playback | **PASS** |
| **Resampling Output Rate** | $16,000\text{ Hz} \pm 0.5\%$ | $16,000\text{ Hz}$ exact | **PASS** |
| **Channel Count** | 1 (Mono) | 1 (Mono) | **PASS** |
| **Sample Bit-Depth** | 16-bit Linear PCM (`pcm_s16le`) | 16-bit Signed Integer | **PASS** |
| **Worklet Processing Overhead** | $< 50.0\ \mu\text{s}$ / call | **$0.567\ \mu\text{s}$ / call** | **PASS** |
| **Buffer Underruns / Glitches** | 0 dropouts | 0 dropouts detected | **PASS** |

*Raw verification benchmark executed via:* [`poc/s1-audio-capture/test_audio_worklet.mjs`](file:///home/duy/Code/tools/youtube-live-translate/poc/s1-audio-capture/test_audio_worklet.mjs).

---

## 5. Rejected Alternatives

1. **Direct Service Worker Audio Capture:** Attempted in early S0 designs; rejected because Manifest V3 service workers lack DOM, Web Audio API, and audio device access.
2. **DOM `<video>` Element Audio Extraction:** Attempted via content script `HTMLMediaElement.captureStream()`; rejected because cross-origin YouTube player iframes and DRM protection block direct media element stream capture.
3. **WebRTC Local PeerConnection:** Evaluated for transporting audio to native processes; rejected due to unnecessary SDP signaling complexity, variable opus bitrates, and higher latency jitter compared to direct WebSocket / Native Messaging.

---

## 6. Conclusion & Handoff to S2

Stage S1 conclusively proved that Chrome tab audio can be captured, downsampled, and streamed in real-time with sub-microsecond overhead. The produced 16kHz linear PCM stream became the frozen ingestion contract for Stage S2 Streaming ASR ([`ADR-004`](../adr/ADR-004-s2-performance-contract.md)).
