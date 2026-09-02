# ADR-000: Architecture Baseline, Evidence Policy & S0 Freeze

**Status:** Accepted
**Date:** 2026-09-01
**Deciders:** Core Engineering Team

---

## 1. Context and Problem Statement

The initial generation of the `youtube-live-translate` repository resulted in an interactive React/Vite web application ("Architecture & Studio Demonstrator"). While this artifact successfully communicated the conceptual vocabulary (5 planes, progressive refinement UI, event models, hardware profiles, MLOps metrics), it lacked the underlying engineering implementation:
- No real Chrome Extension (Manifest V3, Service Worker, Offscreen tabCapture).
- No compiled Native Messaging Host / Local AI Runtime.
- No actual ASR (Automatic Speech Recognition) or MT (Machine Translation) inference.
- No empirical replay or benchmark execution engine.

All metrics presented in the S0 demonstrator (e.g., TTFT 180ms, WER, BLEU 39.4, COMET 0.86, Zero Cloud) were **declared/simulated**, not **empirically measured**.

Continuing to develop or polish the S0 Studio UI introduces *demo gravity*, drifting the project away from building a lean, verifiable, local-first YouTube translation extension.

---

## 2. Decision Drivers

1. **Reality over Simulation**: The core differentiator of this project is local realtime translation with progressive refinement. This requires experimental validation on real audio, real models, and real browser streams.
2. **Evidence-First Engineering**: Every metric, capability, and performance claim must be backed by reproducible empirical data.
3. **Local-First Hygiene**: Core hot-path inference must strictly execute locally on user hardware without reliance on commercial cloud APIs (e.g., OpenAI, Google Gemini API).
4. **Scope Control**: User-facing product is a minimal Chrome Extension, not an expansive multi-tab AI studio.

---

## 3. Considered Options

* **Option A:** Continue building the React/Vite Studio app into a desktop/web app with backend AI services.
* **Option B:** Freeze S0 Studio as an architectural reference, discard cloud dependencies, and execute an evidence-driven ladder of standalone PoCs starting with browser audio capture and local inference.

---

## 4. Decision Outcome

**Chosen Option:** **Option B**.

### 4.1 Actions Decided

1. **Freeze S0 Demonstrator**:
   - The React/Vite Studio code is preserved under `prototypes/s0-architecture-studio/` as a design and UX reference.
   - No further feature expansion will take place inside the S0 Studio.
   - All numbers in S0 are formally classified as `DECLARED / SIMULATED`.

2. **Establish Evidence Hierarchy**:
   Every capability in this repository must progress through the formal ladder:
   $$\text{CLAIM} \longrightarrow \text{DESIGN} \longrightarrow \text{PROTOTYPE} \longrightarrow \mathbf{\text{MEASURED}} \longrightarrow \mathbf{\text{VALIDATED}} \longrightarrow \mathbf{\text{REGRESSION-PROTECTED}}$$

3. **Dependency Cleanup**:
   - Cloud API dependencies (such as `@google/genai`) are banned from the hot translation path.
   - Any auxiliary LLM usage is restricted strictly to asynchronous, offline cold-path language intelligence (e.g., glossary extraction) and must support local models (Ollama / llama.cpp).

4. **Execution Roadmap (Evidence Ladder)**:
   - **S1 (P0):** YouTube Tab Audio Capture PoC (`tabCapture` + `Offscreen` $\to$ 16kHz PCM).
   - **S2 (P0):** Streaming Local ASR Feasibility (Sherpa-ONNX / Whisper.cpp $\to$ WER, RTF, TTFT).
   - **S3 (P0):** Local MT Feasibility (Marian / OPUS-MT / NLLB-200 quantized $\to$ BLEU, chrF, latency).
   - **S4 (P0):** Incremental Translation & Revision minimization research (Wait-$k$, Stable Prefix).
   - **S5 (P1):** Cold-path Context Intelligence & Terminology.
   - **S6 (P1):** Deterministic Audio Replay & Evaluation Harness.
   - **S7 (P1):** Minimal Chrome Extension & Native Messaging Host integration.
   - **S8 (P2):** Resource Management, Graceful Degradation & Crash Recovery.
   - **S9 (P2):** Packaging & Local Model Distribution.
   - **S10 (P3):** Real-world YouTube Live / VOD empirical testing.
   - **S11 (P3):** Production Readiness Gate.

---

## 5. Consequences

### Positive
- Prevents wasted effort building unnecessary UI dashboards.
- Focuses 100% of engineering resources on solving core bottlenecks: audio capture stability, streaming ASR latency, and incremental MT flicker.
- Guarantees that performance numbers published in documentation are reproducible and scientifically verifiable.

### Negative / Trade-offs
- The standalone PoCs will not have glossy dashboards in the initial phases (they will produce terminal logs, raw PCM audio artifacts, and JSON metric reports).
- Requires setting up local model runners (Sherpa-ONNX, ONNX Runtime, Rust/C++ toolchains).
