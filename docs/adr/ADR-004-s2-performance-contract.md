# ADR-004: Stage S2 Performance Contract & Baseline Freeze

## Status
**FROZEN / ACCEPTED** (Date: 2026-09-02)

## Context
Stage S2 established the feasibility and empirical baseline of local streaming Automatic Speech Recognition (ASR) for `youtube-live-translate`.
To ensure subsequent development in Stage S3 (Machine Translation) and Stage S4 (End-to-End Pipeline) does not silently introduce regressions in latency, memory footprint, or streaming stability, an explicit, versioned performance contract is established and frozen.

## Scope & Disclaimers
1. **Engineering Baseline vs Statistical Characterization:** The baseline measurements were collected over 10 repetitions per configuration on standard hardware. This is sufficient for an engineering baseline gate, but does not constitute a universal performance characterization across all hardware configurations or runtime environments.
2. **Regression Fixtures vs Quality Benchmarks:** The audio samples (`en_clean_speech.wav`, `ja_conversational.wav`) serve strictly as deterministic regression test fixtures to catch regressions, not as exhaustive benchmark datasets for general ASR domain evaluation.
3. **Memory & Concurrency Bounds:** "Bounded memory" refers to no measurable memory growth during the 30-second continuous streaming workload under test. In browser AudioWorklet execution, userland process loops have zero explicit array allocations, while internal browser engine audio buffering remains governed by the browser implementation.
4. **Array Wrapping:** Python-level array manipulation uses zero-copy slicing and contiguous memory views; downstream C++ neural network runtime buffering still occurs for acoustic feature extraction.

## Frozen Contract: `s2_performance_contract_v1`

### 1. Latency Budgets
- **English Time-To-First-Transcript (TTFT):**
  - $\text{p50} \le 80.0\text{ ms}$ (Baseline measured: $55.3\text{ ms} - 58.7\text{ ms}$)
  - $\text{p95} \le 100.0\text{ ms}$ (Baseline measured: $60.4\text{ ms} - 61.5\text{ ms}$)
- **Japanese Time-To-First-Transcript (TTFT):**
  - $\text{p50} \le 150.0\text{ ms}$ (Baseline measured: $123.5\text{ ms} - 133.6\text{ ms}$)
  - $\text{p95} \le 180.0\text{ ms}$ (Baseline measured: $135.7\text{ ms} - 156.4\text{ ms}$)
- **Per-Chunk Acoustic Step Latency:** $\le 25.0\text{ ms}$
- **Segment Finalization Latency:** $\le 10.0\text{ ms}$

### 2. Throughput Budgets (Real-Time Factor - RTF)
- **English Streaming RTF:** $\le 0.050$ ($>20\times$ faster than realtime)
- **Japanese Streaming RTF:** $\le 0.100$ ($>10\times$ faster than realtime)

### 3. Resource & Memory Budgets
- **Model Heap Overhead:** $\le 100.0\text{ MB}$ (Baseline measured: $62.4\text{ MB}$)
- **Peak RSS (Process):** $\le 750.0\text{ MB}$ (Baseline measured: $650.7\text{ MB}$)
- **Continuous Stream Memory Drift:** $\le 1.0\text{ MB / minute}$
- **Max CPU Worker Threads:** $4$

### 4. Streaming Stability Budgets
- **Stable Prefix Ratio (SPR):** $\ge 0.95$ (Baseline measured: $1.00$)
- **Destructive Revisions Allowed:** $0$ (Transducer monotonicity guaranteed)

### 5. Regression Accuracy Fixture Limits
- **English Clean Speech WER:** $\le 0.25$ (Baseline measured: $0.22$)
- **Japanese Conversational CER:** $\le 0.06$ (Baseline measured: $0.03$)

### 6. Audio Worklet Hot Path Invariants
- Zero explicit userland heap allocations inside `process()` (`new Float32Array`, `new Object`).
- Resampling phase continuity (`this.sourcePhase`, `this.lastSample`) preserved across 128-sample boundaries.

## Enforcement Mechanism
All thresholds in `s2_performance_contract_v1` are automatically enforced by [`poc/s2-streaming-asr/scripts/run_regression_check.py`](file:///home/duy/Code/tools/youtube-live-translate/poc/s2-streaming-asr/scripts/run_regression_check.py). Any violation will block progress to subsequent stages.
