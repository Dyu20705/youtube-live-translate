# Stage S4 — Incremental Translation & Adaptive Frontier Stabilization

This directory contains the implementation and reproducible empirical benchmark suite for **Stage S4: Incremental Translation & Adaptive Frontier Stabilization**.

---

## 1. Overview

Stage S4 implements a deterministic, stateful streaming translation layer positioned between frozen Stage S2 streaming ASR and Stage S3 Marian CTranslate2 INT8 MT.

```text
[Frozen S2 Streaming ASR (Zipformer)]
                 │
                 ▼ (ASR Partial / Final Revisions)
┌─────────────────────────────────────────────────────────┐
│     STAGE S4 INCREMENTAL STREAMING TRANSLATOR            │
│                                                         │
│  1. Input Deduplication & MT Call Optimizer             │
│  2. Translation Engine Interface (S3 Marian INT8)        │
│  3. Local Agreement Engine (Configurable K)             │
│  4. Adaptive Frontier Controller (Buffer, Boundaries)   │
│  5. Output Contract (Committed Prefix + Suffix)         │
└─────────────────────────────────────────────────────────┘
                 │
                 ▼
[Committed Prefix (Immutable) + Provisional Suffix (Revisable)]
```

### Core Invariants
1. **Committed Prefix Immutability:** `committed_prefix` MUST NEVER mutate or shrink within the same active segment (`committed_prefix_revision_count = 0`).
2. **Deterministic & Model-Free:** Pure deterministic algorithms (Local Agreement + LCP + Adaptive Frontier) on CPU without neural models or LLMs.
3. **Engine-Agnostic Interface:** Interfaces with any `MTEngine` conforming to the Stage S3 abstract contract.

---

## 2. Directory Structure

```
poc/s4-incremental-translation/
├── README.md
├── policy/
│   ├── __init__.py
│   ├── state_model.py             # SegmentStatus, PolicyConfig, SubtitleState, SessionMetrics
│   ├── agreement.py               # Tokenization, detokenization, LCP, LocalAgreementTracker
│   ├── frontier.py                # AdaptiveFrontierController & boundary decision logic
│   └── streaming_translator.py    # Stateful IncrementalTranslator state machine
├── metrics/
│   ├── __init__.py
│   └── s4_metrics.py              # TPS, revision counts, commit delays, overhead distributions
├── benchmark/
│   ├── __init__.py
│   ├── s4_benchmark.py            # Comparative benchmark (S3 Naive vs S4 Adaptive Frontier)
│   └── run_s4_benchmark.py        # CLI benchmark runner & evidence JSON generator
└── tests/
    ├── conftest.py                # Mock engines and pytest fixtures
    ├── test_state_model.py        # Unit tests for state models & serialization
    ├── test_agreement.py          # Unit tests for tokenization & Local Agreement
    ├── test_frontier.py           # Unit tests for Adaptive Frontier & conflicts
    ├── test_s4_metrics.py         # Unit tests for stability metrics
    ├── test_adversarial_fixtures.py # 10 adversarial streaming fixtures
    └── test_s4_integration.py     # E2E S2 Zipformer -> S4 -> Marian INT8 integration test
```

---

## 3. Quick Start & Reproduction

### Run Unit and Integration Tests
```bash
PYTHONPATH=poc/s4-incremental-translation:poc/s3-local-mt:poc/s2-streaming-asr \
/home/duy/Code/tools/youtube-live-translate/poc/s2-streaming-asr/.venv/bin/pytest \
poc/s4-incremental-translation/tests/ -v
```

### Run S4 Empirical Benchmark
```bash
PYTHONPATH=poc/s4-incremental-translation:poc/s3-local-mt \
/home/duy/Code/tools/youtube-live-translate/poc/s2-streaming-asr/.venv/bin/python \
poc/s4-incremental-translation/benchmark/run_s4_benchmark.py
```

---

## 4. Architectural Decision Summary

- **Policy:** Local Agreement ($K=2$) with Adaptive Frontier and protected unstable buffer ($W=2$).
- **Primary Engine:** Helsinki-NLP `opus-mt-ja-en` (Marian CTranslate2 INT8).
- **Evidence Documentation:**
  - Full Empirical Research Report: [`docs/research/s4-incremental-translation.md`](../../docs/research/s4-incremental-translation.md)
  - Architectural Decision Record: [`docs/adr/ADR-006-incremental-translation-frontier.md`](../../docs/adr/ADR-006-incremental-translation-frontier.md)
  - Raw JSON Measurements: [`docs/evidence/s4-incremental-translation/s4_benchmark_measurements.json`](../../docs/evidence/s4-incremental-translation/s4_benchmark_measurements.json)
