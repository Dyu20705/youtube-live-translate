# ADR-002: Real-Time In-Browser Audio Preprocessing & Resampling Contract

**Status:** Accepted (Reconstructed from Stage S1/S2 Integration)
**Date:** 2026-09-01
**Deciders:** Core Engineering Team
**Consulted:** Stage S1 Research Report ([`docs/research/s1-audio-capture.md`](../research/s1-audio-capture.md)), [`ADR-004`](ADR-004-s2-performance-contract.md)

---

## 1. Context and Problem Statement

Downstream Automatic Speech Recognition (ASR) engines (Sherpa-ONNX Zipformer Transducer and Whisper) strictly require **16,000 Hz single-channel (mono) 16-bit linear PCM audio**.

However, browser tab audio captured from YouTube is delivered at variable native sample rates (typically 48,000 Hz or 44,100 Hz) in stereo (2 channels) with 32-bit floating-point samples ($[-1.0, 1.0]$).

We needed to decide whether to perform resampling and channel mixing:
1. Inside the browser extension before transmission, or
2. Inside the local native runtime process after network/IPC transmission.

---

## 2. Decision: In-Browser Resampling via AudioWorklet

We decided to execute audio downsampling and format normalization directly inside the browser extension using a dedicated `AudioWorkletProcessor` (`audio-processor.js`) with a `ScriptProcessor` fallback:

1. **Format Normalization:** Native 48kHz/44.1kHz stereo Float32 is downsampled to 16,000 Hz mono 16-bit signed integer linear PCM (`pcm_s16le`).
2. **Allocation-Free Hot Path:** Working typed arrays are pre-allocated during worklet initialization. The `process()` loop performs zero dynamic heap allocations, achieving an average execution time of **$0.567\ \mu\text{s}$ per 128-sample call**.
3. **Bandwidth Reduction:** Transmitting 16kHz mono 16-bit PCM reduces network/IPC payload volume by **$83.3\%$** compared to sending raw 48kHz stereo Float32 audio over the transport boundary ($32\text{ KB/s}$ vs $192\text{ KB/s}$).

---

## 3. The S1/S2 Audio Ingest Contract

The following binary audio contract is established as an invariant for all downstream components:

```text
┌────────────────────────────────────────────────────────┐
│ Stage S1 / S2 Audio Ingest Contract                    │
├────────────────────────────────────────────────────────┤
│ Sample Rate   : 16,000 Hz                              │
│ Channels      : 1 (Mono)                               │
│ Sample Format : 16-bit Signed Integer Linear PCM       │
│ Byte Order    : Little-Endian (pcm_s16le)              │
│ Scale Factor  : 1.0 / 32768.0                          │
│ Chunk Cadence : 128 ms (~2048 samples / chunk)         │
└────────────────────────────────────────────────────────┘
```

---

## 4. Consequences

### Positive
- Dramatically lowers IPC transport bandwidth between Chrome and the local native runtime.
- Eliminates CPU resampling overhead inside Python inference processes.
- Enforces a deterministic, frozen audio format boundary for all ASR engines.

### Negative / Trade-offs
- Requires maintaining an `AudioWorklet` processor module inside the Chrome extension bundle.
- Requires a fallback `ScriptProcessorNode` for environments where AudioWorklet module loading is restricted.
