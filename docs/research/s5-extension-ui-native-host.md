# Stage S5 Empirical Research Report: Extension Presentation Layer & Native Host Integration

**Date:** 2026-09-02
**Status:** Completed & Empirically Validated (`S5 Verdict = PASS`)
**Deciders:** Core Engineering Team
**Evidence Artifact:** [`docs/evidence/s5-extension-ui/s5_benchmark_measurements.json`](file:///home/duy/Code/tools/youtube-live-translate/docs/evidence/s5-extension-ui/s5_benchmark_measurements.json)

---

## 1. Executive Summary

Stage S5 implemented and empirically validated the final runtime presentation layer of the `youtube-live-translate` system:
1. **Anchored Layout Subtitle Renderer:** Eliminates visual subtitle flicker by separating `committed_text` (100% solid opacity, immovable spatial anchor) from `provisional_text` (65% dimmed opacity, italic tail).
2. **Verified Zero Anchor Displacement:** Mathematically verified that provisional text variations cause **0.0000 px** spatial displacement on already-read committed words ($\Delta \text{left} = 0\text{ px}$, $\Delta \text{top} = 0\text{ px}$).
3. **Native Host & Local WebSocket Transport:** Connects the frozen Stage S2 multilingual Zipformer ASR and Stage S4 Incremental Translator Python pipeline to the Manifest V3 Chrome Extension via versioned JSON protocol `v1.0`.
4. **Frame Coalescing & Stale Update Protection:** Coalesces rapid backend bursts into the browser's animation cadence (`requestAnimationFrame`), filtering 78 duplicate/static frames on live streaming audio.
5. **Sub-Millisecond Rendering Latency:** Measured dispatch latency $\text{p50} = 0.000\text{ ms}$, $\text{p95} = 0.001\text{ ms}$.

---

## 2. Experimental Setup & Benchmarking Methodology

- **ASR Engine:** Sherpa-ONNX v1.13.7 multilingual streaming Zipformer (frozen S2 contract).
- **MT Engine:** Helsinki-NLP `opus-mt-ja-en` in CTranslate2 INT8 (Stage S3).
- **Incremental Policy:** Stage S4 Incremental Translator ($K=2$ Local Agreement, $W=2$ buffer).
- **Extension Platform:** Chrome Manifest V3 with Offscreen Document tab audio capture downsampled to 16kHz mono 16-bit PCM.
- **Evaluation Audio Fixture:** `poc/s2-streaming-asr/datasets/ja_conversational.wav` (13.96s duration, 109 chunks).

---

## 3. Empirical Comparison: Raw Unified UI vs S5 Anchored UI

```text
               RAW UNIFIED RENDERING                          S5 ANCHORED DUAL-BOX RENDERING
               (Unanchored / Centered)                             (Left-Anchored Dual Box)
                         │                                                    │
                         ▼                                                    ▼
         [    The weather today is...   ]                    [ The weather today ][ is nice ]
                         │ (provisional length changes)                       │ (provisional length changes)
                         ▼                                                    ▼
         [ The weather today is very cold ]                  [ The weather today ][ is very cold ]
                         │                                                    │
             Spatial Shift: 239.40 px                              Spatial Shift: 0.0000 px
             Visual Flicker: SEVERE                                Visual Flicker: ELIMINATED
```

| Evaluation Dimension | Raw Unified Strategy | S5 Anchored Strategy | Target / Invariant |
| :--- | :---: | :---: | :---: |
| **Total Ingested Events** | 98 | 98 | - |
| **DOM Updates Executed** | 19 | 20 | Bounded |
| **Committed Text Updates** | N/A | 2 | Monotonic |
| **Provisional Tail Updates**| N/A | 20 | Tail only |
| **Noop Duplicate Events Filtered** | 0 | **78** | Efficient |
| **Full-Node DOM Replacements** | 19 | **0** | $= 0$ (Targeted) |
| **Max Anchor Displacement (px)** | **239.40 px** | **0.0000 px** | $= 0.0\text{ px}$ (PASS) |
| **Avg Anchor Displacement (px)** | **80.27 px** | **0.0000 px** | $= 0.0\text{ px}$ (PASS) |
| **Render Latency p50 (ms)** | $< 0.05\text{ ms}$ | **0.000 ms** | $< 16.0\text{ ms}$ |
| **Render Latency p95 (ms)** | $< 0.08\text{ ms}$ | **0.001 ms** | $< 33.0\text{ ms}$ |
| **Spatial Anchoring Invariant** | **FAILED** | **PASS (100% Stable)** | Hard Invariant |

---

## 4. 6-Tier Verification Matrix & Coverage

The full 6-tier E2E verification suite (`run_e2e_verification.py`) executed across all layers with **100% pass rate** (`docs/evidence/s5-extension-ui/s5_e2e_verification_report.json`):

| Tier | Verification Scope | Tested Behavior | Result | Elapsed Time |
| :--- | :--- | :--- | :---: | :---: |
| **Tier A.1** | S2 Frozen ASR Gate | English & Japanese Zipformer accuracy, latency, zero revisions | **PASS** | 6.86s |
| **Tier A.2** | S3 Marian INT8 | 15 unit tests, quality metrics, tokenizer speed | **PASS** | 24.58s |
| **Tier A.3** | S4 Incremental MT | 36 policy & 10 adversarial streaming scenarios | **PASS** | 9.04s |
| **Tier A.4** | S5 Python Unit | Protocol serialization, schema validation, streaming pipeline | **PASS** | 3.21s |
| **Tier A.5** | S5 Node.js DOM | Tests A through J (coalescing, deduplication, finalization) | **PASS** | 0.03s |
| **Tier B** | Packaging & Manifest Contract | Manifest V3, permissions, executable permissions, host discovery | **PASS** | 0.23s |
| **Tier C** | Real Native Messaging Stdio | 8 concrete scenarios (stdio framing, EOF, >1MB, malformed JSON, crash) | **PASS** | 44.39s |
| **Tier D** | Real WebSocket Transport | Connect, disconnect, rapid burst frames, reconnect resiliency | **PASS** | 10.21s |
| **Tier E** | Multi-Resolution Browser Geometry | 1080p, 1440p, theater, 4K, compact (0.0000px anchor shift) | **PASS** | 0.03s |
| **Tier F** | Fault Injection & Fuzzing | Process SIGKILL recovery, reconnect storm, security fuzzing | **PASS** | 11.71s |
| **Tier G.1** | Golden E2E Trace Replay | Audio WAV -> S2 -> S4 -> S5 exact golden event contract | **PASS** | 8.97s |
| **Tier G.2** | Long-Running Memory Soak | Sustained multi-segment streaming (bounded RSS, 0 memory leak) | **PASS** | 34.96s |

---

## 5. End-to-End Latency & Performance Breakdown

```text
[Tab Audio Capture (S1)]  ───────────────► 128ms Chunk Cadence
           │
           ▼
[Zipformer Streaming ASR (S2)] ──────────► TTFT: 121.4 ms | RTF: 0.0787
           │
           ▼
[Incremental Translation (S4)] ──────────► Policy Overhead: 0.029 ms | Marian MT: 43.34 ms
           │
           ▼
[Extension Renderer (S5)] ───────────────► Dispatch Latency: 0.000 ms (p50) / 0.001 ms (p95)
                                           Anchor Displacement: 0.0000 px
```

- Total end-to-end processing per chunk: $\approx 44\text{ ms}$ on 2 CPU threads ($\text{RTF} = 0.1352$, $7.4\times$ faster than realtime).
- Browser UI rendering overhead is negligible ($< 1\text{ microsecond}$ dispatch), introducing zero perceptible latency.

---

## 6. Definition of Done Compliance

- [x] Extension architecture audited and implemented.
- [x] S4 SubtitleState consumed through decoupled `SubtitleStateAdapter`.
- [x] Committed/provisional rendered separately with visual hierarchy.
- [x] Committed text is visually anchored ($\Delta \text{pos} = 0.0\text{ px}$).
- [x] Zero whole-subtitle DOM replacement on provisional updates.
- [x] Stale updates rejected; duplicate states filtered (78 frames).
- [x] Browser frame update coalescing implemented (`requestAnimationFrame`).
- [x] Finalization merges text cleanly.
- [x] Versioned JSON wire protocol `v1.0` implemented.
- [x] Native host manifest registered in Chrome host directory.
- [x] 8 Native Messaging stdio error/failure scenarios verified.
- [x] Real WebSocket transport with reconnect resilience verified.
- [x] Runtime disconnect handled with degraded status indicator.
- [x] Real end-to-end S2 $\to$ S4 $\to$ S5 pipeline verified.
- [x] Multi-resolution browser geometry verified at 0.0000 px across 5 viewports.
- [x] Security fuzzing and process SIGKILL recovery verified.
- [x] Golden E2E audio trace replay verified.
- [x] 15-iteration memory soak test verified (bounded RSS, zero queue growth).
- [x] Frozen S2 regression check passes 100% (0 violations).
- [x] S3 and S4 test suites pass 100%.
- [x] ADR-007 and S5 Research Report created.

---

## 7. Formal 3-Tier Verdict

* **`S5 Unit / Contract = PASS`**
* **`S5 Integration = PASS`**
* **`S5 Real-world E2E = PASS`**

