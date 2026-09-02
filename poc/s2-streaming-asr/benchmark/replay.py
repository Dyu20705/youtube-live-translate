import time
from pathlib import Path
from typing import Dict, Any
import numpy as np
import soundfile as sf
import scipy.signal

try:
    from ..engines.base import ASREngine
    from ..metrics.tracker import PerformanceTracker
    from ..metrics.text_metrics import evaluate_accuracy
    from ..metrics.stability_metrics import analyze_stream_stability
except (ImportError, ValueError):
    from engines.base import ASREngine
    from metrics.tracker import PerformanceTracker
    from metrics.text_metrics import evaluate_accuracy
    from metrics.stability_metrics import analyze_stream_stability


def load_audio_16k_mono(wav_path: str) -> np.ndarray:
    data, sr = sf.read(wav_path, dtype="float32")
    if len(data.shape) > 1:
        data = data.mean(axis=1)

    if sr != 16000:
        num_samples = int(len(data) * 16000 / sr)
        data = scipy.signal.resample(data, num_samples)

    return data


def run_deterministic_stream_benchmark(
    engine: ASREngine,
    wav_path: str,
    reference_text: str,
    language: str = "en",
    chunk_ms: int = 128,
    simulate_wall_clock: bool = False
) -> Dict[str, Any]:
    audio_data = load_audio_16k_mono(wav_path)
    sample_rate = 16000
    chunk_samples = int(sample_rate * (chunk_ms / 1000.0))
    chunk_duration_sec = chunk_samples / sample_rate

    tracker = PerformanceTracker()
    engine.start_stream()
    tracker.start()

    num_samples = len(audio_data)
    offset = 0

    while offset < num_samples:
        end_idx = min(offset + chunk_samples, num_samples)
        chunk = audio_data[offset:end_idx]

        t0 = time.perf_counter()
        engine.push_audio(chunk)
        partial_hyp = engine.get_partial()
        proc_time = time.perf_counter() - t0

        tracker.record_chunk_processed(chunk_duration_sec, proc_time)
        tracker.record_hypothesis(partial_hyp.text, is_final=False)

        if simulate_wall_clock:
            sleep_time = max(0.0, chunk_duration_sec - proc_time)
            if sleep_time > 0:
                time.sleep(sleep_time)

        offset += chunk_samples

    t_final_0 = time.perf_counter()
    final_hyp = engine.finalize_segment()
    final_duration = time.perf_counter() - t_final_0
    tracker.set_finalization_latency(final_duration)
    tracker.finish_stream(final_hyp.text)

    engine.stop_stream()

    perf_summary = tracker.compute_summary()
    accuracy_summary = evaluate_accuracy(reference_text, final_hyp.text, language=language)
    stability_summary = analyze_stream_stability(tracker.hypotheses_timeline, final_hyp.text)
    model_info = engine.get_model_info()

    return {
        "model_info": {
            "engine_name": model_info.engine_name,
            "model_name": model_info.model_name,
            "model_family": model_info.model_family,
            "language": model_info.language,
            "model_size_mb": model_info.model_size_mb,
            "quantization": model_info.quantization,
            "is_native_streaming": model_info.is_native_streaming,
            "parameters": model_info.parameters
        },
        "benchmark_config": {
            "wav_path": str(wav_path),
            "sample_name": Path(wav_path).stem,
            "target_language": language,
            "chunk_ms": chunk_ms,
            "chunk_samples": chunk_samples
        },
        "realtime_metrics": perf_summary,
        "accuracy_metrics": accuracy_summary,
        "stability_metrics": stability_summary,
        "transcripts": {
            "reference": reference_text,
            "final_hypothesis": final_hyp.text,
            "hypotheses_timeline_count": len(tracker.hypotheses_timeline)
        }
    }
