# ADR-006: Incremental Translation Policy & Adaptive Frontier Stabilization

**Status:** Accepted  
**Date:** 2026-09-02  
**Deciders:** Core Engineering Team  
**Consulted:** Stage S4 Empirical Research Report ([`docs/research/s4-incremental-translation.md`](file:///home/duy/Code/tools/youtube-live-translate/docs/research/s4-incremental-translation.md))  

---

## 1. Context and Problem Statement

In Stage S3, we verified that local INT8 Marian Machine Translation (MT) executes with median latency $\text{p50} = 65.73\text{ ms}$, operating well within the real-time client CPU budget. However, S3 also revealed a fundamental streaming policy challenge: **naive full retranslation on each partial ASR update results in an unstable prefix ($\text{TPS} \approx 0.25$, $50$ destructive revisions per 18 utterances)** due to word-order differences between Japanese (SOV) and English (SVO).

Stage S4 was charged with implementing a deterministic, lightweight, stateful streaming translation layer between frozen Stage S2 ASR and Stage S3 MT to:
1. Provide a formal state abstraction distinguishing an **immutable committed prefix** from a **revisable provisional suffix**.
2. Enforce $\text{committed\_prefix\_revision\_count} = 0$ as a strict correctness invariant.
3. Quantify policy overhead ($\text{p50} < 5\text{ ms}$, $\text{p95} < 15\text{ ms}$) without adding neural models or LLMs.
4. Optimize MT compute via input deduplication.

---

## 2. Decision Methodology: Separation of Stability Concepts

The research audit identified that "stability" cannot be reduced to a single TPS number. Stage S4 explicitly separates three distinct stability concepts:

* **Concept A (Committed-Prefix Stability):** Does already committed text ever mutate or shrink? (Target: strictly 0).
* **Concept B (Provisional Suffix Revision):** How frequently does the uncommitted tail update? (Expected to revise as context grows).
* **Concept C (Whole-Display Destructive Revision):** How frequently does the unified display text (`committed + provisional`) change its prefix? (Comparable to S3 baseline).

```text
[ASR Partial Updates]
         │
         ▼
[1. Input Deduplication] ──(Unchanged text)──► [Return Previous State]
         │ (Changed text)
         ▼
[2. S3 Marian INT8 Translation] ──► [Candidate Translation Hypothesis]
         │
         ▼
[3. Local Agreement Tracking (K consecutive matching hypotheses)]
         │
         ▼
[4. Adaptive Frontier Controller]
      ├── Protected Unstable Suffix Buffer (W=2 tokens)
      ├── Clause / Punctuation Boundary Acceleration (,.!?)
      ├── Japanese Sentence-Final Marker Detection (。！？)
      └── Endpoint / Segment Finalization Flush
         │
         ▼
[5. SubtitleState: Immutable Committed Prefix + Revisable Provisional Suffix]
```

---

## 3. Explicit Architectural Contract: What S4 Guarantees and What It Does Not

To prevent architectural ambiguity in downstream stages (S5/S6), the formal boundaries of Stage S4 are defined as follows:

### S4 Guarantees
* **Committed-Prefix Immutability:** Once a token prefix is promoted to `committed_text` within an active segment, it will never mutate, delete, or re-order ($\text{committed\_prefix\_revision\_count} = 0$).
* **Bounded Revision Surface:** All temporal instability is strictly confined to `provisional_text`.
* **Deterministic State Transitions:** State lifecycle transitions (`RESET` $\to$ `ACTIVE` $\to$ `ENDPOINT` $\to$ `FLUSHED`) are 100% reproducible and model-free.
* **Compute Optimization:** Identical ASR partial updates bypass redundant MT inference ($82.7\%$ reduction on streaming audio).
* **Sub-Millisecond Policy Overhead:** Policy execution consumes $< 0.1\%$ of the per-chunk CPU time budget ($\text{p50} = 0.029\text{ ms}$, $\text{p95} = 0.050\text{ ms}$).

### S4 Does NOT Guarantee
* **Zero Provisional Revisions:** Provisional tail text updates frequently ($\text{provisional\_revision\_rate} \approx 0.98$) as new acoustic tokens arrive.
* **Zero Whole-Display Textual Changes:** Unified display text (`committed + provisional`) exhibits 50 destructive revisions across 18 utterances—equivalent to the S3 naive baseline.
* **Human-Perceived Flicker Elimination:** Flicker elimination cannot be solved by the backend policy alone; it requires anchored visual differentiation in the UI renderer.
* **Semantic Correctness After Arbitrary Late ASR Corrections:** If upstream ASR rewrites an earlier source word after its translation was already committed, the committed English text remains immutable.

---

## 4. Conflict Semantics & Fundamental UX Trade-Off

When an upstream ASR engine rewrites an earlier source token after its translation has already been committed:

```text
ASR Step t:   今日東京... ──► Committed EN: "Today in Tokyo"
ASR Step t+1: 昨日東京... (ASR corrects 'Today' -> 'Yesterday')
```

The system faces a fundamental architectural dilemma:
- **Prioritize Stability ($\text{Stability} \uparrow$, $\text{Fidelity} \downarrow$):** Keep committed English prefix immutable ("Today in Tokyo"), record a commit conflict, and adapt provisional tail.
- **Prioritize Fidelity ($\text{Fidelity} \uparrow$, $\text{Stability} \downarrow$):** Rewrite the entire subtitle line ("Yesterday in Tokyo"), destroying visual stability and causing severe flicker.

### Architectural Rule
> **Committed output is a temporal UX guarantee, not a guarantee that already-committed text is semantically correct under arbitrary later ASR corrections.**

Stage S4 chooses **Stability Over Late Retroactive Correction** within active segments.

---

## 5. Empirical Evaluation Summary

| Evaluation Dimension | Metric Type | S3 Naive Baseline | S4 Candidate ($K=1$) | S4 Candidate ($K=2$)* | S4 Candidate ($K=3$) | Target Threshold |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. Committed Prefix Revisions** | Hard Invariant | N/A | **0** (PASS) | **0** (PASS) | **0** (PASS) | $= 0$ |
| **Commit Conflicts Recorded** | Invariant Telemetry | N/A | 32 (Severe) | **3** (Minimal) | **0** (Zero) | Low |
| **B. Provisional Revision Rate** | Tail Dynamics | N/A | 0.94 | **0.98** | 0.98 | Telemetry |
| **C. Display Destructive Revisions**| Visual Metric | 50 | **31** | 50 | 50 | $\le$ Baseline |
| **C. Display Complete Rewrites** | Visual Metric | 23 | **2** | 22 | 22 | $\le$ Baseline |
| **C. Display TPS (Prefix Agreement)**| Reference TPS | 0.2460 | **0.7181** | 0.2718 | 0.2468 | Baseline |
| **Frontier Advancements** | Telemetry | N/A | 19 | **31** | 26 | Progressive |
| **Avg Commit Delay (steps)** | Latency Metric | 0.00 | 0.11 | **2.06** | 2.56 | Bounded |
| **p95 Commit Delay (steps)** | Latency Metric | 0.00 | 0.30 | **3.00** | 3.00 | Bounded |
| **Policy Overhead (p50)** | Hard Gate | 0.00 ms | **0.032 ms** | **0.029 ms** | **0.029 ms** | $< 5.0\text{ ms}$ |
| **Policy Overhead (p95)** | Hard Gate | 0.00 ms | **0.043 ms** | **0.050 ms** | **0.043 ms** | $< 15.0\text{ ms}$ |
| **Total Step Latency (p50)**| System Metric | 44.86 ms | 42.98 ms | **43.34 ms** | 43.57 ms | $< 100\text{ ms}$ |
| **Final Quality (chrF++)** | Quality Metric | Baseline | 24.32 (Degraded) | **37.53** (Preserved)| **38.29** (Preserved)| Comparable |
| **Audio Replay MT Reduction**| Efficiency | 0.0% | - | **82.7%** | - | $> 0\%$ |

*\* Note: $K=2$ represents the empirical multi-objective choice among $K \in \{1, 2, 3\}$. It is not a mathematically proven global Pareto optimum.*

---

## 6. Decision Outcome

**Chosen Policy:** **Option 3 (S4 Local Agreement $K=2$, Protected Buffer $W=2$)** is adopted as the operational default.

### Rationale:
- $K=2$ achieves the best empirical balance among tested parameters: zero committed revisions, low conflict rate ($3$ conflicts), preserved translation quality ($\text{chrF++} = 37.53$), and progressive frontier advancement ($31$ steps).
- $K=1$ is rejected due to premature commitment leading to 32 conflicts and $-13.21$ chrF++ quality loss.
- $K=3$ is preserved as a conservative zero-conflict alternative when commit latency is secondary.

---

## 7. Downstream Contract for Stage S5 (UI Renderer)

To solve perceptual flicker without degrading MT quality, Stage S5 must adhere to an **Anchored Layout & Visual Hierarchy Contract**:

```text
┌───────────────────────────────────────────────────────────────┐
│                      SUBTITLE CONTAINER                       │
│                                                               │
│   [COMMITTED PREFIX]               [PROVISIONAL SUFFIX]       │
│   • Solid opacity (100%)           • Dimmed opacity (60-70%)  │
│   • Standard font weight           • Italic font style        │
│   • Anchored text baseline         • Floating tail container  │
│   (Zero visual movement)           (Permitted to update)      │
└───────────────────────────────────────────────────────────────┘
```

Stage S5 will serve as the empirical testbed to evaluate whether this visual contract eliminates human-perceived subtitle flicker during live streaming video playback.
