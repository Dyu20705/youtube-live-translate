# Stage S2 — Local Streaming ASR Feasibility

**Status:** `FROZEN` (Baseline Contract v1 Established)  
**Selected Runtime:** `Sherpa-ONNX` (Streaming Zipformer)  
**Performance Contract:** [`s2_performance_contract_v1.json`](file:///home/duy/Code/tools/youtube-live-translate/poc/s2-streaming-asr/s2_performance_contract_v1.json) | [ADR-004](file:///home/duy/Code/tools/youtube-live-translate/docs/adr/ADR-004-s2-performance-contract.md)

---

## 1. Executive Summary

Stage S2 established the empirical evidence base for local streaming Automatic Speech Recognition (ASR).

Under controlled, deterministic streaming conditions (64ms, 128ms, 256ms audio chunks):
* **Sherpa-ONNX (Zipformer Streaming Transducer)** demonstrated frame-synchronous emission with $\text{TTFT} = 55.3\text{ms} - 133.6\text{ms}$, $\text{RTF} = 0.025 - 0.084$, zero destructive revisions ($\text{SPR} = 1.00$), and bounded memory footprint ($62.4\text{ MB}$ model heap).
* **Faster-Whisper (Sliding-Window Re-decoding)** exhibited high CPU saturation, $\text{RTF} > 2.5$, and continuous destructive revisions ($>30$ per stream), proving unsuitable for the core realtime streaming hot path.

---

## 2. Evidence-Bounded Scope & Disclaimers

1. **Baseline Fixtures:** Evaluated datasets (`en_clean_speech.wav`, `ja_conversational.wav`) serve as regression fixtures, not exhaustive general-domain speech benchmarks.
2. **Statistical Scope:** Measurements represent an engineering baseline across 10 repetitions on the host test environment, not a universal guarantee.
3. **Memory & Concurrency:** "Bounded memory" denotes no measurable memory growth during the 30-second continuous streaming workload under test. In browser AudioWorklet execution, userland loops have no explicit array allocations, while internal browser audio buffering remains governed by the browser engine.
4. **Buffer Wrapping:** Python-level array manipulation uses zero-copy slicing; downstream C++ neural network runtime buffering still occurs for acoustic feature extraction.

---

## 3. Directory Layout

```
poc/s2-streaming-asr/
├── s2_performance_contract_v1.json   # Frozen baseline contract specification
├── engines/
│   ├── base.py                       # Abstract ASREngine interface
│   ├── sherpa_onnx_engine.py         # Sherpa-ONNX streaming transducer adapter
│   └── faster_whisper_engine.py      # Faster-Whisper incremental sliding-window adapter
├── metrics/
│   ├── text_metrics.py               # WER, CER, O(min(m,n)) Levenshtein distance
│   ├── stability_metrics.py          # Revision count, SPR calculation
│   └── tracker.py                    # Realtime latency, TTFT, RTF, CPU/RAM telemetry
├── benchmark/
│   ├── replay.py                     # Deterministic chunk streaming harness
│   └── runner.py                     # Benchmark matrix runner
├── audit/
│   └── benchmark_suite.py            # Independent statistical audit suite
├── tests/
│   ├── test_text_metrics.py          # Unit tests for text normalization & edit distance
│   ├── test_stability_metrics.py     # Unit tests for stream stability & SPR
│   └── test_engines.py               # Unit tests for engine lifecycle & dtype handling
├── scripts/
│   ├── download_models.py            # Model downloader
│   ├── prepare_dataset.py            # Dataset preparation
│   └── run_regression_check.py       # Automated regression gate enforcing contract v1
└── results/
    ├── s2_audit_measurements.json    # Full empirical audit dataset with system metadata
    └── benchmark_results.json        # Raw benchmark matrix results
```

---

## 4. Running Tests & Regression Gates

### Run All Unit & Integration Tests
```bash
PYTHONPATH=poc/s2-streaming-asr poc/s2-streaming-asr/.venv/bin/pytest poc/s2-streaming-asr/tests -v
```

### Run Automated S2 Regression Gate (Enforces Contract v1)
```bash
PYTHONPATH=poc/s2-streaming-asr poc/s2-streaming-asr/.venv/bin/python poc/s2-streaming-asr/scripts/run_regression_check.py
```

### Run Empirical Audit Benchmark Suite
```bash
PYTHONPATH=poc/s2-streaming-asr poc/s2-streaming-asr/.venv/bin/python poc/s2-streaming-asr/audit/benchmark_suite.py
```
