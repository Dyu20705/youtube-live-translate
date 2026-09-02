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
* **S3 — Local Machine Translation (MT) Feasibility:** **`READY / NEXT`** — Benchmarking local translation runtimes (MarianMT / NLLB-200 INT8).

---

## 3. Project Structure

```
youtube-live-translater/
├── docs/                        # System architecture specifications, ADRs, and empirical evidence
│   ├── Architecture Specification v1.0.md
│   ├── adr/                     # Architectural Decision Records (ADR-000 to ADR-004)
│   ├── evidence/                # Reproducible benchmark metrics and JSON datasets
│   └── research/                # Technical deep-dives, caution registers, and audit reports
├── poc/                         # Standalone proof-of-concept implementations
│   ├── s1-audio-capture/        # Manifest V3 Chrome Extension for audio capture
│   └── s2-streaming-asr/        # Streaming ASR engines, benchmarks, and regression gates
└── .gitignore                   # Excludes binaries, ML model weights, virtual environments, and temporary recordings
```

---

## 4. Roadmap

```
[S0 Demonstrator] ➔ [S1 Audio Capture] ➔ [S2 Streaming ASR] ➔ [S3 Local MT] ➔ [S4 Progressive Pipeline] ➔ [S5 Extension UI] ➔ [v1 Product]
     (Frozen)               (PASS)               (FROZEN)          (Current)
```

---

## 5. Quick Start & Development

### S1: Audio Capture Extension
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** $\to$ Click **Load unpacked** $\to$ Select `poc/s1-audio-capture/`.
3. Open any YouTube video or live stream, click the extension icon, and select **Start Capture**.

### S2: Streaming ASR Benchmark & Regression Gate
```bash
# 1. Set up Python environment
cd poc/s2-streaming-asr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest

# 2. Download reference models and datasets
python scripts/download_models.py
python scripts/prepare_dataset.py

# 3. Run unit tests and enforce the performance contract gate
PYTHONPATH=. python scripts/run_regression_check.py
```

---

## 6. Documentation

For detailed technical specifications, architectural decisions, and empirical benchmarks:

* **System Architecture Specification:** [`docs/Architecture Specification v1.0.md`](docs/Architecture%20Specification%20v1.0.md)
* **Evidence Policy & S0 Freeze:** [`docs/adr/ADR-000-evidence-policy-and-s0-freeze.md`](docs/adr/ADR-000-evidence-policy-and-s0-freeze.md)
* **Streaming ASR Engine Selection:** [`docs/adr/ADR-003-streaming-asr-engine-selection.md`](docs/adr/ADR-003-streaming-asr-engine-selection.md)
* **S2 Frozen Performance Contract:** [`docs/adr/ADR-004-s2-performance-contract.md`](docs/adr/ADR-004-s2-performance-contract.md)
* **Empirical Benchmark Evidence:** [`docs/evidence/s2-streaming-asr/`](docs/evidence/s2-streaming-asr/)
