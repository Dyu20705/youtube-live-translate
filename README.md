# youtube-live-translater

> **Local-first real-time subtitle translation system delivered Extension-first for YouTube Live and video streams.**

---

## 1. Overview

`youtube-live-translater` is a local-first real-time AI translation system delivered **Extension-first**, initially through a Manifest V3 Chrome Extension and extensible to other browsers and platforms.

* **Ultimate Objective:** Translate arbitrary spoken languages from YouTube into **natural, accurate English (US)** while minimizing perceived latency between speech and understandable translated output. Core translation hot-path executes strictly on local hardware with **zero mandatory commercial cloud API dependencies**.
* **Defining Characteristic:** **Progressive Translation with Revision** — emitting immediate provisional translations as acoustic tokens arrive, progressively accumulating context, and stabilizing full-clause translations without distracting subtitle flicker.

---

## 2. Current Status

The project progresses through a rigorous, empirically verified **Evidence Ladder**:

* **S0 — Architecture Demonstrator:** **`FROZEN`** — Initial demonstrator preserved as architectural and UX reference.
* **S1 — YouTube Audio Capture PoC:** **`PASS`** — Tab audio capture via Manifest V3 Offscreen Document, real-time $48\text{kHz} \to 16\text{kHz}$ linear PCM downsampling, and WebSocket streaming.
* **S2 — Local Streaming ASR Feasibility:** **`FROZEN`** ([`s2_performance_contract_v1.json`](poc/s2-streaming-asr/s2_performance_contract_v1.json)) — Selected **Sherpa-ONNX (Zipformer Streaming Transducer)** with $\text{TTFT} < 60\text{ms}$ (EN) / $< 135\text{ms}$ (JA), $\text{RTF} < 0.08$ on CPU, zero destructive revisions ($\text{SPR} = 1.00$), and bounded memory.
* **S3 — Local Machine Translation (MT) Feasibility:** **`PASS`** ([`ADR-005`](docs/adr/ADR-005-local-mt-engine-selection.md)) — Selected **Helsinki-NLP Marian CTranslate2 INT8** ($\text{p50} = 65.73\text{ms}$, $78\text{MB}$ weights, Apache 2.0 permissive license).
* **S4 — Incremental Translation & Adaptive Frontier:** **`PASS`** ([`ADR-006`](docs/adr/ADR-006-incremental-translation-frontier.md)) — Deterministic stateful streaming translation layer with Local Agreement ($K=2$), Adaptive Frontier ($W=2$), strictly immutable committed prefix ($\text{revisions} = 0$), $82.7\%$ MT call reduction on streaming audio, and sub-millisecond policy overhead ($\text{p50} = 0.031\text{ms}$).
* **S5 — Extension UI & Native Host Integration:** **`PASS`** ([`ADR-007`](docs/adr/ADR-007-extension-renderer-and-native-host-integration.md)) — Manifest V3 Chrome Extension and local Native Host / WebSocket bridge with **Anchored Layout Subtitle Presentation** ($\text{anchor\_displacement} = 0.0000\text{px}$), frame coalescing via `requestAnimationFrame`, versioned wire protocol `v1.0`, and sub-millisecond render dispatch latency ($\text{p50} = 0.000\text{ms}$).

---

## 3. Project Structure

```
youtube-live-translater/
├── docs/                        # System architecture specifications, ADRs, and empirical evidence
│   ├── Architecture Specification v1.0.md
│   ├── adr/                     # Architectural Decision Records (ADR-000 to ADR-007)
│   ├── evidence/                # Reproducible benchmark metrics and JSON datasets
│   │   ├── s2-streaming-asr/
│   │   ├── s3-local-mt/
│   │   ├── s4-incremental-translation/
│   │   └── s5-extension-ui/
│   └── research/                # Technical deep-dives, caution registers, and audit reports
├── poc/                         # Standalone proof-of-concept implementations
│   ├── s1-audio-capture/        # Manifest V3 Chrome Extension for audio capture
│   ├── s2-streaming-asr/        # Streaming ASR engines, benchmarks, and regression gates
│   ├── s3-local-mt/             # Local MT engines (Marian / NLLB INT8) & feasibility benchmarks
│   ├── s4-incremental-translation/ # Incremental translation state machine, local agreement & frontier
│   └── s5-extension-ui/         # Anchored subtitle renderer, native bridge, and extension UI
└── .gitignore                   # Excludes binaries, ML model weights, virtual environments, and temporary recordings
```

---

## 4. Roadmap

```
[S0 Demonstrator] ➔ [S1 Audio Capture] ➔ [S2 Streaming ASR] ➔ [S3 Local MT] ➔ [S4 Progressive MT] ➔ [S5 Extension UI] ➔ [v1 Product]
     (Frozen)               (PASS)               (FROZEN)          (PASS)             (PASS)             (PASS)            (Next)
```

---

## 5. Quick Start & Development

### S1: Audio Capture Extension
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** $\to$ Click **Load unpacked** $\to$ Select `poc/s1-audio-capture/`.
3. Open any YouTube video or live stream, click the extension icon, and select **Start Capture**.

### S2: Streaming ASR Benchmark & Regression Gate
```bash
# Run unit tests and enforce the performance contract gate
PYTHONPATH=poc/s2-streaming-asr \
poc/s2-streaming-asr/.venv/bin/python poc/s2-streaming-asr/scripts/run_regression_check.py
```

### S3: Local MT Benchmark
```bash
# Run S3 unit tests and fast benchmark
PYTHONPATH=poc/s3-local-mt \
poc/s2-streaming-asr/.venv/bin/pytest poc/s3-local-mt/tests/
```

### S4: Incremental Translation & Adaptive Frontier Benchmark
```bash
# Run S4 unit & integration test suite (36 tests)
PYTHONPATH=poc/s4-incremental-translation:poc/s3-local-mt:poc/s2-streaming-asr \
poc/s2-streaming-asr/.venv/bin/pytest poc/s4-incremental-translation/tests/ -v

# Run comparative empirical benchmark
PYTHONPATH=poc/s4-incremental-translation:poc/s3-local-mt:poc/s2-streaming-asr \
poc/s2-streaming-asr/.venv/bin/python poc/s4-incremental-translation/benchmark/run_s4_benchmark.py
```

### S5: Extension UI & Anchored Subtitle Benchmark
```bash
# 1. Run S5 Node.js DOM and layout geometry tests
node poc/s5-extension-ui/tests/test_renderer.mjs
node poc/s5-extension-ui/tests/test_anchor_displacement.mjs

# 2. Run S5 Python protocol and e2e streaming tests
PYTHONPATH=poc/s5-extension-ui:poc/s4-incremental-translation:poc/s3-local-mt:poc/s2-streaming-asr \
poc/s2-streaming-asr/.venv/bin/pytest poc/s5-extension-ui/tests/ -v

# 3. Run S5 comparative rendering benchmark
PYTHONPATH=poc/s5-extension-ui:poc/s4-incremental-translation:poc/s3-local-mt:poc/s2-streaming-asr \
poc/s2-streaming-asr/.venv/bin/python poc/s5-extension-ui/benchmark/run_s5_benchmark.py
```

---

## 6. Documentation

For detailed technical specifications, architectural decisions, and empirical benchmarks:

* **System Architecture Specification:** [`docs/Architecture Specification v1.0.md`](docs/Architecture%20Specification%20v1.0.md)
* **Evidence Policy & S0 Freeze:** [`docs/adr/ADR-000-evidence-policy-and-s0-freeze.md`](docs/adr/ADR-000-evidence-policy-and-s0-freeze.md)
* **Streaming ASR Engine Selection:** [`docs/adr/ADR-003-streaming-asr-engine-selection.md`](docs/adr/ADR-003-streaming-asr-engine-selection.md)
* **S2 Frozen Performance Contract:** [`docs/adr/ADR-004-s2-performance-contract.md`](docs/adr/ADR-004-s2-performance-contract.md)
* **Local MT Engine Selection:** [`docs/adr/ADR-005-local-mt-engine-selection.md`](docs/adr/ADR-005-local-mt-engine-selection.md)
* **Incremental Translation Policy:** [`docs/adr/ADR-006-incremental-translation-frontier.md`](docs/adr/ADR-006-incremental-translation-frontier.md)
* **Extension UI & Native Host:** [`docs/adr/ADR-007-extension-renderer-and-native-host-integration.md`](docs/adr/ADR-007-extension-renderer-and-native-host-integration.md)
* **Stage S5 Research Report:** [`docs/research/s5-extension-ui-native-host.md`](docs/research/s5-extension-ui-native-host.md)
* **Empirical Benchmark Evidence:** [`docs/evidence/`](docs/evidence/)
