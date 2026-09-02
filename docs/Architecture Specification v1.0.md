# youtube-live-translater

## Architecture Specification v1.0

**Status:** Proposed — Architecture Baseline
**Scope:** Product + System Architecture
**Primary Platform:** Chrome Extension
**Runtime Model:** Local-first / Local AI Runtime mandatory
**Primary Output Language:** English (US)
**Primary Use Case:** Realtime translation of YouTube video/live speech
**Core Principles:** Low perceived latency, high semantic fidelity, progressive refinement, privacy, zero mandatory cloud API dependency, lightweight end-user packaging

---

# 1. Executive Summary

`youtube-live-translater` is a local-first realtime AI translation system delivered **Extension-first**, initially through a Chrome Extension and later extensible to other browsers/platforms.

The system translates arbitrary spoken languages from YouTube into **natural, accurate English (US)** while minimizing the time between speech and understandable translated output.

The defining product characteristic is not merely realtime translation. It is **progressive translation with revision**:

```text
Speech
  ↓
Partial ASR
  ↓
Immediate provisional translation
  ↓
Context accumulation
  ↓
Sentence / clause completion
  ↓
Full-context translation
  ↓
Revision / stabilization
```

The user should not have to wait for a speaker to finish a sentence before seeing useful information.

The system is therefore designed around two simultaneous objectives:

```text
Low Latency
    +
High Final Quality
```

rather than maximizing either one independently.

The architecture separates:

```text
Browser UX
        +
Local AI Runtime
        +
Model Runtime
        +
Language Intelligence
        +
MLOps / Evaluation
```

The browser extension is the primary user-facing product, while the Local AI Runtime is the mandatory local data plane that performs audio processing, ASR, translation, context management and refinement.

No external paid AI API is required for the core translation path.

---

# 2. Product Vision

## 2.1 Vision

Make realtime language understanding during YouTube consumption feel immediate and natural:

> The moment the speaker begins communicating an idea, the user should begin receiving meaningful English; when more context becomes available, the system should silently improve the translation.

The system should feel:

* immediate
* stable
* natural
* context-aware
* unobtrusive
* private
* resource-efficient

The user should experience a translation system rather than an AI pipeline.

---

# 3. Product Goals

## 3.1 Primary Goals

### G1 — Realtime understanding

Provide useful English output before the speaker has necessarily completed a sentence.

### G2 — Final translation quality

The finalized English output should prioritize:

1. semantic fidelity
2. grammatical correctness
3. natural English (US)
4. contextual appropriateness
5. preservation of speaker intent
6. appropriate handling of humor, slang and ambiguity

### G3 — Progressive refinement

Allow provisional output to be revised when additional linguistic context changes the interpretation.

### G4 — Local-first operation

The core production path must run locally on the user's machine.

The system must not require:

* OpenAI API
* Google API
* Gemini API
* commercial translation API
* hosted transcription service
* mandatory cloud inference

### G5 — Lightweight end-user experience

The installation and runtime experience must be practical for normal users.

The user should not need to install a complete Python/ML development environment.

### G6 — Hardware adaptability

The system should adapt to available resources:

```text
low-resource machine
      ↓
balanced configuration
      ↓
higher-quality configuration
```

### G7 — Cross-platform architecture

Chrome is the first delivery platform, but the core runtime must not be coupled to Chrome-specific implementation details.

Target future platforms:

```text
Chrome
Firefox
Edge
possibly other browsers
```

and:

```text
Windows
Linux
macOS
```

---

# 4. Non-Goals

The following are explicitly outside the initial product scope.

## NG1 — General-purpose speech assistant

The project is not intended to become a general voice assistant.

## NG2 — Voice cloning

No requirement to generate translated speech in the initial product.

## NG3 — Cloud SaaS

The core product is not designed as a hosted translation SaaS.

## NG4 — Full video understanding

Visual understanding of the video is not part of the core realtime path.

Future multimodal extensions may exist but must not complicate the initial architecture.

## NG5 — Microservice-first deployment

The first production architecture must not introduce distributed infrastructure merely for architectural appearance.

## NG6 — Mandatory LLM inference

A large language model must not be present on every realtime request.

The hot path must remain lightweight.

## NG7 — Maximum model size

The goal is not to ship the largest available model.

The system optimizes:

> **perceived intelligence under realtime resource constraints.**

---

# 5. Core Architectural Invariants

These rules are considered architectural invariants unless explicitly changed through an Architecture Decision Record (ADR).

## I1 — Extension-first

The primary user-facing product is a browser extension.

## I2 — Local AI Runtime is mandatory

The extension may control the system, but the production AI data plane lives outside the browser sandbox.

```text
Extension
   ↓
Local AI Runtime
```

## I3 — No mandatory cloud inference

The core translation path must remain operational without paid external APIs.

## I4 — Model abstraction

ASR and translation implementations must be replaceable.

Code must depend on engine interfaces rather than a specific model.

## I5 — Event-driven internal pipeline

Major processing stages communicate through explicit versioned events.

## I6 — Progressive output

Translation is not a single immutable string-generation operation.

It is a sequence of hypotheses that may transition:

```text
UNSTABLE → STABLE → FINAL
```

## I7 — Bounded memory

Conversation context, audio buffers and intermediate states must be bounded.

The system must not retain an unlimited livestream.

## I8 — Replayability

A recorded event stream must be replayable through the processing pipeline for testing and evaluation.

## I9 — Resource awareness

CPU, RAM, VRAM and thermal/resource constraints are first-class runtime inputs.

## I10 — Packaging is part of architecture

Installation, model acquisition, cache management, process lifecycle and updates are production concerns, not post-production tasks.

---

# 6. High-Level Architecture

```text
                         ┌────────────────────┐
                         │     YouTube Tab    │
                         │                    │
                         │ Video / Live Audio │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Chrome Extension   │
                         │                    │
                         │ Service Worker     │
                         │ Offscreen Capture  │
                         │ Subtitle Renderer  │
                         │ Settings / Control │
                         └─────────┬──────────┘
                                   │
                            Native Messaging
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │       Local AI Runtime          │
                  │                                 │
                  │ Audio Ingestion                 │
                  │ VAD / Endpointing               │
                  │ Streaming ASR                   │
                  │ Segment Manager                 │
                  │ Context Memory                  │
                  │ Incremental Translation         │
                  │ Revision / Stabilization        │
                  │ Subtitle Event Bus              │
                  └───────────────┬─────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
             Model Runtime                Language Data
                    │                           │
          ┌─────────┼─────────┐         ┌──────┼─────────┐
          ▼         ▼         ▼         ▼      ▼         ▼
        ASR       MT       Optional    Glossary Slang   Memory
       Engine    Engine       LLM
```

---

# 7. Architectural Planes

The system is divided into five logical planes.

## 7.1 Experience Plane

Responsible for browser UX.

```text
Chrome Extension
```

Responsibilities:

* capture/control integration
* subtitle rendering
* visual state
* user settings
* runtime status
* model/profile configuration
* error presentation

It must not contain business logic for ASR/translation.

---

## 7.2 AI Data Plane

Implemented by the Local AI Runtime.

Responsibilities:

* audio ingestion
* VAD
* ASR
* segmentation
* context management
* translation
* revision
* event generation
* resource scheduling

This is the central runtime.

---

## 7.3 Model Runtime Plane

Responsible for executing AI models efficiently.

Candidate technologies include:

```text
ASR:
- faster-whisper
- whisper.cpp
- sherpa-onnx
- other streaming-capable runtimes

Translation:
- CTranslate2
- ONNX Runtime
- other optimized inference runtimes

Optional contextual reasoning:
- llama.cpp
- other local quantized inference runtimes
```

These are **technology candidates, not frozen dependencies**.

Final technology choices require benchmarking.

---

## 7.4 Language Intelligence Plane

Contains structured language information that improves translation without requiring a larger model.

Examples:

```text
language metadata
terminology
glossaries
slang
proper nouns
phrase memory
translation memory
speaker style
recent context
normalization rules
```

This layer should evolve independently from the model layer.

---

## 7.5 MLOps / Evaluation Plane

Responsible for:

* datasets
* model metadata
* benchmark execution
* replay
* quality evaluation
* latency evaluation
* resource evaluation
* regression detection
* model selection

MLOps infrastructure is primarily a **development/research system**, not necessarily an end-user dependency.

---

# 8. Browser Extension Architecture

The Chrome implementation should follow Manifest V3.

Logical components:

```text
extension/
├── service-worker
├── offscreen
├── content-script
├── subtitle-ui
├── popup/settings
└── runtime-client
```

## 8.1 Service Worker

Responsibilities:

* extension lifecycle
* runtime connection management
* configuration
* messaging coordination
* native messaging lifecycle

It must remain thin.

---

## 8.2 Offscreen Document

Responsibilities:

* audio capture
* browser APIs requiring document context
* communication with runtime client where appropriate

The design must use the browser's supported tab-audio capture mechanisms rather than extracting YouTube media through fragile DOM/network interception.

---

## 8.3 Content Script / Subtitle Renderer

Responsibilities:

* render translation overlay
* synchronize subtitle events with video playback
* manage visual transitions
* maintain stable subtitle layout

The renderer should treat translation events as state updates rather than plain text replacements.

---

# 9. Local AI Runtime

The runtime is a native process installed locally.

Primary requirements:

* small launcher/binary footprint
* isolated process
* crash resilience
* bounded memory
* predictable resource usage
* cross-platform design
* model independence
* deterministic interfaces
* no dependency on browser internals

The runtime should expose a stable protocol to the extension.

---

# 10. Runtime Boundary

The extension communicates with the runtime through a controlled local interface.

Primary candidate:

```text
Chrome Extension
       ↓
Native Messaging
       ↓
Native Host
       ↓
AI Runtime
```

The runtime should not expose an unnecessary network-facing server by default.

Security objective:

> Local communication must be authenticated/authorized by the browser's native messaging mechanism and bound to the installed extension.

---

# 11. Core Realtime Pipeline

```text
Audio
  ↓
Audio Buffer
  ↓
VAD
  ↓
Streaming ASR
  ↓
Partial Hypotheses
  ↓
Segment Manager
  ↓
Context Memory
  ↓
Incremental Translation
  ↓
Stabilization / Revision
  ↓
Subtitle Events
  ↓
Extension Renderer
```

---

# 12. Audio Ingestion

Input:

```text
YouTube tab audio
```

Audio should be normalized into a runtime-compatible stream.

The ingestion subsystem must:

* detect audio availability
* preserve timing
* handle silence
* tolerate brief interruptions
* maintain bounded buffering
* report capture errors

Audio capture is independent of ASR.

---

# 13. VAD / Endpointing

VAD is responsible for distinguishing:

```text
speech
silence
possible endpoint
```

VAD must not automatically imply sentence completion.

These are separate concepts:

```text
Speech endpoint
≠
Linguistic sentence endpoint
```

For example:

```text
speaker pauses
      ↓
possible clause boundary
      ↓
speaker continues
```

The system must avoid prematurely finalizing the translation.

---

# 14. ASR Architecture

ASR must expose an abstraction similar to:

```text
ASREngine
    start()
    push_audio()
    get_partial()
    finalize_segment()
    stop()
```

The exact API is implementation-dependent.

The engine must be able to produce partial hypotheses.

Conceptual output:

```json
{
  "segment_id": "seg-001",
  "text": "日本では",
  "stability": 0.42,
  "is_final": false,
  "start_ms": 1200,
  "end_ms": 1900
}
```

Later:

```json
{
  "segment_id": "seg-001",
  "text": "日本ではこういうことがよくあります",
  "stability": 0.91,
  "is_final": false
}
```

Eventually:

```json
{
  "segment_id": "seg-001",
  "text": "日本ではこういうことがよくあります",
  "stability": 1.0,
  "is_final": true
}
```

---

# 15. Translation Architecture

Translation must be incremental.

Conceptual abstraction:

```text
TranslationEngine
    translate_partial()
    translate_contextual()
    translate_final()
```

A translation event contains:

```text
source text
source language
target language
translation hypothesis
confidence/stability
context revision
timestamp
```

---

# 16. Progressive Translation Model

The system maintains several linguistic states.

## State A — Raw

```text
speaker output
```

## State B — ASR hypothesis

```text
partial transcription
```

## State C — Provisional translation

```text
immediate English interpretation
```

## State D — Contextual refinement

```text
translation revised using accumulated context
```

## State E — Final

```text
stable full-context translation
```

---

# 17. Example

Speaker:

```text
昨日さ、あの店に行ったんだけど...
```

Possible progression:

```text
Input:
昨日さ

Output:
"Yesterday..."
```

Then:

```text
Input:
昨日さ、あの店に行った

Output:
"Yesterday, I went to that place..."
```

Then full context:

```text
昨日さ、あの店に行ったんだけど...
```

Final:

```text
"Yesterday, I went to that place, and..."
```

The UI may retain already-stable content while revising only the unstable suffix.

---

# 18. Revision Strategy

The renderer should avoid replacing the entire subtitle whenever a partial hypothesis changes.

Instead:

```text
stable prefix
+
unstable suffix
```

Example:

```text
STABLE:
"I went to"

UNSTABLE:
"that shop..."
```

Later:

```text
STABLE:
"I went to that shop"

UNSTABLE:
"yesterday..."
```

This minimizes visual flicker.

---

# 19. Translation Stability

Each output should carry a stability state.

```text
UNSTABLE
STABLE
FINAL
```

The UI should visually distinguish stability only subtly.

The system must avoid:

```text
translation A
translation B
translation C
translation D
```

rapidly replacing the entire subtitle line.

The preferred model is:

```text
A → refined A
```

rather than:

```text
A → B → C → D
```

where possible.

---

# 20. Context Memory

Context memory is bounded and structured.

It should store:

```text
recent source segments
recent translations
speaker style
active topic
named entities
terminology
slang candidates
recent unresolved ambiguity
translation decisions
```

It must not simply store an unlimited transcript.

Conceptually:

```text
Short-term memory
    ↓
Rolling conversational context
    ↓
Relevant semantic memory
```

---

# 21. Language Intelligence

The system should maintain a structured language layer.

```text
Language Intelligence
├── language metadata
├── normalization
├── terminology
├── glossary
├── slang
├── proper nouns
├── phrase patterns
├── translation memory
└── user customizations
```

This layer improves model output without requiring heavier inference.

---

# 22. Slang and Humor

Slang/humor handling is a contextual interpretation problem.

The system should consider:

```text
literal meaning
+
conversation context
+
speaker behavior
+
known slang
+
previous translations
```

An optional local reasoning model may assist only when required.

It must not become mandatory on the realtime hot path.

---

# 23. Hot Path vs Cold Path

## Hot Path

Must remain lightweight:

```text
audio
→ VAD
→ ASR
→ segmentation
→ translation
→ stabilization
→ subtitle
```

## Cold / Optional Path

Used selectively:

```text
context analysis
slang interpretation
ambiguity resolution
translation repair
terminology detection
offline post-processing
```

Large LLMs belong here, not by default on every subtitle update.

---

# 24. Model Strategy

The system must support multiple model profiles.

Example:

```text
LOW
├── low-resource ASR
└── small MT

BALANCED
├── medium ASR
└── medium MT

QUALITY
├── higher-quality ASR
└── higher-quality MT
```

Runtime selection can be based on:

```text
CPU
RAM
GPU
VRAM
OS
battery state
thermal conditions
user preference
```

---

# 25. Model Selection Principle

Model selection must be based on empirical data.

Required benchmark dimensions:

| Dimension            | Measurement                            |
| -------------------- | -------------------------------------- |
| Translation quality  | COMET / BLEU / chrF / human evaluation |
| ASR quality          | WER / CER                              |
| First output latency | time-to-first-translation              |
| End-to-end latency   | speech → displayed translation         |
| Stability            | revision frequency                     |
| CPU                  | average / peak utilization             |
| RAM                  | resident memory                        |
| VRAM                 | allocated memory                       |
| Throughput           | audio seconds processed / real second  |
| Disk                 | model package size                     |
| Startup              | cold-start time                        |

No model becomes the default merely because it is popular.

---

# 26. Candidate Technology Families

These technologies are candidates for research.

## ASR

```text
Whisper
faster-whisper
whisper.cpp
sherpa-onnx
other streaming ASR implementations
```

## Translation

```text
NLLB family
Marian / OPUS-MT
CTranslate2-compatible models
other multilingual MT models
```

## Local LLM

```text
llama.cpp-compatible quantized models
other lightweight local reasoning engines
```

## Inference Runtime

```text
CTranslate2
ONNX Runtime
whisper.cpp
sherpa-onnx
other optimized runtimes
```

These choices must remain behind runtime interfaces.

---

# 27. License Requirements

Software and model licenses must be tracked separately.

For every candidate model:

```text
model
version
license
language coverage
commercial-use restrictions
redistribution restrictions
quantized version license
derived-artifact restrictions
```

No model may be bundled into end-user distribution until its redistribution/license status is explicitly validated.

Status:

```text
UNKNOWN — REQUIRES VALIDATION
```

must be allowed in research metadata.

---

# 28. Model Packaging

Models must be treated as separately managed artifacts.

Preferred installation pattern:

```text
Extension
      ↓
Install lightweight runtime
      ↓
Hardware/language detection
      ↓
Download required model pack
      ↓
Cache locally
```

Avoid:

```text
single installer
└── all models
```

The user should only download what is necessary.

---

# 29. Runtime Packaging

Preferred conceptual structure:

```text
Application
├── extension
├── native runtime
├── model manager
└── cached model packs
```

Research/development dependencies such as:

```text
Python
PyTorch
Jupyter
training tools
benchmark notebooks
```

should not automatically become end-user dependencies.

---

# 30. Cross-Platform Strategy

The architecture must isolate:

```text
browser adapter
```

from:

```text
AI runtime core
```

Conceptually:

```text
Browser Adapter
├── Chrome
├── Firefox
└── Edge

        ↓

Common Runtime Protocol

        ↓

Local AI Runtime
```

This prevents browser-specific assumptions from contaminating the AI system.

---

# 31. Internal Event Model

The system is event-oriented.

Core events:

```text
AudioChunk
ASRPartial
ASRFinal
SegmentOpened
SegmentUpdated
TranslationPartial
TranslationUpdated
TranslationFinal
ContextUpdated
SubtitleUpdated
RuntimeWarning
RuntimeError
```

Every event should contain:

```text
event_id
schema_version
session_id
timestamp
source
payload
```

---

# 32. Event Versioning

Event schemas must be versioned.

Example:

```text
translation.segment.v1
translation.segment.v2
```

Breaking changes require a new schema version.

This is necessary for:

* replay
* debugging
* dataset generation
* compatibility
* future distributed execution

---

# 33. Replay System

The system must support:

```text
recorded input
      ↓
replay
      ↓
same runtime pipeline
      ↓
deterministic-ish benchmark
```

Replay artifacts may contain:

```text
audio
ASR outputs
translation outputs
timestamps
model versions
runtime profile
hardware metadata
```

This becomes one of the foundations of MLOps.

---

# 34. MLOps Architecture

The MLOps system should answer:

> Does model/runtime version B actually improve the product?

not merely:

> Is model B theoretically stronger?

Every model candidate must be evaluated across:

```text
quality
latency
memory
CPU/GPU load
stability
language coverage
license
```

---

# 35. Dataset Strategy

Dataset categories:

```text
clean speech
casual conversation
fast speech
slang
humor
interruptions
disfluencies
partial sentences
long sentences
ambiguous syntax
named entities
technical vocabulary
YouTube-like speech
```

A special emphasis should be placed on **realtime behavior**, not only final sentence quality.

---

# 36. Evaluation Layers

## Layer 1 — Component Evaluation

```text
ASR quality
MT quality
VAD behavior
```

## Layer 2 — Pipeline Evaluation

```text
ASR → MT
```

## Layer 3 — Realtime Evaluation

```text
latency
revision
stability
```

## Layer 4 — UX Evaluation

```text
subtitle flicker
perceived delay
readability
context coherence
```

---

# 37. Quality Definition

“Correct translation” is not one metric.

Final quality should be considered across:

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

English output should be natural English (US), but the system must avoid rewriting the speaker into an unrelated personality.

The translation objective is:

> natural and fluent without drifting from the speaker's meaning.

---

# 38. Realtime Metrics

The initial metrics contract should include:

```text
TTFT
Time To First Translation

E2E latency
Speech → displayed translation

Finalization latency
Speech end → final translation

Revision count
Number of visible revisions

Revision magnitude
How much existing output changes

Stability ratio
Stable output / total output

Real-time factor
processing time / audio duration
```

---

# 39. Target SLO Philosophy

Exact values must be determined experimentally.

The initial design should optimize for:

```text
First useful output
      ↓
very low latency

Final output
      ↓
higher quality

Visible revision
      ↓
minimal
```

Concrete numerical SLOs are:

```text
UNKNOWN — REQUIRES BENCHMARKING
```

They must not be invented before hardware/model benchmarks exist.

---

# 40. Resource Management

The runtime must continuously reason about resource state.

Potential runtime states:

```text
NORMAL
CONSTRAINED
DEGRADED
RECOVERING
```

Examples:

```text
GPU memory pressure
→ switch to smaller model

CPU saturation
→ reduce inference frequency / model size

thermal pressure
→ lower profile

insufficient memory
→ disable optional contextual model
```

Degradation must preserve core functionality whenever possible.

---

# 41. Failure Handling

Failures should be isolated by subsystem.

Example:

```text
ASR failure
    ↓
restart ASR
    ↓
preserve runtime session
```

Optional context model failure:

```text
LLM failure
    ↓
disable optional reasoning
    ↓
continue standard translation
```

Native runtime crash:

```text
Extension detects disconnect
    ↓
attempt controlled restart
    ↓
restore configuration
```

The product should fail soft rather than fail globally.

---

# 42. Privacy

The default system should follow:

```text
audio stays local
transcripts stay local
models run locally
context stays local
```

No audio or transcript should leave the machine unless a user explicitly enables a future external service.

Telemetry, if introduced, must be:

* opt-in or clearly disclosed
* minimal
* non-content-bearing by default
* separable from translation operation

---

# 43. Security

The extension/runtime boundary must be treated as a security boundary.

Requirements:

* explicit extension authorization
* strict native messaging host configuration
* no arbitrary command execution from browser input
* strict input validation
* safe model artifact verification
* signed or integrity-checked model downloads where feasible
* no unnecessary open localhost ports
* no unrestricted filesystem access from extension-originated commands

---

# 44. Observability

Runtime logs must be structured.

Example categories:

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

Metrics must make performance problems diagnosable without recording user speech by default.

---

# 45. Architecture Boundaries

## Browser

Owns:

```text
UX
capture control
subtitle presentation
settings
lifecycle
```

## Runtime

Owns:

```text
AI pipeline
resource management
state
model execution
```

## Model layer

Owns:

```text
inference
```

## Language layer

Owns:

```text
linguistic metadata
```

## MLOps

Owns:

```text
evaluation
benchmarking
model governance
```

No layer should become a generic “utility bucket”.

---

# 46. Repository Concept

A future repository should conceptually separate:

```text
youtube-live-translater/
│
├── extension/
│
├── runtime/
│
├── models/
│
├── language/
│
├── evaluation/
│
├── datasets/
│
├── benchmarks/
│
├── packaging/
│
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── research/
│   └── operations/
│
└── tooling/
```

Exact language/tool choices remain open.

---

# 47. Recommended Runtime Language Direction

Current architectural preference:

```text
Rust or C++
```

for the production runtime boundary/core, with AI inference delegated to optimized native inference libraries.

Python remains valuable for:

```text
research
experimentation
benchmarking
dataset processing
model conversion
MLOps tooling
```

but should not automatically become the production runtime dependency.

This is a design preference, not yet a final implementation decision.

---

# 48. Recommended Development Model

The project should be developed in layers.

## Phase 0 — Technology Research

Determine:

```text
best ASR runtime
best MT runtime/model families
best VAD
best incremental strategy
browser capture feasibility
native runtime feasibility
packaging feasibility
```

Deliverable:

```text
technology decision matrix
```

---

## Phase 1 — Realtime Core Prototype

Build:

```text
audio
→ VAD
→ ASR
→ translation
→ subtitle event
```

The primary goal is **feasibility**, not polished UX.

---

## Phase 2 — Progressive Translation

Implement:

```text
partial ASR
→ provisional translation
→ context buffer
→ refinement
→ stable/final output
```

This phase represents the central product differentiation.

---

## Phase 3 — Browser Integration

Build:

```text
Chrome Extension
+
Native Runtime
```

with real YouTube audio capture.

---

## Phase 4 — Production Runtime

Add:

```text
resource manager
model manager
failure recovery
structured logs
packaging
configuration
runtime health
```

---

## Phase 5 — MLOps

Add:

```text
datasets
replay
benchmarking
model registry
quality regression
performance regression
```

---

## Phase 6 — Cross-platform

Extend the same runtime protocol to:

```text
Firefox
Edge
Linux
Windows
macOS
```

where technically justified.

---

# 49. Technology Research Priorities

Research priority order:

## R1 — Streaming ASR

Highest priority because ASR latency directly affects every downstream stage.

Investigate:

```text
Whisper
faster-whisper
whisper.cpp
sherpa-onnx
```

Evaluate:

```text
WER
TTFT
streaming behavior
CPU
RAM
GPU
startup
partial stability
```

---

## R2 — Machine Translation

Investigate:

```text
NLLB
Marian / OPUS-MT
CTranslate2-supported multilingual models
newer multilingual MT candidates
```

Evaluate:

```text
quality
latency
memory
language coverage
license
```

---

## R3 — Incremental Translation Algorithms

Research:

```text
simultaneous translation
incremental MT
prefix-to-prefix translation
retranslation
stable prefix detection
wait-k style strategies
sentence boundary prediction
revision minimization
```

This is likely to contain the project's most important algorithmic research.

---

## R4 — Browser Audio Architecture

Validate:

```text
Chrome tabCapture
Offscreen API
service-worker lifecycle
audio stream stability
YouTube behavior
permission model
```

---

## R5 — Local Runtime

Benchmark:

```text
Rust
C++
ONNX Runtime
CTranslate2
whisper.cpp
sherpa-onnx
WebGPU/WASM
```

against actual user hardware.

---

## R6 — Packaging

Validate:

```text
Windows installation
Linux packaging
macOS packaging
model downloads
model updates
runtime updates
rollback
uninstall
disk usage
```

This track must start early rather than at the end.

---

# 50. Browser-Only Inference

Browser-only AI inference is a research track, not the primary architecture.

Possible technologies:

```text
WebGPU
WASM
browser-hosted model runtimes
```

Advantages:

* zero native runtime
* easier installation
* potentially simpler distribution

Disadvantages:

* browser GPU variability
* model memory pressure
* sustained inference challenges
* lifecycle restrictions
* cross-browser differences

Primary architecture remains:

```text
Extension
+
Local Runtime
```

until benchmarks prove browser-only execution is superior for the target hardware population.

---

# 51. Architectural Anti-Patterns

The project must explicitly avoid these patterns.

## A1 — Cloud API dependency

```text
YouTube
→ OpenAI API
→ translation
```

Not acceptable as the core architecture.

## A2 — Python development environment as product requirement

```text
user
→ clone repository
→ pip install
→ CUDA
→ PyTorch
→ model
```

Not an acceptable end-user experience.

## A3 — Giant model by default

Quality must not automatically justify unacceptable memory/latency.

## A4 — Full LLM hot path

Every subtitle update must not invoke a large reasoning model.

## A5 — Sentence-only buffering

Waiting until complete sentences destroys the defining UX objective.

## A6 — Unlimited context

Memory must be bounded.

## A7 — Microservice overengineering

Do not introduce Kafka/Kubernetes/Redis/etc. until a measured requirement exists.

## A8 — Model lock-in

No core subsystem should directly depend on a single model.

## A9 — Fragile YouTube scraping

The browser integration should use supported browser capture mechanisms rather than depending on brittle internal YouTube APIs.

## A10 — Benchmarking only final BLEU/WER

Realtime latency and revision behavior are first-class quality dimensions.

---

# 52. Architecture Decision Records

Important future decisions should be recorded as ADRs.

Initial ADR candidates:

```text
ADR-001
Chrome Extension + Local Runtime architecture

ADR-002
Native Messaging vs localhost IPC

ADR-003
ASR engine selection

ADR-004
Translation runtime selection

ADR-005
Model licensing policy

ADR-006
Incremental translation/revision algorithm

ADR-007
Runtime implementation language

ADR-008
Model packaging strategy

ADR-009
Hardware-adaptive model selection

ADR-010
Cross-platform strategy
```

A technology change should modify the relevant ADR rather than silently changing the architecture.

---

# 53. Decision Matrix

Every major technology should be evaluated using:

| Criterion               |    Weight |
| ----------------------- | --------: |
| Realtime latency        | Very High |
| Translation/ASR quality | Very High |
| Memory footprint        |      High |
| CPU efficiency          |      High |
| GPU efficiency          |      High |
| Streaming support       |      High |
| Cross-platform          |      High |
| Model coverage          |      High |
| License                 |  Critical |
| Maturity                |    Medium |
| Packaging complexity    |      High |
| Community/ecosystem     |    Medium |
| Replaceability          |      High |

No technology is accepted solely because it wins one benchmark.

---

# 54. Definition of Production-Ready

`youtube-live-translater` is **not production-ready** merely because translation works.

Production readiness requires:

```text
✓ Chrome extension works reliably
✓ local runtime installs cleanly
✓ model installation is understandable
✓ audio capture is stable
✓ realtime pipeline survives long sessions
✓ partial output is useful
✓ revisions are visually stable
✓ final output is high quality
✓ resource use is bounded
✓ runtime recovers from failures
✓ models are versioned
✓ model licenses are validated
✓ telemetry does not require user content
✓ replay benchmarks exist
✓ regression testing exists
✓ packaging is reproducible
✓ uninstall is clean
✓ runtime/model updates are safe
```

---

# 55. Success Criteria

The product should eventually satisfy this qualitative test:

> A user opens a YouTube livestream in another language, enables translation, and within a short interval begins receiving useful natural English without needing to understand or manage the underlying AI system.

The user should **not** perceive:

```text
ASR delay
translation queue
model loading
context window
GPU scheduling
```

unless an actual failure occurs.

---

# 56. Core Strategic Thesis

The project should not compete by saying:

> “We have a better translation model.”

It should compete by building a better system around existing and future models:

```text
Better capture
      +
better streaming ASR
      +
better incremental translation
      +
better context
      +
better revision
      +
better model selection
      +
better runtime optimization
      +
better packaging
```

The central research/product problem is therefore:

> **How can a local system produce increasingly accurate natural English continuously, with minimal visible delay and minimal resource consumption?**

---

# 57. What Must Not Drift

Future implementation decisions must preserve these five principles:

```text
1. Local-first
2. Realtime-first UX
3. Progressive refinement
4. Model/runtime replaceability
5. Lightweight end-user experience
```

A feature or technology that improves theoretical quality but significantly violates these principles must be treated as an explicit trade-off, not silently adopted.

---

# 58. Current Open Questions

The following are intentionally unresolved.

```text
UNKNOWN — REQUIRES VALIDATION

1. Which streaming ASR gives the best quality/latency trade-off
   on common consumer CPUs?

2. Which multilingual MT family provides the best
   quality/latency/license combination?

3. Whether CTranslate2, ONNX Runtime, or another runtime
   should become the primary MT execution layer.

4. Whether Rust or C++ provides the best production runtime boundary.

5. Whether WebGPU can serve as an optional acceleration backend.

6. The correct incremental translation/revision algorithm.

7. The minimum practical model pack size.

8. Target CPU/RAM/GPU baseline for supported users.

9. Exact end-to-end latency SLO.

10. Exact model distribution and update mechanism.
```

These questions must be resolved by **benchmarking and experiments**, not assumptions.

---

# 59. Final Architecture Baseline

The current canonical architecture is:

```text
                     USER
                      │
                      ▼
              ┌───────────────┐
              │ Chrome        │
              │ Extension     │
              │               │
              │ Capture       │
              │ UI            │
              │ Subtitle      │
              │ Settings      │
              └───────┬───────┘
                      │
               Native Messaging
                      │
                      ▼
              ┌───────────────┐
              │ Local Runtime │
              │               │
              │ VAD           │
              │ ASR           │
              │ Segmentation  │
              │ Context       │
              │ Translation   │
              │ Revision      │
              │ Scheduling    │
              └───────┬───────┘
                      │
             ┌────────┼────────┐
             ▼        ▼        ▼
            ASR       MT      Optional
          Runtime   Runtime    LLM
             │        │        │
             └────────┼────────┘
                      ▼
              Subtitle Events
                      │
                      ▼
              Chrome Renderer
```

Bên ngoài runtime:

```text
        Language Intelligence
                 │
                 ▼
           Context / Terms
                 │
                 ▼

        MLOps / Evaluation
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
     Dataset   Replay   Benchmark
```

Đây là **architecture baseline**, không phải danh sách dependency cố định.

---

# 60. Architectural North Star

`youtube-live-translater` should ultimately feel like:

```text
Install
   ↓
Open YouTube
   ↓
Enable translation
   ↓
Speech appears
   ↓
English appears almost immediately
   ↓
English naturally reorganizes as context arrives
   ↓
Sentence settles into a high-quality final translation
```

while internally operating as:

```text
Edge AI
+
Streaming Systems
+
Incremental NLP
+
Optimized Inference
+
Local Runtime Engineering
+
MLOps
```

The engineering complexity belongs inside the system.

The user's experience should remain simple.
