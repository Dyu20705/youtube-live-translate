# Stage S3 Empirical Research Report: Local Machine Translation Feasibility

**Date:** 2026-09-02  
**Status:** Completed & Empirically Validated  
**Deciders:** Core Engineering Team  
**Evidence Artifact:** [`docs/evidence/s3-local-mt/s3_benchmark_measurements.json`](file:///home/duy/Code/tools/youtube-live-translate/docs/evidence/s3-local-mt/s3_benchmark_measurements.json)  

---

## 1. Executive Summary

Stage S3 empirically evaluated whether local Japanese -> English Machine Translation (MT) is feasible on consumer CPU hardware for translating streaming Automatic Speech Recognition (ASR) outputs emitted by the frozen Stage S2 multilingual Zipformer pipeline.

The benchmark compared two local neural translation architectures under an INT8 quantized CTranslate2 runtime on CPU:
1. **Helsinki-NLP `opus-mt-ja-en` (Marian)**
2. **Meta `nllb-200-distilled-600M`**

### Summary of Empirical Findings

1. **Hard Feasibility Gates:**
   - **Helsinki-NLP Marian INT8 satisfies all hard feasibility gates:** It achieves a median inference latency of **$\text{p50} = 65.73\text{ ms}$** (against the $< 100\text{ ms}$ feasibility threshold), requires **$111.58\text{ MB}$** incremental model RAM overhead (**$514.0\text{ MB}$** peak process RSS), and carries an unrestricted commercial license (Apache 2.0 / CC-BY 4.0).
   - **Meta NLLB-200 INT8 fails the real-time CPU feasibility gates:** It exhibits a median inference latency of **$\text{p50} = 699.61\text{ ms}$** ($\approx 7\times$ above the real-time threshold), requires **$709.42\text{ MB}$** incremental model RAM overhead (**$1231.36\text{ MB}$** peak process RSS), and carries a non-commercial license restriction (CC-BY-NC 4.0).

2. **Quality Metrics vs. Feasibility Boundary:**
   - On realistic S2 ASR outputs, NLLB-200 achieves higher raw quality scores ($\text{BLEU} = 24.14$, $\text{chrF++} = 49.69$, $\text{COMET} = 0.7964$) compared to Marian ($\text{BLEU} = 13.14$, $\text{chrF++} = 36.25$, $\text{COMET} = 0.7685$).
   - Marian is selected as the primary engine because it is the **only evaluated candidate that operates inside the real-time-constrained feasible region** on consumer CPU hardware. NLLB-200 is positioned strictly as a secondary quality/reference engine for offline or asynchronous post-processing.

3. **Streaming Translation Prefix Stability (TPS):**
   - Naive unconstrained re-translation of partial ASR updates yields low prefix stability ($\text{TPS} = 0.2659$ for Marian, $\text{TPS} = 0.3084$ for NLLB) with frequent destructive revisions ($50$ revisions across the test set).
   - This empirically confirms that naive re-translation produces visible subtitle flicker, establishing that **Stage S4 (Incremental Translation & Adaptive Frontier Stabilization)** is architecturally mandatory.

**Gate Decision: `S3 RESULT = GO`**  
- **Primary MT Candidate (Real-Time Hot-Path):** Helsinki-NLP `opus-mt-ja-en` (Marian CTranslate2 INT8).  
- **Secondary Quality/Reference Engine (Offline / Non-Real-Time):** Meta `nllb-200-distilled-600M` (CTranslate2 INT8).

---

## 2. Experimental Setup and Benchmark Scope

### 2.1 Hardware and Runtime Environment
- **Platform:** Linux x86_64, 16 logical cores (8 physical cores), 13.42 GB RAM, Python 3.12.3.
- **MT Runtime:** CTranslate2 v4.8.2 (`device="cpu"`, `compute_type="int8"`, `intra_threads=2`).
- **ASR Engine (Frozen S2 Pipeline):** Sherpa-ONNX v1.13.7 multilingual Zipformer (`ar_en_id_ja_ru_th_vi_zh-2025-02-10`).
- **Evaluation Packages:** `sacrebleu` v2.6.0, `unbabel-comet` v2.2.7 (`Unbabel/wmt22-comet-da`).

### 2.2 Scope and Characterization Disclaimer
This evaluation was conducted as a controlled, fast empirical screening benchmark. The sample size and execution configuration were calibrated to avoid CPU thermal throttling while providing sufficient empirical evidence to resolve architectural engine selection. The measurements provide a concrete engineering baseline for client CPU execution, but do not represent an exhaustive statistical characterization across arbitrary client CPU topologies.

---

## 3. Dataset Construction (Phases 0 and 1)

Input to Stage S3 was generated using authentic Japanese speech recognition hypotheses from the frozen Stage S2 pipeline in addition to clean reference Japanese.

The evaluation manifest ([`manifest.json`](file:///home/duy/Code/tools/youtube-live-translate/poc/s3-local-mt/datasets/manifest.json)) comprises 18 curated items across 5 length buckets:
- **1–10 characters:** Short greetings, confirmations, colloquial expressions (`こんにちは`, `はい、分かりました`, `ありがとうございます`).
- **11–30 characters:** Conversational Japanese, shopping with numbers/currency (`30%オフで1500円`), proper nouns (Nintendo, Shinjuku, YouTube), and authentic S2 audio fixtures (`持ち主とはぐれた傘...` transcribed as `こち主とはぐれた傘...`).
- **31–60 characters:** Travel narratives, compound clauses, technical explanations, weather advisories.
- **61–120 characters:** News broadcasts, livestream gaming commentary, business announcements.
- **>120 characters:** Multi-sentence travel monologues and technical architecture statements.

For each item, 6 deterministic conditions were evaluated ([`partial_variants.json`](file:///home/duy/Code/tools/youtube-live-translate/poc/s3-local-mt/datasets/partial_variants.json)): `FULL`, `UNPUNCTUATED`, `PARTIAL_25`, `PARTIAL_50`, `PARTIAL_75`, `PARTIAL_100` (108 total test conditions).

---

## 4. Latency Distribution and Scaling Analysis (Phases 3 and 4)

### 4.1 Overall MT Latency Distributions

| Model Runtime | Cold Start | p50 | p90 | p95 | p99 | Max | Mean ± Std |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Marian INT8 (2 CPU threads)** | 13.87 ms | **65.73 ms** | 160.36 ms | **180.19 ms** | 197.15 ms | 201.38 ms | 74.16 ± 53.6 ms |
| **NLLB-200 INT8 (2 CPU threads)** | 209.86 ms | **699.61 ms** | 1534.57 ms | **2105.67 ms** | 2145.24 ms | 2155.13 ms | 800.44 ± 567.1 ms |

### 4.2 Phase Breakdown per MT Invocation (Marian INT8)
- **Tokenizer Latency (p50):** $0.16\text{ ms}$ ($< 0.3\%$ of total execution time)
- **CTranslate2 Model Inference (p50):** $65.26\text{ ms}$ ($99.3\%$ of total execution time)
- **Detokenizer Latency (p50):** $0.27\text{ ms}$ ($< 0.4\%$ of total execution time)

### 4.3 Input Length Scaling (Median Latency p50)
| Character Bucket | Marian INT8 (p50) | NLLB-200 INT8 (p50) | Scaling Factor (NLLB / Marian) |
| :--- | :---: | :---: | :---: |
| **1–10 chars** | **18.89 ms** | 243.05 ms | $12.9\times$ |
| **11–30 chars** | **43.31 ms** | 402.94 ms | $9.3\times$ |
| **31–60 chars** | **75.43 ms** | 797.17 ms | $10.6\times$ |
| **61–120 chars** | **100.67 ms** | 1186.66 ms | $11.8\times$ |
| **> 120 chars** | **188.92 ms** | 2126.03 ms | $11.3\times$ |

---

## 5. Translation Quality Evaluation (Phase 5)

Quality was evaluated across two paths:
- **Path A (Clean Japanese):** `reference_ja -> Model -> English`
- **Path B (Realistic S2 ASR):** `asr_ja -> Model -> English` (Primary evaluation path)

| Evaluation Path | Metric | Marian INT8 | NLLB-200 INT8 | Delta |
| :--- | :--- | :---: | :---: | :---: |
| **Path A (Clean Reference)** | SacreBLEU | 18.54 | **26.63** | $+8.09$ (NLLB) |
| | chrF++ | 46.47 | **52.40** | $+5.93$ (NLLB) |
| | COMET (`wmt22-da`) | 0.8337 | **0.8410** | $+0.0073$ (NLLB) |
| **Path B (Realistic S2 ASR)** | SacreBLEU | 13.14 | **24.14** | $+11.00$ (NLLB) |
| | chrF++ | 36.25 | **49.69** | $+13.44$ (NLLB) |
| | COMET (`wmt22-da`) | 0.7685 | **0.7964** | $+0.0279$ (NLLB) |
| **ASR Degradation Impact** | BLEU Delta ($\text{Path A} \to \text{Path B}$) | $-5.40$ | $-2.49$ | Marian more sensitive |
| | chrF++ Delta ($\text{Path A} \to \text{Path B}$) | $-10.22$ | $-2.71$ | Marian more sensitive |

---

## 6. Partial and Unpunctuated Robustness (Phases 6 and 7)

### 6.1 Translation Prefix Stability (TPS)
We measured stability across consecutive partial slices ($25\% \to 50\% \to 75\% \to 100\%$):

$$\text{TPS} = \frac{\text{len}(\text{LCP}(\text{prev\_tokens}, \text{curr\_tokens}))}{\text{len}(\text{prev\_tokens})}$$

| Streaming Stability Dimension | Marian INT8 | NLLB-200 INT8 | Architectural Consequence |
| :--- | :---: | :---: | :--- |
| **Average TPS** | **0.2659** | **0.3084** | Early tokens are mutated during unconstrained full decoding |
| **Destructive Revisions** | 50 | 46 | Causes UI subtitle flicker if directly displayed |
| **Complete Rewrites** | 12 | 9 | Driven by Japanese SOV to English SVO structural inversion |
| **Average Revision Size** | 3.4 tokens | 3.1 tokens | Average tokens modified per destructive revision |

---

## 7. Re-translation Compute Load (Phase 8)

| Dimension | Marian INT8 | NLLB-200 INT8 | Feasibility Assessment |
| :--- | :---: | :---: | :--- |
| **Simulated MT Calls / Utterance** | 4.0 calls | 4.0 calls | 4 chunk hypothesis updates |
| **Total MT CPU Time / Utterance** | **185.4 ms** | **2,480.2 ms** | Marian completes within utterance duration |
| **Redundant Chars Translated** | 124.5% | 124.5% | Naive re-translation overhead |
| **Naive Streaming Feasible on CPU** | **YES** | **NO** | Marian CPU load $< 15\%$; NLLB saturates cores |

---

## 8. Pipeline Step Latency Breakdown (Phase 9)

In the simulated streaming replay (`ja_conversational.wav`, 5.2s audio duration), we evaluated the per-chunk step processing latency through `Audio Chunk -> Zipformer ASR Step -> MT Translation Step -> Subtitle Hypothesis`.

### Step Latency Breakdown per Emitted Partial
- **ASR Step Processing Latency (p50):** $18.50\text{ ms}$
- **IPC / Glue Overhead:** $< 0.05\text{ ms}$
- **Marian MT Translation Latency (p50):** $46.90\text{ ms}$
- **Per-Chunk Pipeline Step Latency (p50):** **$65.45\text{ ms}$** (p95 = $148.20\text{ ms}$)
- **Pipeline Real-Time Factor (RTF):** **$0.082$** ($12\times$ faster than realtime)

*Note on Acoustic Latency:* Per-chunk pipeline step latency ($65.45\text{ ms}$) measures computational delay once an audio chunk is received. Full acoustic speech-to-subtitle delay from utterance onset also incorporates acoustic buffering and ASR Time-To-First-Transcript ($123.5 - 133.6\text{ ms}$ in S2), yielding an estimated speech-onset-to-first-subtitle delay of $\approx 190 - 200\text{ ms}$.

---

## 9. Resource and Memory Benchmarks (Phase 10)

Memory was measured by tracking process resident set size (RSS) across baseline, post-load, and peak execution states:

| Resource Dimension | Marian INT8 | NLLB-200 INT8 |
| :--- | :---: | :---: |
| **Model Size on Disk** | **77.97 MB** | 634.82 MB |
| **Model Initialization Time** | **426.06 ms** | 1010.65 ms |
| **Process Baseline RSS (pre-load)** | 390.61 MB | 514.01 MB |
| **Process RSS (post-load)** | 502.19 MB | 1223.43 MB |
| **Incremental Model RAM Overhead** | **111.58 MB** | 709.42 MB |
| **Peak Process RSS (under inference)** | **514.00 MB** | 1231.36 MB |

---

## 10. Licensing and Deployment Audit (Phase 11)

| Criterion | Helsinki-NLP `opus-mt-ja-en` | Meta `nllb-200-distilled-600M` |
| :--- | :--- | :--- |
| **License** | **Apache 2.0 / CC-BY 4.0** | **CC-BY-NC 4.0** |
| **Commercial Distribution** | **Allowed (Permissive)** | **Prohibited (Non-commercial only)** |
| **Redistribution Conditions** | Attribution required | Attribution required + non-commercial |
| **Packaging Suitability** | **Approved:** Compact $78\text{MB}$ weights embeddable in native host | **Restricted:** Large $635\text{MB}$ binary, non-commercial restriction |

---

## 11. Decision Methodology & Comparison Matrix (Phases 13 and 14)

### 11.1 Hard Feasibility Gates vs. Quality Metrics

```
                     HARD FEASIBILITY GATES
  ┌─────────────────────────────────────────────────────────┐
  │  1. Latency: MT p50 < 100 ms                           │
  │  2. Memory: Process Peak RSS < 1000 MB                 │
  │  3. Deployment: Lightweight binary (< 150 MB)          │
  │  4. Licensing: Permissive commercial redistribution    │
  └────────────────────────────┬────────────────────────────┘
                               │
               Passes All Hard Feasibility Gates?
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
             [ YES ]                       [ NO ]
      Helsinki-NLP Marian INT8       Meta NLLB-200 600M INT8
       (Enters Quality Eval)       (Excluded from Real-Time Path)
                │                             │
                ▼                             ▼
     SELECTED AS PRIMARY ENGINE    RETAINED AS REFERENCE / OFFLINE
```

### 11.2 Evaluation Matrix

| Dimension | Classification | Helsinki-NLP Marian INT8 | Meta NLLB-200 INT8 | Gate Threshold | Feasibility Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **MT Latency (p50)** | Hard Gate | **65.73 ms** | 699.61 ms | $< 100\text{ ms}$ | **Marian PASS / NLLB FAIL** |
| **MT Latency (p95)** | Hard Gate | **180.19 ms** | 2105.67 ms | $< 200\text{ ms}$ | **Marian PASS / NLLB FAIL** |
| **Peak Process RSS** | Hard Gate | **514.00 MB** | 1231.36 MB | $< 1000\text{ MB}$ | **Marian PASS / NLLB FAIL** |
| **Model Size on Disk**| Hard Gate | **77.97 MB** | 634.82 MB | $< 150\text{ MB}$ | **Marian PASS / NLLB FAIL** |
| **Commercial License**| Hard Gate | **Apache 2.0 / CC-BY** | CC-BY-NC 4.0 | Permissive | **Marian PASS / NLLB FAIL** |
| **BLEU (Realistic ASR)**| Quality Metric| 13.14 | **24.14** | Baseline | NLLB $+11.00$ |
| **chrF++ (Realistic ASR)**| Quality Metric| 36.25 | **49.69** | Baseline | NLLB $+13.44$ |
| **COMET (Realistic ASR)**| Quality Metric| 0.7685 | **0.7964** | Baseline | NLLB $+0.0279$ |
| **Prefix Stability (TPS)**| Quality Metric| 0.2659 | 0.3084 | Baseline | Both require Stage S4 |
| **Per-Chunk Step Latency**| Realtime Test | **65.45 ms** | 485.42 ms | $< 150\text{ ms}$ | **Marian PASS / NLLB FAIL** |

---

## 12. Final Recommendation

### Outcome: `S3 RESULT = GO`

1. **Primary Real-Time Hot-Path Engine:**  
   **Helsinki-NLP `opus-mt-ja-en` (Marian CTranslate2 INT8)**  
   *Justification:* Marian is the only evaluated model that satisfies all hard real-time feasibility gates ($\text{p50} = 65.73\text{ ms}$, $78\text{ MB}$ disk footprint, $514\text{ MB}$ peak RSS, permissive licensing).

2. **Secondary Quality / Reference Engine:**  
   **Meta `nllb-200-distilled-600M` (CTranslate2 INT8)**  
   *Justification:* Retained strictly as an offline quality benchmark or asynchronous cold-path engine where real-time constraints do not apply.

---

## 13. Verification of Claims

| Claim | Verification Status | Empirical Grounding |
| :--- | :---: | :--- |
| Local JA -> EN MT is feasible on CPU with $\text{p50} < 100\text{ ms}$ | **VERIFIED** | Marian INT8 measured at $\text{p50} = 65.73\text{ ms}$. |
| S2 streaming ASR can feed directly into local MT pipeline | **VERIFIED** | Per-chunk pipeline step latency measured at $\text{p50} = 65.45\text{ ms}$. |
| NLLB-200 600M INT8 is suitable for real-time CPU streaming | **FAILED** | Measured $\text{p50} = 699.61\text{ ms}$ on CPU, failing real-time budget by $\approx 7\times$. |
| Naive re-translation produces stable streaming prefixes | **FAILED** | Measured $\text{TPS} = 0.2659$ ($50$ revisions), proving Stage S4 stabilization is required. |
| Stage S2 baseline performance preserved without regressions | **VERIFIED** | Stage S2 regression gate passed with zero violations. |
