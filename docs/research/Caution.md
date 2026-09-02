# youtube-live-translater — Caution Research

> **Research Snapshot:** 31 August 2026
> **Purpose:** Record the principal risks, uncertainties, guardrails, and validation requirements that must govern research and development of `youtube-live-translater`.
> **Status:** Architectural caution baseline

---

# 1. Purpose

`youtube-live-translater` combines several difficult domains:

```text
Streaming ASR
+
Machine Translation
+
Incremental Translation
+
Context Management
+
Local AI Inference
+
Browser Integration
+
Native Runtime
+
MLOps
```

The central risk is not that any individual component is impossible.

The central risk is that **the combined system becomes too complex, too slow, too large, too fragile, or too difficult to validate on ordinary consumer hardware**.

This document exists to prevent that failure mode.

The project must therefore follow:

> **Evidence before complexity. Benchmark before optimization. Baseline before novelty.**

---

# 2. Primary Safety Principle

The project must not attempt to solve every difficult problem simultaneously.

Preferred progression:

```text
working baseline
      ↓
measurement
      ↓
identified bottleneck
      ↓
one controlled improvement
      ↓
measurement
      ↓
comparison
```

Never:

```text
new ASR
+
new MT
+
new frontier
+
new context system
+
LLM
+
new runtime
```

in one experiment.

---

# 3. Risk Classification

Every major uncertainty should be classified as:

### Evidence-backed

Supported by:

* peer-reviewed research
* official documentation
* reproducible benchmark
* source code
* controlled experiment

### Engineering Inference

Reasoned conclusion derived from several evidence sources.

### Hypothesis

Promising idea that has not yet been experimentally demonstrated.

The project must never present a **Hypothesis** as an established result.

---

# 4. Risk Register

| Risk                        |    Severity | Primary Mitigation             | Validation Gate                      |
| --------------------------- | ----------: | ------------------------------ | ------------------------------------ |
| System complexity explosion |    Critical | staged architecture            | each stage benchmarked independently |
| Local LLM latency           |        High | remove from MVP hot path       | measured E2E latency                 |
| ASR latency                 |    Critical | hardware benchmark matrix      | RTF + E2E benchmark                  |
| Translation latency         |    Critical | optimized local MT runtime     | E2E benchmark                        |
| Frontier instability        |        High | LCP baseline first             | revision-cost benchmark              |
| YouTube capture failure     |    Critical | early browser POC              | 60-minute capture test               |
| Native Messaging friction   |        High | one-click installer            | fresh-machine install test           |
| Model footprint             |        High | model profiles + lazy loading  | disk/RAM benchmark                   |
| Long-session drift          |    Critical | bounded state + health control | 60+ minute test                      |
| Language coverage           |    Critical | measured language tiers        | per-language benchmark               |
| ASR error propagation       |        High | ASR-noise evaluation           | noisy-ASR MT benchmark               |
| Model licensing             |    Critical | model registry/license gate    | pre-distribution audit               |
| Thermal throttling          |        High | long-duration profiling        | thermal/resource test                |
| Browser API changes         | Medium/High | adapter boundary               | integration regression tests         |
| Model regression            |        High | replay-based MLOps             | benchmark regression gate            |

---

# 5. Risk #1 — Complexity Explosion

## Problem

The full vision includes:

```text
Streaming ASR
Fast MT
Adaptive Frontier
Context
Selective LLM
MLOps
Cross-platform
Packaging
```

Each area can independently become a major engineering/research project.

### Failure mode

The project reaches:

```text
everything implemented
```

but:

```text
nothing measurable
nothing replaceable
nothing clearly responsible for improvement
```

## Guardrail

The project must use progressive capability levels:

```text
Level 0
offline ASR → MT

Level 1
realtime ASR → MT

Level 2
+ LCP stabilization

Level 3
+ adaptive WAIT/WRITE

Level 4
+ bounded context

Level 5
+ selective reasoning

Level 6
+ production resource adaptation
```

### Rule

> **Do not add Level N+1 until Level N has a reproducible benchmark.**

---

# 6. Risk #2 — Local LLM Becomes the Bottleneck

## Problem

A local LLM may be more computationally expensive than ASR + MT.

This can violate the core product promise:

```text
immediate translation
```

if the system becomes:

```text
ASR
 ↓
LLM
 ↓
translation
```

## Guardrail

The MVP contains:

```text
Audio
 ↓
VAD
 ↓
ASR
 ↓
MT
 ↓
stability
 ↓
subtitle
```

No mandatory LLM.

LLM is an optional capability activated only when:

```text
uncertainty is high
AND
expected benefit > expected cost
```

Potential uses:

```text
slang
ambiguity
contextual repair
terminology disambiguation
```

### Status

```text
Selective local reasoning
= research capability

LLM on critical path
= prohibited for MVP
```

---

# 7. Risk #3 — ASR RTF Is Not End-to-End Latency

## Problem

A system may have:

```text
RTF < 1
```

and still feel slow.

Example:

```text
buffering
+
ASR
+
queue
+
MT
+
revision
+
rendering
```

can accumulate multiple seconds of perceived delay.

## Required Metrics

Measure:

```text
capture latency
buffer latency
ASR latency
MT latency
revision latency
render latency
```

and:

$$
L_{E2E} = T_{render} - T_{speech}
$$

RTF remains useful, but only as one component.

## Required benchmark dimensions

```text
hardware
×
ASR model
×
model size
×
quantization
×
window/chunk configuration
```

Measure:

```text
TTFP
E2E latency
RTF
CPU
RAM
GPU
VRAM
startup
```

---

# 8. Risk #4 — Adaptive Translation Frontier Is Underspecified

## Problem

The architecture currently describes:

```text
hypothesis
 ↓
stability
 ↓
COMMIT / WAIT / REVISE
```

but "stability" is not yet a precise algorithm.

Possible definitions include:

```text
character LCP
token LCP
Local Agreement
confidence
translation divergence
semantic similarity
linguistic completeness
```

## Guardrail

Development order:

```text
LCP
 ↓
Local Agreement
 ↓
adaptive WAIT/WRITE
 ↓
semantic stability
```

### Baseline requirement

`LCP` becomes the initial measurable baseline because comparable recent research uses longest-common-prefix style stabilization.

Source:

https://aclanthology.org/2026.iwslt-1.30/

### Rule

> **Do not claim semantic stability is superior until it beats LCP experimentally.**

### Stage S4 Resolution (September 2026)
Stage S4 empirically implemented and validated **Local Agreement ($K=2$) + Adaptive Frontier ($W=2$)** (`S4 Functional / Contract = PASS`, `S4 Perceptual UX = OPEN`):
- **Committed-Prefix Immutability Verified:** Zero committed revisions ($\text{revisions} = 0$), sub-millisecond overhead ($\text{p50} = 0.029\text{ ms}$), and $82.7\%$ MT call reduction.
- **Architectural Rule on Conflict Semantics:** Committed output is a temporal UX stability guarantee, not a guarantee that already-committed text is semantically correct under arbitrary later ASR corrections.
- **Handoff to S5:** Perceptual flicker reduction requires Stage S5 anchored layout rendering (solid committed text + dimmed provisional tail without line reflow). See [`ADR-006`](../adr/ADR-006-incremental-translation-frontier.md) and [`s4-incremental-translation.md`](s4-incremental-translation.md).

---

# 9. Risk #5 — YouTube Integration Is an Unverified Boundary

The AI pipeline is irrelevant if browser audio capture is unreliable.

Potential issues:

```text
VOD vs Live
audio routing
codec/sample rate
tab lifecycle
pause/resume
quality changes
ads
browser changes
protected content
long-session behavior
```

`chrome.tabCapture` provides the relevant capture primitive, but the actual production behavior must be validated experimentally.

Source:

https://developer.chrome.com/docs/extensions/reference/api/tabCapture

The Offscreen API is also relevant for extension functionality that requires a document context.

Source:

https://developer.chrome.com/docs/extensions/reference/api/offscreen

## Mandatory POC

Test:

```text
VOD
Live
low/high quality
pause/resume
fullscreen
tab switching
ad transitions
long-running streams
```

Acceptance:

```text
✓ audio captured
✓ original audio remains usable
✓ no periodic dropouts
✓ timestamps stable
✓ no progressive latency drift
✓ 60-minute session passes
```

### Stage S5 Resolution (September 2026)
Stage S5 implemented and verified the **Extension UI & Native Host Integration** (`S5 Verdict = PASS`):
- **Anchored Presentation Verified:** $\text{anchor\_displacement} = 0.0000\text{px}$ under continuous provisional updates.
- **End-to-End Pipeline Verified:** Ingests live audio $\to$ Zipformer (S2) $\to$ Marian INT8 (S3) $\to$ Incremental Translator (S4) $\to$ Extension Overlay (S5).
- **Sub-Millisecond Dispatch Latency:** $\text{p50} = 0.000\text{ ms}$, $\text{p95} = 0.001\text{ ms}$. See [`ADR-007`](../adr/ADR-007-extension-renderer-and-native-host-integration.md) and [`s5-extension-ui-native-host.md`](s5-extension-ui-native-host.md).

---

# 10. Risk #6 — DRM/Protected Playback Assumptions

Do not assume:

```text
DRM always blocks capture
```

or:

```text
tabCapture captures everything
```

Both are unsafe architectural assumptions.

The system must establish actual behavior through controlled testing.

### Status

```text
UNKNOWN — REQUIRES VALIDATION
```

---

# 11. Risk #7 — Native Messaging Installation Friction

Architecture:

```text
Extension
 ↓
Native Messaging
 ↓
Local Runtime
```

creates a genuine deployment cost.

Different platforms require different host installation mechanisms.

Chrome's Native Messaging architecture requires a registered native host and an explicit extension authorization relationship.

Source:

https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging

## Guardrail

The user should not interact with:

```text
manifest
registry
PATH
runtime dependencies
Python
CUDA
```

directly.

Preferred UX:

```text
Install Extension
       ↓
Install Runtime
       ↓
Detect Hardware
       ↓
Recommended Model
```

The implementation should hide platform-specific details inside installers.

---

# 12. Risk #8 — Model Footprint Contradicts "Lightweight"

An extension can be tiny while the model installation is gigabytes.

Therefore:

```text
lightweight extension
≠
lightweight product
```

Footprint must be separated into:

```text
installer
runtime
active model
model cache
```

## Guardrail

Use:

```text
lazy model download
+
model profiles
+
cache management
```

Example:

```text
Starter
Balanced
Quality
```

The product must not automatically download every available model.

---

# 13. Risk #9 — "Any Language" Is an Unrealistic Undifferentiated Promise

Multilingual support is not binary.

A language may have:

```text
excellent ASR
good MT
poor MT
poor ASR
little benchmark data
high compute cost
```

Therefore:

```text
196 languages supported
```

does not imply:

```text
196 languages have equal quality
```

## Guardrail

Use measured support tiers:

```text
Tier A
High-confidence

Tier B
Usable

Tier C
Experimental
```

The supported-language matrix must be based on benchmark evidence.

---

# 14. Risk #10 — ASR Errors Propagate Into MT

Cascaded architecture:

```text
ASR
 ↓
MT
```

has a structural failure mode:

```text
ASR error
 ↓
incorrect source text
 ↓
incorrect translation
```

Recent simultaneous translation work has explored training translation systems against realistic ASR noise.

Example:

Pinch-AST uses ASR-noise-augmented data in its translation pipeline.

Source:

https://aclanthology.org/2026.iwslt-1.30/

## Guardrail

Translation evaluation must include:

```text
clean transcript
```

and:

```text
realistic ASR output
```

not only clean parallel text.

---

# 15. Risk #11 — Long-Session Latency Drift

## Failure modes

```text
memory accumulation
queue growth
context growth
thermal throttling
fragmentation
repeated re-decoding
```

A system that works for 2 minutes may fail after 60 minutes.

## Guardrails

Every major state must be bounded:

```text
audio queue
ASR state
context
translation history
revision state
```

No component may silently grow forever.

---

# 16. Runtime Health Model

The runtime should expose explicit states:

```text
NORMAL
CONSTRAINED
DEGRADED
RECOVERING
```

Potential triggers:

```text
RTF rising
queue growth
RAM growth
VRAM pressure
thermal pressure
runtime failure
```

Example:

```text
GPU pressure
→ smaller model

CPU overload
→ lower inference profile

LLM overload
→ disable optional LLM

memory anomaly
→ flush/reinitialize component
```

---

# 17. Risk #12 — Restart Strategy

Do not use:

```text
restart everything every N minutes
```

as a generic solution.

Instead use two recovery levels.

### Soft recovery

```text
flush stale context
restart subsystem
reset bounded buffer
```

### Hard recovery

```text
restart native process
restore session configuration
reload required state
```

Failures should remain isolated.

Example:

```text
ASR crash
→ restart ASR

LLM crash
→ disable LLM

runtime crash
→ restart runtime
```

---

# 18. Risk #13 — Model Licensing

Technical quality does not imply redistribution rights.

For every model artifact record:

```text
model
version
license
language coverage
commercial-use status
redistribution status
quantization artifact status
attribution requirements
```

Example:

`facebook/nllb-200-distilled-600M` is listed as **CC-BY-NC-4.0** on its Hugging Face model card.

Source:

https://huggingface.co/facebook/nllb-200-distilled-600M

Therefore:

> Model selection must include license selection.

A model cannot be bundled merely because it is technically excellent.

---

# 19. Risk #14 — Thermal Throttling

A consumer laptop can behave differently after:

```text
30 seconds
```

versus:

```text
30 minutes
```

Therefore benchmark:

```text
cold
warm
long-running
```

states.

Record:

```text
CPU frequency
CPU utilization
temperature where available
RTF
latency
RAM
GPU load
VRAM
```

The system must optimize sustained performance, not benchmark peaks.

---

# 20. Risk #15 — Browser Changes

YouTube and browser APIs evolve.

The AI runtime must therefore avoid dependencies on:

```text
YouTube internal APIs
DOM structure for audio extraction
private media endpoints
fragile player implementation details
```

The browser adapter should be isolated:

```text
Chrome adapter
Firefox adapter
Edge adapter
```

from:

```text
Common Runtime Protocol
```

---

# 21. Risk #16 — Semantic Stability May Be Too Expensive

Semantic stability is attractive:

```text
"I went to the shop"
```

vs

```text
"I went to that store"
```

may be semantically equivalent.

But semantic comparison can itself require expensive inference.

Therefore:

```text
semantic stability
```

must not be assumed to be computationally cheap.

## Guardrail

Research order:

```text
LCP
→ token/phrase heuristics
→ lightweight similarity
→ semantic model
```

Only adopt a higher-level method if its quality gain exceeds its compute cost.

---

# 22. Risk #17 — Context Becomes Another Hidden Memory Leak

Context systems often start small and become:

```text
full livestream transcript
+
all translations
+
all terminology
+
all embeddings
```

This violates the local resource constraint.

## Guardrail

Context must have explicit layers:

```text
L0 current audio
L1 current segment
L2 recent turns
L3 active terminology
L4 relevant semantic memory
```

Every layer requires:

```text
maximum size
eviction rule
lifetime
```

No unbounded context.

---

# 23. Risk #18 — MLOps Overengineering

It is easy to turn:

```text
MLOps
```

into:

```text
Kubernetes
Kafka
Redis
Airflow
Ray
MLflow
distributed model serving
```

without needing them.

## Guardrail

Initial MLOps only requires:

```text
datasets
+
replay
+
benchmark runner
+
model metadata
+
regression reports
```

Distributed infrastructure is justified only by a demonstrated bottleneck.

---

# 24. Risk #19 — Multi-variable Experiments

Changing many variables simultaneously makes results uninterpretable.

Bad:

```text
new ASR
+
new MT
+
new policy
+
new runtime
```

Good:

```text
E001
baseline

E002
ASR changed

E003
MT changed

E004
LCP added

E005
adaptive policy added
```

## Rule

> **One principal experimental variable per experiment.**

Secondary changes must be explicitly recorded.

---

# 25. Risk #20 — Optimizing the Wrong Metric

Traditional metrics alone are insufficient.

A model can have:

```text
higher BLEU
```

but:

```text
worse latency
worse RAM
worse revision
worse user experience
```

Therefore the project uses a multidimensional evaluation model:

```text
Quality
+
Latency
+
Revision Cost
+
Resource Cost
```

---

# 26. Revision Cost

A proposed product-specific metric:

```text
small textual revision
=
small cost

large visible rewrite
=
large cost
```

This lets the system measure subtitle stability.

It should eventually be paired with:

```text
quality
latency
resource usage
```

to evaluate the actual product objective.

---

# 27. Core Benchmark Baselines

The research program should maintain explicit baselines:

```text
Baseline A
fixed chunk + ASR + MT

Baseline B
retranslation + LCP

Baseline C
Local Agreement

Baseline D
adaptive READ/WRITE

Candidate E
Adaptive Translation Frontier

Candidate F
semantic stability
```

Every candidate must demonstrate measurable benefit over an earlier baseline.

---

# 28. Minimum Feasibility Gate

Before sophisticated AI research continues, the following must work:

```text
YouTube
 ↓
audio capture
 ↓
ASR
 ↓
MT
 ↓
subtitle
```

with:

```text
real-time operation
+
bounded queue
+
stable session
```

If this cannot run acceptably on target hardware, advanced modules are postponed.

---

# 29. Minimum MVP

### Mandatory

```text
Chrome Extension
Local Runtime
Audio Capture
ASR
MT
LCP stabilization
basic resource management
basic recovery
```

### Deferred

```text
Adaptive WAIT/WRITE
advanced context
semantic stability
selective LLM
cross-platform browsers
advanced MLOps
```

This is a deliberate scope boundary.

---

# 30. Technology Selection Rule

No component is selected because it is:

```text
newest
most popular
largest
most impressive
```

Selection requires evidence across:

```text
quality
latency
memory
CPU
GPU
streaming capability
cross-platform support
license
maturity
packaging complexity
replaceability
```

---

# 31. Model Selection Rule

A model is acceptable only if:

```text
quality acceptable
+
latency acceptable
+
resource footprint acceptable
+
license acceptable
+
distribution acceptable
```

A model that fails any critical constraint should not silently become the production default.

---

# 32. "Lightweight" Definition

For this project, lightweight means:

```text
small initial installer
+
small runtime
+
reasonable active model footprint
+
bounded RAM
+
bounded CPU/GPU
+
fast startup
+
low operational friction
```

It does **not** necessarily mean:

```text
the entire product including every model < 100 MB
```

The latter may be unrealistic.

---

# 33. End-User Hardware Policy

The supported hardware baseline must be empirical.

Do not initially promise:

```text
works on every laptop
```

Instead define:

```text
Supported
Degraded but usable
Experimental
Unsupported
```

after benchmarks.

---

# 34. Long-Session Test Policy

Every production candidate must be tested at:

```text
30 seconds
10 minutes
30 minutes
60 minutes+
```

Record:

```text
latency drift
queue size
memory
CPU
GPU
VRAM
thermal state
errors
restarts
subtitle stability
```

A candidate that only passes short tests is not production-ready.

---

# 35. Failure Philosophy

The system should:

> **degrade before it crashes.**

Preferred sequence:

```text
Quality degradation
      ↓
optional feature disabled
      ↓
smaller model
      ↓
reduced context
      ↓
component restart
      ↓
runtime restart
```

rather than:

```text
small resource problem
      ↓
whole translation system fails
```

---

# 36. Security Guardrails

The browser/runtime boundary must enforce:

```text
explicit authorization
+
strict input validation
+
restricted native host
+
no arbitrary process execution
+
no unnecessary localhost server
+
safe model artifacts
+
controlled filesystem access
```

---

# 37. Privacy Guardrails

Default behavior:

```text
audio → local
ASR → local
translation → local
context → local
```

No cloud upload should be required.

Future telemetry must not implicitly become collection of:

```text
raw audio
full transcripts
private conversations
```

without explicit product/legal review and user consent where applicable.

---

# 38. Research Anti-Patterns

Do not:

```text
❌ start with Kubernetes
❌ start with distributed inference
❌ make LLM mandatory
❌ assume NLLB is the final MT choice
❌ assume Whisper is the final ASR choice
❌ optimize only BLEU/WER
❌ use fixed chunking forever
❌ retain unlimited context
❌ bundle every model
❌ couple AI logic to YouTube DOM
❌ benchmark only short sessions
❌ change five components in one experiment
❌ call an untested idea "production-ready"
```

---

# 39. Research Decision Gate

Before adding any major technology, answer:

```text
1. What problem does it solve?

2. What metric does it improve?

3. How much compute does it add?

4. Does it increase memory footprint?

5. Does it increase latency?

6. Does it increase packaging complexity?

7. Does it introduce a new failure mode?

8. Can the improvement be measured?

9. Can it be removed without redesigning the system?

10. Does it preserve the local-first product contract?
```

If these questions cannot be answered, the technology should remain in research.

---

# 40. Architecture Guardrails

The following remain non-negotiable:

```text
Local-first
Realtime-first UX
Progressive refinement
Model/runtime replaceability
Bounded state
Resource awareness
Replayability
Measured language support
Production-grade packaging
```

---

# 41. Current Strategic Position

The project should not attempt to beat the research field by training a new foundation model.

The stronger strategy is:

```text
existing strong models
        +
optimized runtime
        +
adaptive policy
        +
context management
        +
revision/stability
        +
resource-aware scheduling
        +
careful packaging
```

The research contribution, if validated, may emerge from how these pieces are orchestrated under strict consumer-device constraints.

---

# 42. Research Hypothesis Under Caution

### Adaptive Translation Frontier

Potential state:

```text
WAIT
PARTIAL
COMMIT
REVISE
FINALIZE
```

Potential inputs:

```text
ASR confidence
translation divergence
linguistic completeness
semantic stability
context
latency budget
resource budget
```

Potential objective:

```text
maximize translation quality
while minimizing
latency
revision cost
compute cost
memory cost
```

### Important qualification

This is:

```text
RESEARCH HYPOTHESIS
```

not:

```text
ESTABLISHED RESULT
```

It must beat LCP/Local Agreement/adaptive baselines before becoming a claimed project contribution.

---

# 43. Final Research Discipline

The project follows this loop:

```text
Research
   ↓
Hypothesis
   ↓
Baseline
   ↓
Experiment
   ↓
Benchmark
   ↓
Compare
   ↓
Decision
   ↓
ADR / documentation
   ↓
Implementation
```

Never:

```text
interesting technology
   ↓
integrate immediately
```

---

# 44. Final North Star

The system must remain aligned with the actual product:

```text
User opens YouTube
       ↓
Enables translation
       ↓
Speaker starts talking
       ↓
Useful English appears quickly
       ↓
Output improves as context arrives
       ↓
Only uncertain regions are revised
       ↓
Final translation settles naturally
```

The internal system may be sophisticated.

The user's installation and experience must remain simple.

---

# 45. Final Rule

> **Do not make `youtube-live-translater` impressive by adding more technology. Make it impressive by extracting more user-perceived intelligence from less compute, while proving every major improvement with reproducible evidence.**
