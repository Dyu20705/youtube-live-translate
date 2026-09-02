# Stage S0: Architecture Demonstrator & Conceptual Baseline

> **Stage Status:** `FROZEN` ([`ADR-000`](../adr/ADR-000-evidence-policy-and-s0-freeze.md))
> **Epistemic Classification:** `DECLARED / SIMULATED` (Non-Empirical Baseline)
> **Historical Date:** August 2026
> **Purpose:** Document the initial product vision, 5-plane conceptual architecture, simulated latency claims, and the specific reasons for freezing S0 in favor of an empirical evidence ladder.

---

## 1. Original Product Hypothesis

The `youtube-live-translater` project began with a high-level product hypothesis:

> *Can a browser extension deliver real-time, high-accuracy translation of live Japanese YouTube streams into natural English subtitles using on-device local AI with zero cloud API dependencies?*

The initial Stage S0 artifact was created as an interactive web demonstrator ("Architecture & Studio Demonstrator"). It established the conceptual vocabulary, architectural planes, and target user experience for progressive subtitle refinement.

```text
┌────────────────────────────────────────────────────────┐
│ S0 Conceptual Five-Plane Architecture                  │
│                                                        │
│ 1. Audio Plane       : Tab capture & downsampling      │
│ 2. ASR Plane         : Streaming speech-to-text        │
│ 3. Policy & MT Plane : Incremental translation logic   │
│ 4. Context Plane     : Auxiliary glossary & reasoning  │
│ 5. Presentation Plane: Floating overlay & subtitles    │
└────────────────────────────────────────────────────────┘
```

---

## 2. Declared & Simulated Metrics in S0

During Stage S0, performance numbers and latency metrics were modeled mathematically and simulated in UI mockups rather than measured against actual neural network inference on hardware:

| Evaluated Dimension | S0 Declared Value | Epistemic Classification | Actual S2–S5 Empirical Outcome |
| :--- | :---: | :---: | :---: |
| **ASR Time-to-First-Token (TTFT)** | $180\text{ ms}$ | `DECLARED / SIMULATED` | **$62.9\text{ ms}$ (EN) / $125.7\text{ ms}$ (JA)** (Sherpa Zipformer) |
| **ASR Real-Time Factor (RTF)** | $< 0.15$ | `DECLARED / SIMULATED` | **$0.025$ (EN) / $0.082$ (JA)** (CPU Multi-core) |
| **MT Inference Latency (p50)** | $45\text{ ms}$ | `DECLARED / SIMULATED` | **$65.7\text{ ms}$** (CTranslate2 Marian INT8) |
| **Translation Quality (BLEU)** | $39.4$ | `DECLARED / SIMULATED` | **$21.4$ (Raw ASR) / $26.8$ (Clean)** |
| **Subtitle Flicker Rate** | $0\%$ | `DECLARED / SIMULATED` | **$0.0000\text{ px}$ Anchor Displacement** (S5 Dual-Box) |
| **Cloud API Overhead** | $0\text{ ms}$ | `DECLARED / SIMULATED` | **Zero Cloud Required** (100% On-Device Local) |

---

## 3. Why Stage S0 Was Frozen

In accordance with [`ADR-000`](../adr/ADR-000-evidence-policy-and-s0-freeze.md), Stage S0 was formally frozen to protect the project from *demo gravity* (the tendency to polish visual simulators rather than solving hard engineering constraints):

1. **Absence of Real Browser Primitives:** S0 was a standalone web page; it lacked Manifest V3 Service Worker integration, `tabCapture` stream handling, and Native Messaging stdio protocols.
2. **Absence of Real Local AI Engines:** S0 simulated ASR and MT with synthetic timers and static JSON transcripts; it did not execute ONNX or CTranslate2 inference engines.
3. **Risk of Uncontrolled Cloud Creep:** Conceptual designs flirted with commercial cloud APIs (e.g. Gemini, OpenAI) for real-time translation, which violated the local-first, privacy-respecting core premise.
4. **Transition to Evidence-First Ladder:** Engineering governance mandated that no metric could be claimed without a reproducible test harness and raw measurement artifacts.

---

## 4. Key S0 Hypotheses & Their Empirical Resolutions

| S0 Architectural Hypothesis | Moving to Empirical PoC (S1–S5) | Empirical Resolution |
| :--- | :--- | :--- |
| **H1: Background Audio Capture** | Background service workers in Manifest V3 have no DOM or Web Audio access. | **Invalidated.** Replaced with `tabCapture` stream ID + `Offscreen Document` ([`ADR-001`](../adr/ADR-001-manifest-v3-tab-audio-capture.md)). |
| **H2: Single-pass Monolithic Subtitle String** | Re-rendering the full string on every word causes severe visual flicker. | **Invalidated.** Replaced with S5 Dual-Box Anchored Presentation ([`ADR-007`](../adr/ADR-007-extension-renderer-and-native-host-integration.md)). |
| **H3: Cloud LLM on Streaming Critical Path** | Cloud API latency ($> 800\text{ms}$) destroys conversational subtitle pacing. | **Banned.** Core hot-path restricted strictly to local CPU Marian INT8 MT ([`ADR-005`](../adr/ADR-005-local-mt-engine-selection.md)). |
| **H4: Whisper-only ASR Pipeline** | Standard Whisper chunking requires high compute and introduces windowing delay. | **Refined.** Sherpa-ONNX Zipformer selected for native causal streaming with $\text{RTF} < 0.08$ ([`ADR-003`](../adr/ADR-003-streaming-asr-engine-selection.md)). |

---

## 5. Architectural Legacy of S0

While frozen as a code artifact, Stage S0 permanently contributed foundational design principles to the V1 system:
- **Progressive Refinement:** The user interface must present provisional words immediately while stabilizing committed text.
- **Evidence Hierarchy:** Every technical claim must progress through: $\text{Claim} \to \text{Design} \to \text{Prototype} \to \text{Measured} \to \text{Validated} \to \text{Regression-Protected}$.
- **Decoupled 4-Layer Architecture:** Strict separation between audio capture, streaming ASR, incremental translation policy, and DOM presentation.
