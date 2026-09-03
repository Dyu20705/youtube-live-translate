# YouTube Live Translate

> **Local-first real-time subtitle translation system delivered Extension-first for YouTube Live and video streams.**

---

## 1. Overview

`youtube-live-translate` is a local-first real-time AI translation system delivered **Extension-first** through a Manifest V3 Chrome Extension connected to an on-device CPU inference runtime.

* **Ultimate Objective:** Translate spoken Japanese from YouTube streams into **natural, accurate English (US)** while minimizing perceived latency between speech and understandable translated output. Core translation hot-path executes strictly on local hardware with **zero mandatory commercial cloud API dependencies**.
* **Defining Characteristic:** **Progressive Translation with Anchored Presentation** — emitting immediate provisional translations as acoustic tokens arrive, progressively accumulating context, and stabilizing full-clause translations with zero subtitle flicker ($\text{anchor displacement} = 0.0000\text{px}$).

---

## 2. Current Status & Evidence Ladder

The project progresses through a rigorous, empirically verified **Evidence Ladder**:

* **S0 — Architecture Demonstrator:** **`FROZEN`** ([`s0-architecture.md`](docs/research/s0-architecture.md), [`ADR-000`](docs/adr/ADR-000-evidence-policy-and-s0-freeze.md)) — Initial demonstrator preserved as architectural and UX reference.
* **S1 — YouTube Audio Capture PoC:** **`PASS`** ([`s1-audio-capture.md`](docs/research/s1-audio-capture.md), [`ADR-001`](docs/adr/ADR-001-manifest-v3-tab-audio-capture.md), [`ADR-002`](docs/adr/ADR-002-realtime-audio-resampling-contract.md)) — Tab audio capture via Manifest V3 Offscreen Document, real-time $48\text{kHz} \to 16\text{kHz}$ linear PCM downsampling ($0.567\mu\text{s}$ overhead), and verified audio passthrough.
* **S2 — Local Streaming ASR Feasibility:** **`FROZEN`** ([`s2-streaming-asr.md`](docs/research/s2-streaming-asr.md), [`ADR-003`](docs/adr/ADR-003-streaming-asr-engine-selection.md), [`ADR-004`](docs/adr/ADR-004-s2-performance-contract.md)) — Selected **Sherpa-ONNX (Zipformer Streaming Transducer INT8)** with $\text{TTFT} < 65\text{ms}$ (EN) / $< 130\text{ms}$ (JA), $\text{RTF} < 0.08$ on CPU, zero destructive revisions ($\text{SPR} = 1.00$), and bounded memory.
* **S3 — Local Machine Translation (MT) Feasibility:** **`PASS`** ([`s3-local-mt.md`](docs/research/s3-local-mt.md), [`ADR-005`](docs/adr/ADR-005-local-mt-engine-selection.md)) — Selected **Helsinki-NLP Marian CTranslate2 INT8** ($\text{p50} = 65.73\text{ms}$, $82\text{MB}$ weights, Apache 2.0 permissive license).
* **S4 — Incremental Translation & Adaptive Frontier:** **`PASS`** ([`s4-incremental-translation.md`](docs/research/s4-incremental-translation.md), [`ADR-006`](docs/adr/ADR-006-incremental-translation-frontier.md)) — Deterministic stateful streaming translation layer with Local Agreement ($K=2$), Adaptive Frontier ($W=2$), strictly immutable committed prefix ($\text{revisions} = 0$), $82.7\%$ MT call reduction on streaming audio, and sub-millisecond policy overhead ($\text{p50} = 0.031\text{ms}$).
* **S5 — Extension UI & Native Host Integration:** **`PASS`** ([`s5-extension-ui-native-host.md`](docs/research/s5-extension-ui-native-host.md), [`ADR-007`](docs/adr/ADR-007-extension-renderer-and-native-host-integration.md)) — Manifest V3 Chrome Extension and local Native Host / WebSocket bridge with **Anchored Layout Subtitle Presentation** ($\text{anchor displacement} = 0.0000\text{px}$), frame coalescing via `requestAnimationFrame`, versioned wire protocol `v1.0`, and sub-millisecond render dispatch latency ($\text{p50} = 0.000\text{ms}$).
* **V1 — User-Ready Product Release:** **`PASS`** ([`dist/`](dist/), [`CHANGELOG.md`](CHANGELOG.md), [`INSTALL.md`](docs/user/INSTALL.md)) — Packaged Chrome Extension, automated Linux runtime installer with model lifecycle management, tab detection popup UI, and zero-configuration Native Messaging integration.

---

## 3. Project Structure

```text
youtube-live-translate/
├── dist/                              # Standalone distribution packages
│   ├── extension/                     # Packaged Chrome Extension (.zip + unpacked)
│   └── runtime/                       # Standalone Linux Native Runtime (.tar.gz + unpacked)
├── docs/                              # Architecture specifications, ADRs, research & evidence
│   ├── Architecture Specification v1.0.md
│   ├── adr/                           # Architectural Decision Records (ADR-000 to ADR-007)
│   ├── evidence/                      # Empirical benchmark data (S1 through S5)
│   │   ├── s1-audio-capture/
│   │   ├── s2-streaming-asr/
│   │   ├── s3-local-mt/
│   │   ├── s4-incremental-translation/
│   │   └── s5-extension-ui/
│   ├── research/                      # Master Research Index and S0-S5 deep-dive reports
│   └── user/                          # End-user documentation (Install, Quickstart, Privacy, etc.)
├── scripts/                           # Release build & automated verification gates
│   ├── build_release.sh
│   └── verify_release.sh
├── src/                               # Canonical V1 Production Source Code
│   ├── extension/                     # Chrome Extension (Manifest V3)
│   └── runtime/                       # Local Native Runtime (Host, Engines, Models, Installer)
├── poc/                               # Historical verification proof-of-concept stages
│   ├── s1-audio-capture/
│   ├── s2-streaming-asr/
│   ├── s3-local-mt/
│   ├── s4-incremental-translation/
│   └── s5-extension-ui/
├── CHROMEWEBSTORE.md                  # Chrome Web Store metadata & permissions justifications
├── VERSION                            # 1.0.0
└── CHANGELOG.md                       # Product release history
```

---

## 4. Quick Start for Users

1. **Install Local Runtime (Linux x86_64):**
   ```bash
   tar -xzf dist/runtime/youtube-live-translate-runtime-linux-x86_64-v1.0.0.tar.gz
   cd youtube-live-translate-runtime-linux-x86_64-v1.0.0
   ./install.sh
   ```
2. **Install Chrome Extension:**
   - Open Chrome $\to$ `chrome://extensions/` $\to$ Enable **Developer mode** $\to$ **Load unpacked** $\to$ Select `dist/extension/youtube-live-translate`.
3. **Translate Live Video:**
   - Open any Japanese YouTube stream $\to$ Click the extension icon $\to$ Click **Start Live Translation**.

For detailed instructions, see [`docs/user/INSTALL.md`](docs/user/INSTALL.md) and [`docs/user/QUICKSTART.md`](docs/user/QUICKSTART.md).

---

## 5. Automated Verification & Testing

To run the complete 7-gate release verification suite:

```bash
./scripts/verify_release.sh
```

To run individual stage benchmarks:
```bash
# S1: In-browser AudioWorklet downsampling test
node poc/s1-audio-capture/test_audio_worklet.mjs

# S2: Frozen streaming ASR performance contract check
PYTHONPATH=poc/s2-streaming-asr poc/s2-streaming-asr/.venv/bin/python poc/s2-streaming-asr/scripts/run_regression_check.py

# S3: Local MT benchmark
PYTHONPATH=poc/s3-local-mt poc/s2-streaming-asr/.venv/bin/pytest poc/s3-local-mt/tests/

# S4: Incremental translation policy tests
PYTHONPATH=poc/s4-incremental-translation:poc/s3-local-mt:poc/s2-streaming-asr poc/s2-streaming-asr/.venv/bin/pytest poc/s4-incremental-translation/tests/

# S5: Extension DOM renderer & browser geometry tests
node poc/s5-extension-ui/tests/test_renderer.mjs
node poc/s5-extension-ui/tests/test_anchor_displacement.mjs
node poc/s5-extension-ui/tests/test_browser_geometry.mjs
```

---

## 6. Complete Documentation Index

### Architectural Decision Records (ADRs)
* **[`ADR-000`](docs/adr/ADR-000-evidence-policy-and-s0-freeze.md):** Evidence Policy & Stage S0 Freeze
* **[`ADR-001`](docs/adr/ADR-001-manifest-v3-tab-audio-capture.md):** Manifest V3 Tab Audio Capture & Offscreen Document Architecture
* **[`ADR-002`](docs/adr/ADR-002-realtime-audio-resampling-contract.md):** Real-Time In-Browser Audio Resampling Contract
* **[`ADR-003`](docs/adr/ADR-003-streaming-asr-engine-selection.md):** Streaming ASR Engine Selection (Sherpa-ONNX Zipformer)
* **[`ADR-004`](docs/adr/ADR-004-s2-performance-contract.md):** Stage S2 Frozen Performance Contract
* **[`ADR-005`](docs/adr/ADR-005-local-mt-engine-selection.md):** Local Machine Translation Engine Selection (Marian INT8)
* **[`ADR-006`](docs/adr/ADR-006-incremental-translation-frontier.md):** Incremental Translation Policy (Local Agreement $K=2, W=2$)
* **[`ADR-007`](docs/adr/ADR-007-extension-renderer-and-native-host-integration.md):** Anchored Subtitle Presentation Layer & Native Host Integration

### Stage Research Reports
* **Master Research Index & Synthesis:** [`docs/research/RESEARCH.md`](docs/research/RESEARCH.md)
* **Caution Baseline & Risk Register:** [`docs/research/Caution.md`](docs/research/Caution.md)
* **Stage S0 (Architecture Demonstrator):** [`docs/research/s0-architecture.md`](docs/research/s0-architecture.md)
* **Stage S1 (Audio Capture & Resampling):** [`docs/research/s1-audio-capture.md`](docs/research/s1-audio-capture.md)
* **Stage S2 (Streaming Local ASR):** [`docs/research/s2-streaming-asr.md`](docs/research/s2-streaming-asr.md)
* **Stage S3 (Local Machine Translation):** [`docs/research/s3-local-mt.md`](docs/research/s3-local-mt.md)
* **Stage S4 (Incremental MT & Frontier):** [`docs/research/s4-incremental-translation.md`](docs/research/s4-incremental-translation.md)
* **Stage S5 (Extension UI & Native Host):** [`docs/research/s5-extension-ui-native-host.md`](docs/research/s5-extension-ui-native-host.md)

### User & Store Documentation
* **Installation Guide:** [`docs/user/INSTALL.md`](docs/user/INSTALL.md)
* **Quick Start Guide:** [`docs/user/QUICKSTART.md`](docs/user/QUICKSTART.md)
* **Troubleshooting Guide:** [`docs/user/TROUBLESHOOTING.md`](docs/user/TROUBLESHOOTING.md)
* **Privacy & Local AI Statement:** [`docs/user/PRIVACY.md`](docs/user/PRIVACY.md)
* **Support Matrix:** [`docs/user/SUPPORT_MATRIX.md`](docs/user/SUPPORT_MATRIX.md)
* **Chrome Web Store Specification:** [`CHROMEWEBSTORE.md`](CHROMEWEBSTORE.md)
