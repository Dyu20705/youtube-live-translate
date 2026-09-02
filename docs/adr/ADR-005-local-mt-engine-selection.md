# ADR-005: Selection of Local Machine Translation (MT) Engine and Model Family

**Status:** Accepted  
**Date:** 2026-09-02  
**Deciders:** Core Engineering Team  
**Consulted:** Stage S3 Empirical Research Report ([`docs/research/s3-local-mt.md`](file:///home/duy/Code/tools/youtube-live-translate/docs/research/s3-local-mt.md))  

---

## 1. Context and Problem Statement

`youtube-live-translate` requires local Japanese -> English Machine Translation (MT) to transform streaming speech recognition hypotheses emitted by the Stage S2 Zipformer pipeline into English subtitles in real time.

The engineering challenge requires selecting an MT architecture that satisfies strict operational constraints on client CPU hardware:
1. **Real-Time Latency:** Translation must execute fast enough ($\text{p50} < 100\text{ ms}$) to keep pace with live streaming speech.
2. **Resource Feasibility:** Memory and compute footprint must co-exist with streaming ASR on consumer laptops without thermal saturation.
3. **Packaging and Distribution:** Model binary must be compact enough for desktop extension native host delivery.
4. **Licensing Compliance:** Model distribution must be permitted for open-source and commercial use.

---

## 2. Decision Methodology: Hard Feasibility Gates vs. Quality Metrics

We distinguish **Hard Feasibility Gates** (binary go/no-go constraints) from **Translation Quality Metrics**:

### Hard Feasibility Gates
* **Latency Gate:** $\text{MT p50} < 100\text{ ms}$ on 2 CPU threads.
* **Memory Gate:** Peak process $\text{RSS} < 1000\text{ MB}$.
* **Packaging Gate:** Weight footprint $< 150\text{ MB}$.
* **Licensing Gate:** Permissive commercial redistribution (no non-commercial restriction).

### Translation Quality Metrics
* **SacreBLEU**, **chrF++**, and **COMET (`wmt22-da`)** evaluated on realistic imperfect ASR output.

---

## 3. Considered Options

* **Option 1: Helsinki-NLP `opus-mt-ja-en` (Marian / OPUS-MT) in CTranslate2 INT8**
* **Option 2: Meta `nllb-200-distilled-600M` in CTranslate2 INT8**
* **Option 3: Cloud Translation APIs** — *Rejected per Architecture Invariant I3 (Zero mandatory external cloud dependency)*.

---

## 4. Empirical Evaluation Summary (Stage S3 Benchmark)

| Evaluation Dimension | Metric Type | Helsinki-NLP Marian INT8 | Meta NLLB-200 INT8 | Feasibility Threshold |
| :--- | :---: | :---: | :---: | :---: |
| **MT Latency (p50)** | Hard Gate | **65.73 ms** (PASS) | 699.61 ms (FAIL) | $< 100\text{ ms}$ |
| **MT Latency (p95)** | Hard Gate | **180.19 ms** (PASS) | 2105.67 ms (FAIL) | $< 200\text{ ms}$ |
| **Model Disk Size** | Hard Gate | **77.97 MB** (PASS) | 634.82 MB (FAIL) | $< 150\text{ MB}$ |
| **Baseline Process RSS** | Telemetry | 390.61 MB | 514.01 MB | - |
| **Incremental Model RAM** | Telemetry | **111.58 MB** | 709.42 MB | - |
| **Peak Process RSS** | Hard Gate | **514.00 MB** (PASS) | 1231.36 MB (FAIL) | $< 1000\text{ MB}$ |
| **Commercial License** | Hard Gate | **Apache 2.0 / CC-BY** (PASS) | CC-BY-NC 4.0 (FAIL) | Permissive |
| **BLEU (Realistic S2 ASR)** | Quality Metric | 13.14 | **24.14** | Baseline |
| **chrF++ (Realistic S2 ASR)**| Quality Metric | 36.25 | **49.69** | Baseline |
| **COMET (Realistic S2 ASR)** | Quality Metric | 0.7685 | **0.7964** | Baseline |
| **Prefix Stability (TPS)** | Quality Metric | 0.2659 | 0.3084 | Baseline |
| **Per-Chunk Step Latency** | Pipeline Test | **65.45 ms** | 485.42 ms | $< 150\text{ ms}$ |

*Note on Benchmark Scope:* The empirical evaluation was conducted as a fast, resource-constrained screening benchmark. It provides conclusive evidence for filtering candidates into the real-time feasible region, though it is not an exhaustive multi-hardware characterization.

---

## 5. Decision Outcome

**Chosen Candidate:** **Option 1 (Helsinki-NLP `opus-mt-ja-en` in CTranslate2 INT8)** is selected as the **Primary Real-Time Hot-Path Engine**.

**Secondary Role:** **Option 2 (Meta `nllb-200-distilled-600M`)** is designated as a **Secondary Quality / Reference Engine** (for offline post-stream export or asynchronous non-real-time quality validation only).

### 5.1 Rationale
1. **Real-Time Feasibility Boundary:** Marian INT8 is the only candidate that passes all hard feasibility gates on CPU. NLLB-200 exhibits a median latency of $\sim 700\text{ ms}$ and a peak latency of $> 2000\text{ ms}$, which causes immediate queue accumulation and cannot track live speech.
2. **Resource Footprint:** Marian adds $111.58\text{ MB}$ of incremental RAM ($514.0\text{ MB}$ peak process RSS) and occupies $78\text{ MB}$ disk space, allowing clean packaging inside a native host application.
3. **Licensing Compliance:** Marian's Apache 2.0 / CC-BY license allows unrestricted commercial and open-source distribution, unlike Meta's non-commercial CC-BY-NC 4.0 license.
4. **Selection Principle:** Marian is chosen because it is the superior candidate **inside the feasible real-time operational envelope**, not because it achieves higher absolute translation quality than NLLB-200.

---

## 6. Consequences & Next Steps

### Positive
- Sub-100ms MT latency budget is verified ($\text{p50} = 65.73\text{ ms}$).
- Per-chunk pipeline step latency (`Audio chunk -> ASR partial -> MT partial`) is verified at $\text{p50} = 65.45\text{ ms}$ ($\text{p95} = 148.20\text{ ms}$) with a real-time factor of $0.082$.
- Model weights ($78\text{ MB}$) can be embedded or fetched dynamically with low overhead.

### Trade-offs & Mitigations
- Marian's translation quality on complex sentences is lower than 600M-parameter models ($13.14$ vs $24.14$ BLEU on ASR output).
- *Mitigation:* Downstream context intelligence (Stage S5) and dynamic terminology glossaries will support the lightweight engine.

### Immediate Requirement for Stage S4
The low raw Translation Prefix Stability ($\text{TPS} = 0.2659$, $50$ destructive revisions) demonstrates that unconstrained re-translation produces subtitle flicker. Work must immediately proceed to **Stage S4: Incremental Translation & Adaptive Frontier Stabilization (Wait-$k$ / Local Agreement)**.
