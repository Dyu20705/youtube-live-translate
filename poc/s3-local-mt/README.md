# Stage S3 — Local Machine Translation (MT) PoC & Feasibility Benchmark

This directory contains the implementation and reproducible empirical benchmark suite for **Stage S3: Local Machine Translation Feasibility**.

---

## Directory Structure

```
poc/s3-local-mt/
├── README.md
├── datasets/
│   ├── build_dataset.py           # Dataset builder & partial prefix generator
│   ├── manifest.json              # 18-item curated deterministic Japanese test corpus
│   └── partial_variants.json      # 108 deterministic partial prefix variants (FULL, UNPUNCT, 25%, 50%, 75%, 100%)
├── models/
│   ├── download_and_convert.py    # Model acquisition & CTranslate2 INT8 converter
│   ├── opus-mt-ja-en-ct2-int8/    # Converted Helsinki-NLP Marian INT8 model weights + tokenizer
│   └── nllb-200-600m-ct2-int8/    # Converted Meta NLLB-200 distilled 600M INT8 model weights + tokenizer
├── engines/
│   ├── base.py                    # Standard MTEngine interface & TranslationResult dataclass
│   ├── marian_engine.py           # Marian CTranslate2 INT8 runtime
│   └── nllb_engine.py             # NLLB CTranslate2 INT8 runtime
├── metrics/
│   ├── quality_metrics.py         # BLEU (sacrebleu), chrF++, COMET (Unbabel/wmt22-comet-da)
│   ├── stability_metrics.py       # Translation Prefix Stability (TPS), revision counts, rewrites
│   └── latency_tracker.py         # Statistical latency distribution & phase breakdown profiler
├── benchmark/
│   ├── corpus_benchmark.py        # Latency distribution, scaling & quality on Clean vs ASR
│   ├── partial_stability.py       # Partial prefix & unpunctuated robustness analyzer
│   ├── retranslation_cost.py      # Naive re-translation CPU cost & redundancy quantifier
│   └── e2e_s2_s3_runner.py        # Streaming pipeline runner (Sherpa-ONNX ASR -> MT -> Subtitle)
├── scripts/
│   ├── run_fast_benchmark.py      # Fast empirical screening benchmark runner (~3-5s)
│   ├── run_full_benchmark.py      # Full comprehensive benchmark runner
│   └── run_regression_check.py    # Automated CI/regression performance gate
└── tests/
    ├── conftest.py                # Pytest path configuration
    ├── test_marian_engine.py      # Unit tests for Marian engine
    ├── test_nllb_engine.py        # Unit tests for NLLB engine
    ├── test_metrics.py            # Unit tests for BLEU, chrF++, TPS, latency tracker
    └── test_e2e_pipeline.py       # Integration tests for streaming ASR -> MT pipeline
```

---

## Quick Start & Reproduction

### 1. Run Unit & Integration Tests
```bash
pytest poc/s3-local-mt/tests/ -v
```

### 2. Run Fast Screening Benchmark
```bash
python3 poc/s3-local-mt/scripts/run_fast_benchmark.py
```

### 3. Run S3 Regression Performance Gate
```bash
python3 poc/s3-local-mt/scripts/run_regression_check.py
```

---

## Architectural Decision Summary

- **Primary MT Candidate (Real-Time Hot-Path):** Helsinki-NLP `opus-mt-ja-en` (Marian CTranslate2 INT8)
- **Secondary Quality / Reference Engine:** Meta `nllb-200-distilled-600M` (CTranslate2 INT8)
- **Feasibility Result:** `S3 RESULT = GO` ($\text{MT p50} = 65.73\text{ ms} < 100\text{ ms}$, per-chunk step latency $\text{p50} = 65.45\text{ ms}$)
- **Evidence Documentation:**
  - Full Empirical Research Report: [`docs/research/s3-local-mt.md`](file:///home/duy/Code/tools/youtube-live-translate/docs/research/s3-local-mt.md)
  - Architecture Decision Record: [`docs/adr/ADR-005-local-mt-engine-selection.md`](file:///home/duy/Code/tools/youtube-live-translate/docs/adr/ADR-005-local-mt-engine-selection.md)
  - Raw JSON Measurements: [`docs/evidence/s3-local-mt/s3_benchmark_measurements.json`](file:///home/duy/Code/tools/youtube-live-translate/docs/evidence/s3-local-mt/s3_benchmark_measurements.json)
