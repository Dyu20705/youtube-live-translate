# ADR-007: Extension Presentation Layer & Native Host Integration

**Status:** Accepted
**Date:** 2026-09-02
**Deciders:** Core Engineering Team
**Consulted:** Stage S5 Empirical Research Report ([`docs/research/s5-extension-ui-native-host.md`](file:///home/duy/Code/tools/youtube-live-translate/docs/research/s5-extension-ui-native-host.md))

---

## 1. Context and Problem Statement

In Stage S4, we verified that the Local Agreement ($K=2$) + Adaptive Frontier ($W=2$) policy guarantees committed prefix immutability ($\text{committed prefix revisions} = 0$) with sub-millisecond policy overhead ($\text{p50} = 0.029\text{ ms}$). However, the S4 research audit proved that **backend translation policy alone cannot eliminate subtitle flicker if the frontend UI renders the full text as an unanchored, monolithic string**, because the uncommitted provisional tail fluctuates as sentence context arrives.

Stage S5 was charged with:
1. Implementing an **Anchored Layout & Stable Subtitle Presentation Layer** in a Manifest V3 Chrome Extension.
2. Eliminating spatial displacement and line reflow on already-read committed text ($\text{anchor displacement} = 0\text{ px}$).
3. Establishing a versioned wire protocol (`v1.0`) and bridging the frozen S2 Zipformer ASR + S4 Incremental Translator Python runtime with the browser extension.
4. Implementing frame coalescing via `requestAnimationFrame` and backpressure protection (stale provisional frames dropped, committed frames never lost).
5. Defining graceful degraded/error states when native bridges disconnect.

---

## 2. Decision: Four-Layer Decoupled Architecture

We designed a strict 4-layer architecture with zero coupling between DOM rendering and MT internals:

```text
┌────────────────────────────────────────────────────────┐
│ S5 Subtitle Presentation Layer (DOM/CSS)               │
│ - Dedicated Anchored Committed Box (100% Solid)        │
│ - Attached Secondary Provisional Box (65% Dimmed)      │
│ - Stable text baseline (0px anchor displacement)       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Subtitle State Adapter (JavaScript)                    │
│ - Monotonic (segment_id, revision) stale rejection     │
│ - Duplicate state filtering                            │
│ - Frame coalescing (requestAnimationFrame)             │
│ - Segment lifecycle state machine                      │
└───────────────────────────┬────────────────────────────┘
                            │ Chrome Messaging / WebSocket
┌───────────────────────────▼────────────────────────────┐
│ Native Host / Local Runtime Bridge (Python)            │
│ - Chrome Native Messaging (stdio) + WebSocket Server   │
│ - Ingests 16kHz PCM audio from S1 tab capture          │
│ - Drives Frozen S2 Zipformer ASR + S4 Incremental MT   │
│ - Serializes Version 1.0 JSON Wire Protocol            │
└────────────────────────────────────────────────────────┘
```

---

## 3. The Anchored Layout Contract

### 3.1 Dual-Container Subtitle Structure
```html
<div id="ylt-subtitle-viewport" class="ylt-viewport">
  <div class="ylt-subtitle-line">
    <span class="ylt-committed-box"><span class="ylt-committed-text">Committed Text</span></span>
    <span class="ylt-provisional-box"><span class="ylt-provisional-text"> provisional text...</span></span>
  </div>
</div>
```

### 3.2 Visual Hierarchy & Invariants
- **Committed Box:** Solid 100% opacity, standard font weight, anchored to the line origin. When provisional text mutates or changes length, the committed DOM node and its spatial bounding box **never move** ($\Delta \text{left} = 0\text{ px}$, $\Delta \text{top} = 0\text{ px}$).
- **Provisional Box:** Dimmed 65% opacity, italic style, attached to the tail of the committed box.
- **Zero Full-Node Replacements:** DOM mutations are targeted exclusively to the modified text span (`.textContent = ...`). Full container teardowns and `innerHTML` replacements are strictly avoided.

---

## 4. Empirical Benchmark Summary

| Evaluation Dimension | Metric Type | Raw Unified UI | S5 Anchored Dual-Box UI | Target Limit |
| :--- | :---: | :---: | :---: | :---: |
| **Max Anchor Displacement** | Spatial Invariant | 239.40 px (FAILED) | **0.0000 px** (PASS) | $= 0.0\text{ px}$ |
| **Avg Anchor Displacement** | Spatial Invariant | 80.27 px | **0.0000 px** | $= 0.0\text{ px}$ |
| **Full-Node DOM Replacements** | Rendering Overhead | 19 | **0** (PASS) | $= 0$ |
| **Duplicate Events Filtered** | Efficiency | 0 | **78** (PASS) | $> 0$ |
| **Render Dispatch Latency (p50)** | Latency | $< 0.05\text{ ms}$ | **0.000 ms** (PASS) | $< 16.0\text{ ms}$ |
| **Render Dispatch Latency (p95)** | Latency | $< 0.08\text{ ms}$ | **0.001 ms** (PASS) | $< 33.0\text{ ms}$ |
| **Spatial Anchoring Invariant** | Correctness | FAILED | **PASS (100% Stable)** | PASS |

---

## 5. Security & Isolation Controls

- **Origin Validation:** Native host and WebSocket bridge accept connections only from local loopback (`127.0.0.1`) and registered extension ID.
- **Minimal Schema Surface:** Wire protocol exposes only structured subtitle/status events; no arbitrary shell execution or filesystem access is exposed over the boundary.
- **Graceful Degradation:** Native bridge disconnects trigger `DEGRADED` state and display a subtle indicator without crashing YouTube pages.

---

## 6. Consequences & Next Steps

### Positive
- Subtitle flicker is structurally and visually eliminated: already-read words remain completely motionless on screen.
- Sub-millisecond rendering latency ensures zero contribution to perceived latency.
- Full end-to-end integration verified: Audio Capture (S1) $\to$ Zipformer (S2) $\to$ Marian INT8 (S3) $\to$ Incremental Translator (S4) $\to$ Anchored Presentation (S5).
- All frozen S2 contracts and S3/S4 regressions pass 100%.

### Status
Stage S5 is accepted as **`PASS`**.
