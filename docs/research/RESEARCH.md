# youtube-live-translater — Research

> **Research Snapshot:** 31 August 2026
> **Status:** Living research document
> **Purpose:** Consolidate the most relevant recent research, technologies, open-source implementations, and research directions for building `youtube-live-translater` as a lightweight, local-first, production-grade realtime translation system.

---

# 1. Research Thesis

`youtube-live-translater` is not primarily a subtitle translator.

The target system is a **local, adaptive, simultaneous interpretation runtime** for unbounded YouTube speech.

```text
YouTube Live / Video
        ↓
Streaming Audio
        ↓
Streaming ASR
        ↓
Incremental Linguistic State
        ↓
Adaptive Translation Policy
        ↓
Provisional Translation
        ↓
Stable / Confident Frontier
        ↓
Contextual Refinement
        ↓
Final Natural English (US)
```

The system optimizes several objectives simultaneously:

* useful translation latency
* semantic fidelity
* natural English (US)
* minimal visible revision
* bounded CPU/RAM/GPU consumption
* local/offline operation
* practical end-user packaging

The central research question is:

> **Can a lightweight local system continuously produce useful English from unbounded conversational speech, while progressively improving meaning with minimal latency, revision, and compute cost?**

A stronger systems question is:

> **Can an adaptive translation frontier decide what to emit, what to wait for, and what to revise more effectively than fixed chunking or naive retranslation under consumer-device constraints?**

---

# 2. Why the Problem Is Technically Interesting

A conventional translation pipeline looks approximately like:

```text
audio
  ↓
complete segment
  ↓
ASR
  ↓
translation
  ↓
subtitle
```

This architecture naturally introduces delay.

The desired system instead behaves like:

```text
audio stream
  ↓
partial ASR
  ↓
partial translation
  ↓
context accumulation
  ↓
revision
  ↓
final translation
```

The core tension is:

```text
earlier output
        vs
more context
```

Waiting for more context generally improves linguistic accuracy but increases latency.

Emitting too early reduces latency but causes:

* incorrect word order
* premature commitments
* subtitle flicker
* semantic corrections
* awkward English

Therefore the core problem is not simply translation quality.

It is the **quality / latency / revision / resource trade-off**.

---

# 3. State of the Field: 2024–2026

Recent work in **Streaming Speech Translation (StreamST)** and **Simultaneous Speech Translation (SimulST)** is highly relevant.

A useful distinction is:

```text
SimulST
=
translation of incrementally received speech

StreamST
=
continuous translation of an unbounded stream
```

The second formulation is much closer to YouTube Live.

A livestream does not naturally provide:

```text
sentence #1
sentence #2
sentence #3
```

Instead:

```text
audio → audio → audio → audio → ...
```

The system has to determine its own linguistic units and maintain bounded history.

---

# 4. StreamAtt — ACL 2024

### StreamAtt: Direct Streaming Speech-to-Text Translation with Attention-based Audio History Selection

StreamAtt explicitly tackles continuous unbounded speech and introduces methods for selecting useful audio history rather than assuming that all previous audio can remain in context.

It also introduces **StreamLAAL**, a latency metric for streaming speech translation.

Important implications for `youtube-live-translater`:

```text
unbounded input
       ↓
bounded relevant history
       ↓
continuous translation
```

rather than:

```text
entire livestream
       ↓
ever-growing context
```

This is a foundational paper for the system architecture.

Source:

https://aclanthology.org/2024.acl-long.202/

---

# 5. InfiniSST — ACL Findings 2025

### InfiniSST: Simultaneous Translation of Unbounded Speech with Large Language Model

InfiniSST treats unbounded speech more like a sequence of conversational turns and explores context/KV-cache management for long-form simultaneous translation.

This supports an important architecture principle:

> A livestream should be treated as a continuously evolving conversational state, not as one giant input.

Potential runtime abstraction:

```text
recent audio
+
recent ASR
+
recent translations
+
relevant context
```

instead of retaining everything indefinitely.

Source:

https://aclanthology.org/2025.findings-acl.157/

---

# 6. IWSLT 2026 — Current Research Frontier

The 2026 IWSLT Simultaneous Speech Translation work shows a rapidly moving field.

Current themes include:

* adaptive emission policies
* READ/WRITE decisions
* streaming ASR
* cascaded ASR → MT systems
* LLM-assisted translation
* multimodal models
* bounded conversational history
* KV-cache management
* long-form translation
* latency-aware evaluation
* contextual adaptation

Source:

https://aclanthology.org/volumes/2026.iwslt-1/

The important conclusion is that **adaptive streaming behavior is becoming as important as the underlying model architecture**.

---

# 7. Pinch-AST — IWSLT 2026

### Pinch-AST: Robust Cascaded Speech Translation System for the IWSLT 2026 Simultaneous Speech Translation Task

Pinch-AST is particularly relevant because it uses:

```text
speech model
+
translation model
+
retranslation
+
Longest Common Prefix
```

The key mechanism is conceptually:

```text
new source
   ↓
retranslate
   ↓
compare hypotheses
   ↓
retain stable prefix
   ↓
revise uncertain suffix
```

This closely matches the intended UX:

```text
show something early
        ↓
improve it as context arrives
```

The project should study this mechanism carefully rather than simply waiting for complete sentences.

Source:

https://aclanthology.org/2026.iwslt-1.30/

---

# 8. Local Agreement and Stable Prefixes

The broader **Local Agreement** family of approaches provides an important principle:

```text
hypothesis N
+
hypothesis N+1
        ↓
common stable part
```

The stable portion can be committed while the unstable part remains mutable.

This gives a useful UI model:

```text
stable prefix | unstable suffix
```

Example:

```text
"I went to that shop | yesterday..."
```

instead of repeatedly replacing:

```text
"Yesterday..."
"I went..."
"I went to..."
"I went to that shop..."
```

This is both an NLP mechanism and a UX mechanism.

---

# 9. CUHKSZ — IWSLT 2026

The CUHKSZ system demonstrates an approach where the model can predict `<wait>` when more source context is required.

Conceptually:

```text
READ / WAIT
    or
WRITE
```

This is much more powerful than a rule such as:

```text
translate every 2 seconds
```

because linguistic structure varies.

For example:

```text
日本では...
```

may need more context before producing a polished English sentence.

This directly supports an adaptive emission controller.

Source:

https://aclanthology.org/2026.iwslt-1.13/

---

# 10. Dynamic Attention / Adaptive Context

Recent research also explores predicting how much future context is needed rather than using a fixed wait policy.

The underlying principle is:

```text
required context
=
content-dependent
```

rather than:

```text
required context
=
fixed number of milliseconds
```

This is important because different utterances have very different information density.

A name may be translated immediately.

A clause with unresolved grammatical dependencies may need more context.

Source:

https://aclanthology.org/2026.iwslt-1.20/

---

# 11. Adaptive Policy Research

### Divergence-Guided Simultaneous Speech Translation

This line of work uses translation divergence to make READ/WRITE decisions.

Conceptually:

```text
current source
     ↓
translation distribution
     ↓
estimated effect of more source
     ↓
WAIT or WRITE
```

This is very close to the desired runtime behavior.

The important shift is:

> Emission should depend on predicted information value, not only elapsed time.

Source:

https://ojs.aaai.org/index.php/AAAI/article/view/29733

---

# 12. DrFrattn — Adaptive Streaming Policy

Recent work also explores learning adaptive streaming policies from model attention.

The implication is that latency control can become a learned or model-driven decision instead of a hand-written timing rule.

Relevant conceptual model:

```text
source arrives
    ↓
policy estimates confidence / information gain
    ↓
WAIT / WRITE
```

This reinforces the decision to keep the emission controller as an independent architectural subsystem.

Source:

https://aclanthology.org/2025.emnlp-main.1767/

---

# 13. Streaming ASR

ASR is the first major bottleneck.

Traditional Whisper usage often resembles:

```text
audio window
    ↓
decode
    ↓
audio window
    ↓
decode
```

This can produce unnecessary computation and latency.

More recent research and systems explore genuinely streaming or causal inference.

---

# 14. sherpa-onnx

`sherpa-onnx` is a particularly important candidate because it provides explicit online/streaming recognition APIs and streaming model families.

Conceptually:

```text
audio chunk
   ↓
online recognizer
   ↓
partial hypothesis
   ↓
more audio
   ↓
updated hypothesis
```

This maps directly onto the product requirement.

Repository:

https://github.com/k2-fsa/sherpa-onnx

Research questions:

* latency
* CPU consumption
* RAM
* multilingual support
* partial stability
* long-session behavior
* hardware acceleration
* model footprint

---

# 15. whisper.cpp

`whisper.cpp` is another important local inference/runtime candidate.

It has real-time/streaming examples and supports a broad set of local hardware environments.

Repository:

https://github.com/ggml-org/whisper.cpp

However, an important distinction must be preserved:

```text
streaming example
≠
optimal native streaming architecture
```

Sliding-window inference can still be useful as a baseline even if the eventual system adopts a more causal architecture.

---

# 16. WhisperRT / Causal Whisper Research

Recent work explores converting Whisper toward genuinely causal streaming inference.

The key architectural difference is:

```text
offline Whisper
+
repeated window decoding
```

versus:

```text
causal streaming encoder
+
incremental decoder
```

The second approach has the potential to reduce redundant computation and improve latency behavior.

This area deserves high research priority because ASR latency propagates into every downstream stage.

---

# 17. Streaming Knowledge Distillation

Another promising direction is distilling large/offline speech models into lighter streaming architectures.

The general strategy:

```text
strong offline teacher
       ↓
knowledge distillation
       ↓
smaller streaming student
```

This could eventually address one of the hardest project constraints:

> retain some of the quality of a strong model without shipping its full computational cost.

This is potentially more important for product deployment than simply choosing the newest large model.

---

# 18. Machine Translation Runtime

For local translation, the model and inference runtime should remain separate concepts.

```text
model
≠
runtime
```

A strong runtime can make an existing model substantially more practical.

---

# 19. CTranslate2

CTranslate2 is one of the strongest candidates for the translation execution layer.

Relevant capabilities include:

* optimized Transformer inference
* CPU/GPU execution
* quantization
* layer fusion
* asynchronous execution
* support for multiple model families
* native C++ runtime

It can work with model families such as NLLB, Marian and OPUS-MT.

Repository:

https://github.com/OpenNMT/CTranslate2

Performance:

https://github.com/OpenNMT/CTranslate2/blob/master/docs/performance.md

Quantization:

https://github.com/OpenNMT/CTranslate2/blob/master/docs/quantization.md

The strategic reason it is attractive:

```text
same model family
       ↓
optimized runtime
       ↓
smaller/faster inference
```

This aligns with the requirement:

```text
strong
+
local
+
lightweight
```

---

# 20. NLLB

NLLB remains a useful multilingual baseline because of broad language coverage.

However:

```text
many languages
+
high quality
```

can come with substantial model and memory costs.

More importantly, model licensing must be evaluated separately from technical quality.

For example, the Hugging Face model card for:

`facebook/nllb-200-distilled-600M`

lists a **CC-BY-NC-4.0** license.

Therefore:

> Open model does not automatically mean unrestricted redistribution.

Source:

https://huggingface.co/facebook/nllb-200-distilled-600M

---

# 21. Translation Model Research Direction

The project should not lock itself to NLLB.

Candidates should include:

```text
NLLB family
Marian
OPUS-MT
CTranslate2-compatible multilingual models
newer multilingual MT models
future specialized English-target models
```

The selection criterion must be:

```text
quality
+
latency
+
memory
+
language coverage
+
license
+
packaging
```

not popularity.

---

# 22. Local LLMs

Large language models are becoming increasingly important in simultaneous translation research.

Examples in recent IWSLT systems include Qwen-family models and other multilingual/multimodal foundation models.

However, the product has an unusually strict constraint:

```text
FREE
+
LOCAL
+
LIGHTWEIGHT
+
CONSUMER HARDWARE
```

Therefore the architecture should not become:

```text
Audio
 ↓
large LLM
 ↓
translation
```

on every update.

---

# 23. Selective Intelligence

A better architecture is:

```text
                    HOT PATH

Audio
 ↓
VAD
 ↓
Streaming ASR
 ↓
Fast MT
 ↓
Stabilization
 ↓
Subtitle


                 OPTIONAL PATH

                  ┌──────────┐
                  │ Context  │
                  └────┬─────┘
                       │
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
       slang       ambiguity       repair
       context     resolution      refinement
```

A local LLM becomes a **selective specialist**, not a mandatory translator.

This is one of the most important architectural principles of the project.

---

# 24. InfiniSST and Long-Form Context

The long-form research strongly supports a bounded conversational memory architecture.

Instead of:

```text
whole livestream
```

use:

```text
current segment
+
recent turns
+
relevant memory
```

Potential layers:

```text
L0 — current audio
L1 — current linguistic segment
L2 — recent turns
L3 — active terminology
L4 — relevant semantic memory
```

This provides context without unbounded resource growth.

---

# 25. Contextual Translation

The translation engine can use:

```text
previous source
+
previous translation
+
speaker style
+
named entities
+
terminology
+
slang
+
topic
```

This is particularly important for:

* pronouns
* omitted subjects
* slang
* jokes
* recurring terms
* technical vocabulary
* game/anime terminology
* speaker-specific expressions

The language layer should therefore be separate from the model.

---

# 26. Language Intelligence Layer

The project should maintain structured language knowledge:

```text
Language Intelligence
│
├── language metadata
├── normalization
├── terminology
├── glossary
├── slang
├── proper nouns
├── phrase patterns
├── translation memory
└── user customization
```

This means the product can improve contextual behavior without increasing model size indefinitely.

---

# 27. Segmentation Is Not the Same as VAD

This distinction is fundamental.

```text
speech endpoint
≠
linguistic endpoint
```

Example:

```text
speaker:
"Yesterday, I went to..."

pause
```

The speaker may simply be breathing or thinking.

A VAD-only system can incorrectly interpret this as:

```text
sentence finished
```

A linguistic system should instead consider:

```text
sentence incomplete
→ WAIT
```

Recent research on differentiable segmentation reinforces the importance of learning meaningful translation boundaries rather than relying exclusively on fixed segmentation.

Source:

https://aclanthology.org/2023.findings-acl.485/

---

# 28. Confident Translation Length

Another particularly relevant concept is the idea of predicting how much translation is sufficiently confident to expose.

Conceptually:

```text
source available
ABCDEFGHIJK

translation confidence
██████░░░░░

safe output
ABCDEF
```

This is closely related to the concept of a translation frontier.

It is preferable to a binary:

```text
FINAL
NOT FINAL
```

because realtime translation is inherently gradual.

Source:

https://aclanthology.org/2024.lrec-main.34/

---

# 29. Adaptive Translation Frontier

The strongest research direction emerging from the literature is an architecture-level synthesis.

## Definition

The **Adaptive Translation Frontier** is the boundary between:

```text
information safe to expose
```

and:

```text
information that should remain provisional
```

Conceptually:

```text
Current Source
      ↓
Hypothesis generation
      ↓
Confidence / stability estimation
      ↓
┌────────────────────────────┐
│ Adaptive Translation       │
│ Frontier                   │
│                            │
│ COMMIT | WAIT | REVISE     │
└────────────────────────────┘
      ↓
Subtitle state
```

The frontier continuously moves as more speech arrives.

---

# 30. Example

Suppose the source stream is:

```text
ABCDEFGHIJKLM
```

and the translation system currently produces:

```text
abcdefg|hijkl
       ↑
    frontier
```

Then:

```text
abcdefg
```

is treated as relatively stable.

```text
hijkl
```

remains revisable.

After additional context:

```text
ABCDEFGHIJKLMNOPQ
```

the result might become:

```text
abcdefghij|klmnop
          ↑
       frontier
```

The user experiences a continuously improving translation rather than repeated full-line replacement.

---

# 31. Beyond Character-Level Stability

Character-level LCP is useful but may be too conservative.

Example:

```text
Hypothesis A:
I went to the shop.

Hypothesis B:
I went to that shop.

Hypothesis C:
I went to that store.
```

Surface strings differ.

Semantic content is largely stable.

This suggests a future research direction:

```text
character stability
        ↓
token stability
        ↓
phrase stability
        ↓
semantic stability
        ↓
final linguistic stability
```

A semantic stability estimator could potentially reduce subtitle flicker without sacrificing final quality.

**Status:** research hypothesis, not an established result.

---

# 32. READ / WRITE / REVISE

The product's emission state should eventually be more expressive than binary waiting.

Candidate state machine:

```text
WAIT
PARTIAL
COMMIT
REVISE
FINALIZE
```

Possible inputs:

```text
ASR stability
translation divergence
linguistic completeness
context availability
elapsed time
resource pressure
```

Output:

```text
action
```

This provides a clean separation between:

```text
model inference
```

and:

```text
product behavior
```

---

# 33. Revision Cost

Traditional BLEU/WER measurements are insufficient for this product.

Introduce:

## Revision Cost

Measure how much already-visible text changes.

Small:

```text
"I went to the shop"
→
"I went to that shop"
```

Large:

```text
entire subtitle changes
```

The product can therefore optimize:

```text
Quality
+
Latency
+
Revision Cost
+
Resource Cost
```

This turns an important UX requirement into an ML/system metric.

**Status:** proposed project metric.

---

# 34. Proposed Research Objective

A useful conceptual objective is:

$$
J =
\alpha Q
-\beta L
-\gamma R
-\delta C
-\epsilon M
$$

where:

* `Q` = translation quality
* `L` = latency
* `R` = revision cost
* `C` = compute cost
* `M` = memory/resource cost

The coefficients should be established experimentally.

This formulation intentionally avoids optimizing only one traditional ML metric.

---

# 35. Browser Architecture Research

Chrome already provides relevant extension primitives.

### `chrome.tabCapture`

Allows an extension to capture media from the current tab after explicit user interaction.

Source:

https://developer.chrome.com/docs/extensions/reference/api/tabCapture

### Offscreen API

Allows extension functionality requiring a document/DOM without presenting another UI surface.

Source:

https://developer.chrome.com/docs/extensions/reference/api/offscreen

Possible structure:

```text
Chrome Extension
│
├── Service Worker
│    └── lifecycle / control
│
├── Offscreen Document
│    └── audio capture
│
├── Content Script
│    └── YouTube integration
│
├── Subtitle Renderer
│    └── progressive output
│
└── Runtime Client
     └── local runtime communication
```

---

# 36. Why Extension-First + Local Runtime

A browser-only system is attractive because:

```text
no native installer
```

but sustained AI inference creates difficult constraints:

* browser GPU differences
* memory pressure
* long-session performance
* browser lifecycle behavior
* extension limitations

Therefore the current architectural baseline is:

```text
Chrome Extension
       +
Local AI Runtime
```

The extension is the product interface.

The runtime is the AI data plane.

---

# 37. Native Messaging

A strong integration candidate is:

```text
Chrome Extension
       ↓
Native Messaging
       ↓
Native Host
       ↓
Local AI Runtime
```

This keeps:

```text
browser-specific code
```

separate from:

```text
AI/runtime code
```

and can later support other browsers.

The Native Messaging model is also available in Firefox, though implementation details differ.

---

# 38. Local Runtime

The runtime should provide:

```text
Audio ingestion
VAD
ASR
Segmentation
Context management
Translation
Revision
Model management
Resource management
Health monitoring
```

It should be:

* isolated
* restartable
* bounded
* cross-platform
* model-independent
* packageable
* observable

---

# 39. Native Runtime Language

Current candidates:

```text
Rust
C++
```

The final choice should be benchmark-driven.

Python remains highly useful for:

```text
research
datasets
benchmarking
model conversion
experiments
MLOps
```

but should not automatically become the production end-user dependency.

---

# 40. Browser-Only Inference

WebGPU/WASM should remain an active research branch.

Potential upside:

```text
no native runtime
```

Potential limitations:

```text
GPU variability
memory
sustained inference
browser compatibility
extension lifecycle
```

Therefore:

```text
Browser-only
=
experimental/optional backend

Extension + Local Runtime
=
primary architecture
```

until evidence suggests otherwise.

---

# 41. Lightweight Packaging

The goal is not necessarily:

> tiny total bytes including every model.

The goal is:

> lightweight user installation and resource footprint.

Separate:

```text
installer size
runtime size
model size
model cache size
```

Preferred model:

```text
Extension
   ↓
Lightweight Runtime
   ↓
Hardware detection
   ↓
Select model profile
   ↓
Download required model pack
```

not:

```text
installer
└── every model
```

---

# 42. Adaptive Model Profiles

Possible runtime profiles:

```text
LOW RESOURCE
BALANCED
QUALITY
```

Selection can use:

```text
CPU
RAM
GPU
VRAM
OS
thermal state
battery state
user preference
```

Potential behavior:

```text
GPU memory pressure
→ smaller model

CPU saturation
→ lower profile

optional LLM too expensive
→ disable reasoning path
```

The goal is graceful degradation, not binary failure.

---

# 43. MLOps Architecture

MLOps exists to answer:

> Does this model/runtime/policy actually improve the product?

The fundamental loop is:

```text
dataset
   ↓
model
   ↓
runtime
   ↓
replay
   ↓
metrics
   ↓
regression analysis
   ↓
new candidate
```

This means the MLOps layer is tightly coupled to product evaluation but does not need to become part of the user's runtime.

---

# 44. Replayability

Every sufficiently captured translation session should be replayable.

Conceptually:

```text
recorded audio/events
        ↓
replay
        ↓
same pipeline
        ↓
new model/policy
        ↓
comparison
```

This allows direct comparison between:

```text
model A
vs
model B
```

or:

```text
policy A
vs
Adaptive Translation Frontier
```

without asking a user to reproduce the same livestream.

---

# 45. Dataset Strategy

Dataset categories should include:

```text
clean speech
casual conversation
fast speech
slang
humor
disfluencies
interruptions
partial sentences
ambiguous grammar
named entities
technical vocabulary
long-form conversation
YouTube-like speech
```

The benchmark must include **realtime behavior**, not only final transcription/translation quality.

---

# 46. Evaluation Metrics

## ASR

```text
WER
CER
time-to-first-partial
partial stability
```

## Translation

```text
COMET
BLEU
chrF
human preference
terminology accuracy
```

## Realtime

```text
time-to-first-translation
end-to-end latency
finalization latency
revision count
revision magnitude
stability ratio
real-time factor
```

## System

```text
CPU
RAM
VRAM
startup time
disk
thermal behavior
```

---

# 47. Quality Definition

Final translation quality should consider more than lexical overlap.

Important dimensions:

```text
Semantic Fidelity
Grammatical Correctness
Naturalness
Context Preservation
Tone Preservation
Terminology
Named Entities
Humor / Slang
```

The output target is:

> Natural English (US) that remains faithful to what the speaker actually means.

The system should not aggressively rewrite personality or tone merely to sound polished.

---

# 48. Privacy

The core system should be local by default:

```text
audio
→ local
transcript
→ local
context
→ local
models
→ local
```

Future cloud services can exist only as explicit optional integrations.

No cloud dependency should be required for normal operation.

---

# 49. Security

The extension/runtime boundary must be treated as a security boundary.

Requirements include:

* explicit runtime authorization
* strict Native Messaging configuration
* validated input
* no arbitrary process execution
* safe model artifact handling
* integrity checks where practical
* no unnecessary exposed local network service
* minimal filesystem privileges

---

# 50. Observability

Structured runtime categories should include:

```text
capture
audio
vad
asr
translation
context
runtime
model
resource
ipc
packaging
```

Metrics should diagnose performance without requiring collection of raw user speech.

---

# 51. Long-Session Stability

A major hidden risk is accumulated latency.

A pipeline can appear realtime during the first minute while becoming slower over a long livestream.

Therefore research and testing must include:

```text
10 min
30 min
60 min+
```

and evaluate whether:

```text
processing time
```

gradually separates from:

```text
live playback time
```

Long-form simultaneous translation research specifically highlights this class of challenge.

---

# 52. Architecture Candidates

### A — Browser-only

```text
Extension
 ↓
WebGPU/WASM
 ↓
ASR + MT
```

Strong installation UX, but uncertain sustained inference/resource behavior.

### B — Extension + Python

```text
Extension
 ↓
Native Messaging
 ↓
Python
 ↓
AI models
```

Excellent for research prototypes but less attractive as the final end-user runtime.

### C — Extension + native runtime

```text
Extension
 ↓
Native Messaging
 ↓
Rust/C++
 ↓
optimized inference runtime
```

Best current fit for:

```text
local
free
cross-platform
resource-aware
production package
```

**Current preference: C.**

---

# 53. Technology Landscape

| Area               | Important Candidates                                              |
| ------------------ | ----------------------------------------------------------------- |
| Browser capture    | Chrome MV3, tabCapture, Offscreen                                 |
| ASR                | sherpa-onnx, faster-whisper, whisper.cpp, causal Whisper research |
| MT                 | NLLB, Marian, OPUS-MT, newer multilingual MT                      |
| MT runtime         | CTranslate2, ONNX Runtime                                         |
| Optional local LLM | llama.cpp-compatible models                                       |
| Runtime            | Rust / C++                                                        |
| Research/MLOps     | Python ecosystem                                                  |
| Streaming policy   | Local Agreement, LCP, READ/WRITE, adaptive policies               |
| Context            | bounded history, KV cache, RAG                                    |
| Packaging          | native runtime + separate model packs                             |

These remain candidates until benchmarked.

---

# 54. Research Gaps Worth Pursuing

The literature already provides strong solutions to individual components.

The more interesting gap is the **combination**:

```text
Chrome-first
+
local-first
+
lightweight runtime
+
unbounded YouTube speech
+
streaming ASR
+
incremental MT
+
adaptive emission
+
progressive revision
+
bounded context
+
selective reasoning
+
resource-aware scheduling
+
MLOps replay
```

This is not a claim that no one has ever built such a combination.

It is a project-level research opportunity identified from the current technology landscape.

---

# 55. Candidate Novel Direction

## Adaptive Translation Frontier

Potential architecture:

```text
                  incoming stream
                         │
                         ▼
                 Streaming ASR
                         │
                         ▼
                linguistic state
                         │
                         ▼
              translation hypotheses
                         │
                         ▼
             stability / confidence
                         │
                         ▼
          ┌──────────────────────────┐
          │ Adaptive Frontier        │
          │                          │
          │ WAIT / PARTIAL           │
          │ COMMIT / REVISE / FINAL  │
          └──────────────────────────┘
                         │
                         ▼
                     subtitle
```

The frontier could consider:

```text
ASR confidence
+
translation divergence
+
linguistic completeness
+
semantic stability
+
context
+
latency budget
+
resource budget
```

This is a research hypothesis requiring experiments.

---

# 56. Candidate Project Contribution

A meaningful project contribution does not require training a new foundation model.

A potential contribution is:

> **A lightweight local runtime that adaptively balances translation quality, latency, revision cost and compute cost for unbounded conversational speech.**

A possible experimental comparison:

```text
Baseline A
fixed chunking

Baseline B
retranslation + LCP

Baseline C
adaptive READ/WRITE

Candidate D
Adaptive Translation Frontier
```

Evaluate:

```text
quality
latency
revision cost
CPU
RAM
VRAM
throughput
```

Only a reproducible improvement would justify calling the mechanism a meaningful contribution.

---

# 57. Research Priorities

## Priority 1 — Streaming ASR

Determine the best quality/latency/resource point.

## Priority 2 — Translation runtime/model

Determine the best multilingual → English (US) combination under license and resource constraints.

## Priority 3 — Incremental Translation

Study:

```text
LCP
Local Agreement
wait-k
READ/WRITE
adaptive policies
semantic stability
```

## Priority 4 — Browser Capture

Validate actual YouTube capture behavior for long sessions.

## Priority 5 — Local Runtime

Benchmark:

```text
Rust
C++
CTranslate2
ONNX Runtime
whisper.cpp
sherpa-onnx
WebGPU
```

## Priority 6 — Packaging

Validate practical end-user installation and model management.

## Priority 7 — MLOps

Build datasets, replay, benchmarks and regression evaluation.

---

# 58. What the Project Should Borrow

The project should build on proven ideas:

```text
StreamAtt
→ bounded relevant history

InfiniSST
→ long-form context management

Local Agreement / LCP
→ stable-prefix commitment

Adaptive READ/WRITE
→ dynamic emission timing

Confident Translation Length
→ confidence-aware output

IWSLT 2026 context systems
→ context and memory mechanisms

CTranslate2 / optimized runtimes
→ practical local inference

Streaming ASR research
→ low-latency speech recognition
```

These are foundations, not implementation prescriptions.

---

# 59. What the Project Should Improve

The project should investigate whether it can move:

```text
fixed chunks
        →
adaptive linguistic timing
```

```text
character-only stability
        →
semantic stability
```

```text
large-model hot path
        →
selective intelligence
```

```text
research prototype
        →
consumer-grade local runtime
```

```text
final-score-only evaluation
        →
quality + latency + revision + resource evaluation
```

---

# 60. Architectural Rules That Must Not Drift

Future implementation decisions should preserve:

```text
1. Local-first
2. Realtime-first UX
3. Progressive refinement
4. Model/runtime replaceability
5. Lightweight end-user experience
```

A technology that improves theoretical quality but significantly violates these principles must be treated as an explicit trade-off.

---

# 61. Evidence Classification

Every future research entry should be classified as one of:

### Evidence-backed

Directly demonstrated by:

* peer-reviewed paper
* official documentation
* reproducible benchmark
* source code
* controlled experiment

### Engineering Inference

A reasoned conclusion based on several evidence sources.

### Research Hypothesis

An idea worth testing, but not yet demonstrated.

This prevents architecture decisions from silently becoming assumptions.

---

# 62. Current Open Questions

```text
UNKNOWN — REQUIRES VALIDATION

1. Which streaming ASR provides the best
   quality/latency trade-off on consumer CPUs?

2. Which multilingual MT model provides the best
   quality/latency/license combination?

3. CTranslate2 vs ONNX Runtime vs another MT runtime.

4. Rust vs C++ for the production runtime.

5. Whether WebGPU can be a useful optional backend.

6. How to implement semantic stability robustly.

7. How to define Adaptive Translation Frontier mathematically.

8. What model pack size is acceptable.

9. What consumer hardware baseline should be supported.

10. What end-to-end latency SLO is realistically achievable.

11. How much long-session latency accumulates.

12. How effectively selective local reasoning handles
    slang, ambiguity and humor.
```

---

# 63. Research Roadmap

```text
R1
Streaming ASR
        ↓
R2
Local MT
        ↓
R3
Incremental translation
        ↓
R4
Adaptive Translation Frontier
        ↓
R5
Chrome capture integration
        ↓
R6
Native local runtime
        ↓
R7
Hardware adaptation
        ↓
R8
Packaging
        ↓
R9
MLOps replay/evaluation
```

The ordering intentionally puts **feasibility and algorithmic behavior ahead of packaging polish**.

---

# 64. Final Research Position — 31 August 2026

As of **31 August 2026**, research in simultaneous and streaming speech translation is clearly moving toward:

```text
streaming
+
adaptive emission
+
context
+
long-form processing
+
revision/stability
+
LLM assistance
+
latency-aware evaluation
```

There is already substantial research solving individual pieces.

Therefore, `youtube-live-translater` should not try to win by claiming:

> "We use a better translation model."

The stronger direction is:

```text
Streaming ASR
+
Fast Local MT
+
Adaptive Emission
+
Stable/Confident Frontier
+
Context Management
+
Selective Reasoning
+
Resource-Aware Scheduling
+
Replay-Based MLOps
+
Consumer-Grade Packaging
```

The strongest current project hypothesis is:

> **A lightweight, local Adaptive Translation Frontier can continuously expose the most reliable portion of a translation while deferring or revising uncertain content, achieving a better quality/latency/revision/resource trade-off than fixed chunking or naive retranslation.**

This is a **research hypothesis**, not an established academic result.

---

# 65. North Star

The user's experience should ultimately be:

```text
Install
  ↓
Open YouTube
  ↓
Enable translation
  ↓
Speaker starts talking
  ↓
English appears almost immediately
  ↓
Output improves as context arrives
  ↓
Only uncertain regions change
  ↓
Sentence settles naturally
```

while internally the system is:

```text
Edge AI
+
Streaming NLP
+
Simultaneous Translation
+
Optimized Inference
+
Local Runtime Engineering
+
MLOps
```

The complexity belongs inside the system.

The user should only experience **immediate understanding**.

---

# 66. Primary References

1. **StreamAtt: Direct Streaming Speech-to-Text Translation with Attention-based Audio History Selection** — ACL 2024
   https://aclanthology.org/2024.acl-long.202/

2. **InfiniSST: Simultaneous Translation of Unbounded Speech with Large Language Model** — ACL Findings 2025
   https://aclanthology.org/2025.findings-acl.157/

3. **Pinch-AST: Robust Cascaded Speech Translation System for the IWSLT 2026 Simultaneous Speech Translation Task**
   https://aclanthology.org/2026.iwslt-1.30/

4. **CUHKSZ Simultaneous Speech Translation System for IWSLT 2026**
   https://aclanthology.org/2026.iwslt-1.13/

5. **Test-Time Adaptation of an Offline Multimodal Foundation Model for Simultaneous Speech Translation**
   https://aclanthology.org/2026.iwslt-1.27/

6. **Towards Dynamic Attention Masking for Simultaneous Speech Translation**
   https://aclanthology.org/2026.iwslt-1.20/

7. **Divergence-Guided Simultaneous Speech Translation**
   https://ojs.aaai.org/index.php/AAAI/article/view/29733

8. **End-to-End Simultaneous Speech Translation with Differentiable Segmentation**
   https://aclanthology.org/2023.findings-acl.485/

9. **CTranslate2**
   https://github.com/OpenNMT/CTranslate2

10. **sherpa-onnx**
    https://github.com/k2-fsa/sherpa-onnx

11. **whisper.cpp**
    https://github.com/ggml-org/whisper.cpp

12. **Chrome `tabCapture` API**
    https://developer.chrome.com/docs/extensions/reference/api/tabCapture

13. **Chrome Offscreen API**
    https://developer.chrome.com/docs/extensions/reference/api/offscreen

14. **facebook/nllb-200-distilled-600M**
    https://huggingface.co/facebook/nllb-200-distilled-600M
