# Stage S5 — Extension UI & Native Host Integration

This directory contains the implementation and benchmark suite for **Stage S5: Extension UI & Native Host Integration**.

---

## 1. Overview

Stage S5 delivers the Manifest V3 Chrome Extension and local Native Host / WebSocket bridge that presents real-time translated subtitles with an **Anchored Layout & Stable Subtitle Presentation Layer**.

```text
┌─────────────────────────────────────────┐
│ S5 Subtitle Presentation Layer (DOM/CSS)│
│ - Anchored Committed Box (100% Solid)   │
│ - Attached Provisional Box (65% Dimmed) │
│ - 0.0px Spatial Anchor Displacement     │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│ Subtitle State Adapter (JavaScript)     │
│ - Monotonic Reordering & Stale Reject   │
│ - Duplicate Deduplication (78 frames)   │
│ - Frame Coalescing (rAF)                │
└───────────────────┬─────────────────────┘
                    │ Wire Protocol JSON v1.0
┌───────────────────▼─────────────────────┐
│ Native Host / Local Runtime Bridge      │
│ - S2 Zipformer ASR + S4 Incremental MT  │
│ - Chrome Native Messaging + WebSocket   │
└─────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
poc/s5-extension-ui/
├── manifest.json                  # Manifest V3 Extension Configuration
├── background.js                  # Service worker managing bridge & audio capture
├── offscreen.html                 # Audio capture offscreen document
├── offscreen.js                   # Offscreen audio stream coordinator
├── audio-processor.js             # 48kHz -> 16kHz PCM downsampler AudioWorklet
├── wav-encoder.js                 # Minimal WAV encoder
├── content/
│   ├── subtitle_renderer.js       # Anchored dual-box subtitle renderer
│   ├── subtitle_adapter.js        # State adapter, stale rejection, coalescing
│   ├── subtitle_overlay.css       # Responsive, high-contrast overlay styling
│   └── content_script.js          # Injects viewport into YouTube video player
├── popup/
│   ├── popup.html                 # Extension popup interface
│   ├── popup.css
│   └── popup.js
├── bridge/
│   ├── protocol.py                # Version 1.0 JSON wire protocol schemas
│   ├── runtime_pipeline.py        # S2 ASR -> S4 Incremental Translation driver
│   ├── native_messaging_host.py   # Chrome Native Messaging stdio host
│   ├── websocket_bridge.py        # Local WebSocket bridge server
│   └── manifest_host.json         # Native messaging host registration manifest
├── tests/
│   ├── test_protocol.py           # Protocol serialization & validation tests
│   ├── test_runtime_pipeline.py   # Pipeline state transition tests
│   ├── test_e2e_streaming.py      # E2E live audio streaming test
│   ├── test_renderer.mjs          # Node.js DOM unit tests (Tests A through J)
│   └── test_anchor_displacement.mjs # Geometry layout test (0.0px anchor shift)
└── benchmark/
    ├── s5_benchmark.py            # Comparative rendering simulation
    └── run_s5_benchmark.py        # CLI benchmark runner
```

---

## 3. Quick Start & Reproduction

### Run S5 JavaScript / DOM Unit Tests
```bash
node poc/s5-extension-ui/tests/test_renderer.mjs
node poc/s5-extension-ui/tests/test_anchor_displacement.mjs
```

### Run S5 Python Pipeline Tests
```bash
PYTHONPATH=poc/s5-extension-ui:poc/s4-incremental-translation:poc/s3-local-mt:poc/s2-streaming-asr \
poc/s2-streaming-asr/.venv/bin/pytest poc/s5-extension-ui/tests/ -v
```

### Run S5 Rendering & Anchored Layout Benchmark
```bash
PYTHONPATH=poc/s5-extension-ui:poc/s4-incremental-translation:poc/s3-local-mt:poc/s2-streaming-asr \
poc/s2-streaming-asr/.venv/bin/python poc/s5-extension-ui/benchmark/run_s5_benchmark.py
```

### Load Extension in Google Chrome
1. Navigate to `chrome://extensions/`.
2. Enable **Developer mode** $\to$ Click **Load unpacked** $\to$ Select `poc/s5-extension-ui/`.
3. Open any YouTube live stream or video, click the extension icon, and click **Start Live Translation**.

---

## 4. Documentation

* **Architectural Decision Record:** [`docs/adr/ADR-007-extension-renderer-and-native-host-integration.md`](../../docs/adr/ADR-007-extension-renderer-and-native-host-integration.md)
* **Stage S5 Empirical Research Report:** [`docs/research/s5-extension-ui-native-host.md`](../../docs/research/s5-extension-ui-native-host.md)
* **Evidence Measurements Artifact:** [`docs/evidence/s5-extension-ui/s5_benchmark_measurements.json`](../../docs/evidence/s5-extension-ui/s5_benchmark_measurements.json)
