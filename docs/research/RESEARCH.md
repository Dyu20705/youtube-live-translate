# Research Index & Scientific Synthesis Map

> **Project:** `youtube-live-translater`
> **Status:** Living Master Research Index & Synthesis Map
> **Date:** September 2026
> **Purpose:** Provide an exhaustive, organized knowledge map linking theoretical speech translation literature, empirical stage findings (S0–S5), and production architecture decisions.

---

## 1. Executive Research Index

The research backing `youtube-live-translate` is structured across dedicated stage reports, risk registers, and architectural decision records:

```text
docs/research/
├── RESEARCH.md                      # [THIS FILE] Master research index & scientific synthesis
├── Caution.md                       # Risk register, epistemic guardrails & caution baseline
├── s0-architecture.md               # S0 Architecture demonstrator & freeze rationale
├── s1-audio-capture.md              # S1 Manifest V3 tab audio capture & AudioWorklet resampling
├── s2-streaming-asr.md              # S2 Streaming ASR feasibility (Sherpa-ONNX vs Whisper)
├── s3-local-mt.md                   # S3 Local MT runtime selection (Marian vs NLLB INT8)
├── s4-incremental-translation.md    # S4 Incremental translation policy (Local Agreement K=2, W=2)
└── s5-extension-ui-native-host.md   # S5 Extension UI, anchored rendering & native host bridge
```

### Stage Research Reports & Architectural Decision Records

| Stage | Topic | Research Report | Key Architectural Decision | Status |
| :--- | :--- | :--- | :--- | :---: |
| **S0** | Architecture Demonstrator | [`s0-architecture.md`](s0-architecture.md) | [`ADR-000`](../adr/ADR-000-evidence-policy-and-s0-freeze.md) (Evidence Policy & Freeze) | `FROZEN` |
| **S1** | Audio Capture & Resampling | [`s1-audio-capture.md`](s1-audio-capture.md) | [`ADR-001`](../adr/ADR-001-manifest-v3-tab-audio-capture.md), [`ADR-002`](../adr/ADR-002-realtime-audio-resampling-contract.md) | `PASS` |
| **S2** | Streaming Local ASR | [`s2-streaming-asr.md`](s2-streaming-asr.md) | [`ADR-003`](../adr/ADR-003-streaming-asr-engine-selection.md), [`ADR-004`](../adr/ADR-004-s2-performance-contract.md) | `FROZEN` |
| **S3** | Local Machine Translation | [`s3-local-mt.md`](s3-local-mt.md) | [`ADR-005`](../adr/ADR-005-local-mt-engine-selection.md) (Marian INT8) | `PASS` |
| **S4** | Incremental MT Frontier | [`s4-incremental-translation.md`](s4-incremental-translation.md) | [`ADR-006`](../adr/ADR-006-incremental-translation-frontier.md) (Local Agreement) | `PASS` |
| **S5** | Anchored Presentation & Host | [`s5-extension-ui-native-host.md`](s5-extension-ui-native-host.md) | [`ADR-007`](../adr/ADR-007-extension-renderer-and-native-host-integration.md) (Anchored UI) | `PASS` |

---

## 2. Core Research Thesis

`youtube-live-translater` is an on-device, adaptive **Simultaneous Speech Translation (SimulST) & Streaming Speech Translation (StreamST)** runtime designed for continuous, unbounded conversational speech from YouTube.

```text
YouTube Audio Stream
        ↓
In-Browser AudioWorklet Resampling (48kHz -> 16kHz PCM)
        ↓
Sherpa-ONNX Zipformer Streaming Transducer ASR (CPU INT8)
        ↓
Local Agreement (K=2) + Adaptive Frontier (W=2) Policy
        ↓
Helsinki-NLP Marian INT8 CTranslate2 MT (< 70ms)
        ↓
Anchored Dual-Box Subtitle Presentation Layer (0.0000px displacement)
```

The system optimizes across four competing dimensions simultaneously:
1. **Useful Latency:** Time from speech utterance to readable translation on screen ($\text{TTFT} < 130\text{ms}$, $\text{MT} < 70\text{ms}$).
2. **Visual & Temporal Stability:** Zero retroactive line reflow or spatial jumping on already-read committed words ($\text{anchor displacement} = 0\text{px}$).
3. **Semantic Fidelity:** Coherent, natural English (US) output without broken word fragments.
4. **Local Resource Bounds:** Multi-core CPU inference with $\text{RTF} < 0.09$, memory $\text{RSS} < 700\text{MB}$, and zero cloud API dependencies.

---

## 3. Scientific Foundations & Literature Grounding

### 3.1 Streaming vs. Simultaneous Speech Translation
- **StreamAtt (ACL 2024):** Demonstrated that unbounded streaming audio requires bounded history selection rather than growing attention contexts ([Paper](https://aclanthology.org/2024.acl-long.202/)).
- **InfiniSST (ACL Findings 2025):** Established long-form conversational turn management and bounded KV-cache strategies ([Paper](https://aclanthology.org/2025.findings-acl.157/)).

### 3.2 Incremental Emission Policies & Local Agreement
- **Pinch-AST & Local Agreement (IWSLT 2026):** Evaluated retranslation with Longest Common Prefix (LCP) and Local Agreement ($K$). Verifies that committing prefixes matching across $K=2$ consecutive steps eliminates destructive revision loops ([Paper](https://aclanthology.org/2026.iwslt-1.30/)).
- **Divergence-Guided SimulST (AAAI 2026):** Explored information-density-driven READ/WRITE boundaries rather than static temporal slicing ([Paper](https://ojs.aaai.org/index.php/AAAI/article/view/29733)).

### 3.3 Selective Intelligence Architecture
Large Language Models (LLMs) are computationally excessive for the real-time translation hot path on consumer hardware. We adopt a **Selective Intelligence** model:
- **Hot Path (Deterministic & Fast):** Zipformer ASR + Local Agreement + Marian INT8 MT (Strictly $< 200\text{ms}$ total cycle).
- **Cold Path (Optional & Asynchronous):** Offline glossary extraction, entity disambiguation, or post-session transcription.

---

## 4. Empirical Evidence Ladder Summary (S0 $\to$ S5)

| Stage | Evaluated Technology | Measured Metric | Target Constraint | Verdict |
| :--- | :--- | :--- | :--- | :---: |
| **S0** | Architecture Demonstrator | `DECLARED / SIMULATED` | Proof of concept | `FROZEN` |
| **S1** | Manifest V3 AudioWorklet | Worklet overhead: **$0.567\mu\text{s}$** | $< 50\mu\text{s}$ | **`PASS`** |
| **S2** | Sherpa-ONNX Zipformer | TTFT: **$62.9\text{ms}$ (EN) / $125.7\text{ms}$ (JA)**, RTF: **$0.025$** | $\text{TTFT} < 180\text{ms}$, $\text{RTF} < 0.10$ | **`FROZEN`** |
| **S3** | Marian INT8 (CTranslate2) | Latency: **$65.7\text{ms}$ (p50)**, Size: **$82\text{MB}$** | $\text{Latency} < 120\text{ms}$, Size $< 500\text{MB}$ | **`PASS`** |
| **S4** | Local Agreement ($K=2, W=2$) | Committed revisions: **$0$**, MT calls reduced: **$82.7\%$** | $\text{Revisions} = 0$, Overhead $< 1.0\text{ms}$ | **`PASS`** |
| **S5** | Anchored Subtitle Renderer | Max anchor displacement: **$0.0000\text{px}$** | $\Delta \text{pos} = 0.0\text{px}$, Dispatch $< 16\text{ms}$ | **`PASS`** |

---

## 5. Known Invalidated Hypotheses & Caution Baseline

As detailed in [`Caution.md`](Caution.md), empirical validation disproved several early architectural assumptions:
1. *Assumption:* Background service workers can capture tab audio directly.
   **Reality:** MV3 requires `chrome.tabCapture` paired with an Offscreen Document.
2. *Assumption:* Translation flicker can be solved purely by translation policy without UI changes.
   **Reality:** Monolithic text replacements cause visual line reflow; visual stability requires dual-container DOM anchoring.
3. *Assumption:* Multilingual NLLB-200 600M is practical for lightweight distribution.
   **Reality:** NLLB requires $> 600\text{MB}$ RAM, $> 250\text{ms}$ latency, and carries a non-commercial license (CC-BY-NC-4.0). Marian INT8 is $8\times$ smaller ($82\text{MB}$), $4\times$ faster ($65\text{ms}$), and permissively licensed (Apache 2.0).

---

## 6. Open Research Directions (Post-V1)

1. **Multimodal Visual Context:** Utilizing on-screen video text / OCR to resolve Japanese homophones and proper names.
2. **Speaker Diarization:** Multi-speaker acoustic embeddings to color-code speaker turns without breaking anchor stability.
3. **Dynamic Wait-$k$ Acoustic Adaptation:** Dynamically modulating the unstable buffer window $W$ based on speech cadence and acoustic prosody.
