# Stage S4 Empirical Research Report: Incremental Translation & Adaptive Frontier Stabilization

**Date:** 2026-09-02
**Status:** Completed & Empirically Audited (`S4 Functional / Contract = PASS`, `S4 Perceptual UX = OPEN`)
**Deciders:** Core Engineering Team
**Evidence Artifact:** [`docs/evidence/s4-incremental-translation/s4_benchmark_measurements.json`](file:///home/duy/Code/tools/youtube-live-translate/docs/evidence/s4-incremental-translation/s4_benchmark_measurements.json)

---

## 1. Executive Summary

Stage S4 implemented and empirically audited a deterministic stateful streaming translation layer bridging frozen Stage S2 multilingual Zipformer ASR with Stage S3 Marian CTranslate2 INT8 MT.

### Empirical Verdict Breakdown
```text
S4 Functional Contract:       PASS (100% compliant)
S4 Resource/Latency:          PASS (p50 = 0.029 ms policy overhead)
S4 State Safety:              PASS (0 committed prefix revisions)
S4 Empirical Stability:       PARTIAL (Structural stability verified, raw display baseline-equivalent)
S4 Perceptual UX:             OPEN (Handed off to Stage S5 UI anchored rendering)
```

---

## 2. Explicit Guarantees and Boundaries

### What Stage S4 Guarantees
- **Committed-Prefix Immutability:** Once promoted to `committed_text` within an active segment, output never mutates ($\text{committed prefix revisions} = 0$).
- **Bounded Revision Surface:** All temporal mutability is confined to `provisional_text`.
- **Deterministic State Lifecycle:** Clean transitions (`RESET` $\to$ `ACTIVE` $\to$ `ENDPOINT` $\to$ `FLUSHED`).
- **Input Deduplication:** Skips redundant MT calls on identical streaming partials ($82.7\%$ call reduction on audio).
- **Sub-Millisecond Policy Overhead:** Measured $\text{p50} = 0.029\text{ ms}$, $\text{p95} = 0.050\text{ ms}$ on 2 CPU threads.

### What Stage S4 Does NOT Guarantee
- **Zero Provisional Revisions:** Provisional tail updates frequently ($\text{provisional revision rate} \approx 0.98$) as acoustic tokens accumulate.
- **Zero Whole-Display Textual Changes:** Raw concatenated display text exhibits 50 destructive revisions across 18 items (equal to S3 baseline).
- **Human-Perceived Flicker Elimination:** Flicker elimination cannot be achieved by MT policy alone; it requires anchored visual differentiation in Stage S5 UI.
- **Semantic Correctness After Arbitrary Late ASR Corrections:** If upstream ASR rewrites an earlier word after commit, committed English remains frozen.

---

## 3. Conflict Semantics & Fundamental UX Trade-Off

When upstream ASR rewrites an earlier source word after its English translation has already been committed:

```text
ASR Step t:   今日東京... ──► Committed EN: "Today in Tokyo"
ASR Step t+1: 昨日東京... (ASR corrects 'Today' -> 'Yesterday')
```

The system faces a fundamental architectural dilemma:
- **Prioritize Stability ($\text{Stability} \uparrow$, $\text{Fidelity} \downarrow$):** Keep committed English prefix immutable ("Today in Tokyo"), record a commit conflict, and adapt provisional tail.
- **Prioritize Fidelity ($\text{Fidelity} \uparrow$, $\text{Stability} \downarrow$):** Rewrite the entire subtitle line ("Yesterday in Tokyo"), destroying visual stability and causing severe flicker.

### Architectural Invariant
> **Committed output is a temporal UX guarantee, not a guarantee that already-committed text is semantically correct under arbitrary later ASR corrections.**

Stage S4 chooses **Stability Over Late Retroactive Correction** within active segments.

---

## 4. Empirical Benchmark Comparison

### 4.1 Comparative Evaluation Table (18 Items / 108 Variants)

| Metric | S3 Naive Baseline | S4 ($K=1$) | S4 ($K=2$, Empirical Choice)* | S4 ($K=3$) | Target / Limit |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **A. Committed Prefix Revisions** | N/A | **0** | **0** | **0** | $= 0$ (Hard Invariant) |
| **Commit Conflicts Recorded** | N/A | 32 (Severe) | **3** (Minimal) | **0** (Zero) | Minimal |
| **B. Provisional Revisions (Count)**| N/A | 51 | **53** | 53 | Telemetry |
| **B. Provisional Revision Rate** | N/A | 0.94 | **0.98** | 0.98 | Telemetry |
| **C. Display Destructive Revisions**| 50 | **31** | 50 | 50 | $\le$ Baseline |
| **C. Display Complete Rewrites** | 23 | **2** | 22 | 22 | $\le$ Baseline |
| **C. Display TPS (Prefix Agreement)**| 0.2460 | **0.7181** | 0.2718 | 0.2468 | Baseline |
| **Frontier Advancements** | N/A | 19 | **31** | 26 | Progressive |
| **Avg Commit Delay (steps)** | 0.00 | 0.11 | **2.06** | 2.56 | Bounded |
| **p95 Commit Delay (steps)** | 0.00 | 0.30 | **3.00** | 3.00 | Bounded |
| **Policy Overhead p50 (ms)** | 0.000 | **0.032** | **0.029** | **0.029** | $< 5.0\text{ ms}$ |
| **Policy Overhead p95 (ms)** | 0.000 | **0.043** | **0.050** | **0.043** | $< 15.0\text{ ms}$ |
| **Total Step Latency p50 (ms)** | 44.86 | 42.98 | **43.34** | 43.57 | $< 100\text{ ms}$ |
| **Final Quality (chrF++)** | Baseline | 24.32 (Degraded) | **37.53** (Preserved) | **38.29** (Preserved) | Reference |

*\* Note: $K=2$ is the empirical sweep choice among $\{1, 2, 3\}$. It is not a mathematically proven global Pareto optimum.*

---

## 5. Live Audio Streaming Replay & Compute Efficiency

On continuous streaming audio replay (`ja_conversational.wav`, 13.96s duration, 109 chunks):

- **Audio Duration:** $13.96\text{ s}$
- **Pipeline Wall-Clock Time:** $1.89\text{ s}$
- **Pipeline Real-Time Factor (RTF):** **$0.1352$** ($7.4\times$ faster than realtime on 2 CPU threads)
- **Audio Chunks / ASR Updates:** 109
- **MT Invocations Incurred:** 19 calls
- **MT Calls Saved via Deduplication:** 90 calls
- **MT Call Reduction Ratio:** **$82.7\%$**
- **Committed Prefix Revisions:** **$0$**
- **Policy Overhead Latency (p50):** **$0.002\text{ ms}$**

---

## 6. Adversarial Fixture Validation (10 Scenarios)

The test suite in [`test_adversarial_fixtures.py`](file:///home/duy/Code/tools/youtube-live-translate/poc/s4-incremental-translation/tests/test_adversarial_fixtures.py) validated all 10 adversarial streaming scenarios (clause-final inversions, late particles, question punctuation, ASR source corrections, insertions, deletions, middle rewrites, duplicate frames, endpoint flushes, multi-segment isolation).

---

## 7. Downstream Contract for Stage S5 (UI Renderer)

Stage S5 must implement an **Anchored Layout & Stable Rendering Contract**:
1. **Committed Text:** Rendered in solid 100% opacity with an anchored baseline/container so it never shifts or jitters on screen.
2. **Provisional Text:** Rendered in dimmed 60-70% opacity and italic style in a secondary tail container.
3. **No Layout Reflow:** Revisions to provisional text must not cause the preceding committed subtitle line to re-wrap or animate abruptly.

---

## 8. Final Stage S4 Gate Verdict

```text
S0 — Architecture Demonstrator: FROZEN
S1 — YouTube Audio Capture PoC: PASS
S2 — Local Streaming ASR:       FROZEN
S3 — Local Machine Translation: PASS
S4 — Incremental Translation:   PASS (Functional / Contract)
S5 — Extension UI & Native Host:READY
```
