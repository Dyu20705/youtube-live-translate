"""
e2e_s2_s3_runner.py - Measures End-to-End latency for the complete S2 ASR -> S3 MT streaming pipeline.
"""

import time
import sys
import types
import importlib.util
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import soundfile as sf
import scipy.signal

try:
    from ..engines.base import MTEngine
except (ImportError, ValueError):
    from engines.base import MTEngine

POC_DIR = Path(__file__).parent.parent.resolve()
WORKSPACE_DIR = POC_DIR.parent.parent.resolve()
S2_DIR = WORKSPACE_DIR / "poc" / "s2-streaming-asr"


def get_s2_sherpa_engine_class():
    """Dynamically loads SherpaOnnxStreamingEngine from S2 directory cleanly."""
    s2_pkg = "s2_streaming_asr_engines"
    if s2_pkg not in sys.modules:
        pkg_mod = types.ModuleType(s2_pkg)
        pkg_mod.__path__ = [str(S2_DIR / "engines")]
        sys.modules[s2_pkg] = pkg_mod

    base_file = S2_DIR / "engines" / "base.py"
    spec_base = importlib.util.spec_from_file_location(f"{s2_pkg}.base", str(base_file))
    mod_base = importlib.util.module_from_spec(spec_base)
    sys.modules[f"{s2_pkg}.base"] = mod_base
    spec_base.loader.exec_module(mod_base)

    eng_file = S2_DIR / "engines" / "sherpa_onnx_engine.py"
    spec_eng = importlib.util.spec_from_file_location(f"{s2_pkg}.sherpa_onnx_engine", str(eng_file))
    mod_eng = importlib.util.module_from_spec(spec_eng)
    sys.modules[f"{s2_pkg}.sherpa_onnx_engine"] = mod_eng
    spec_eng.loader.exec_module(mod_eng)
    return mod_eng.SherpaOnnxStreamingEngine


def load_audio_16k_mono(wav_path: str) -> np.ndarray:
    data, sr = sf.read(wav_path, dtype="float32")
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    if sr != 16000:
        num_samples = int(len(data) * 16000 / sr)
        data = scipy.signal.resample(data, num_samples)
    return data


def run_e2e_streaming_pipeline(
    asr_engine: Any,
    mt_engine: MTEngine,
    wav_path: str,
    reference_ja: str,
    reference_en: str,
    chunk_ms: int = 128
) -> Dict[str, Any]:
    """
    Executes real-time simulated streaming pipeline:
    Audio Capture -> S2 ASR Partial -> S3 MT -> English Subtitle Output.
    Measures per-event latency breakdown.
    """
    audio_data = load_audio_16k_mono(wav_path)
    sample_rate = 16000
    chunk_samples = int(sample_rate * (chunk_ms / 1000.0))
    total_audio_duration_sec = len(audio_data) / sample_rate

    asr_engine.start_stream()

    timeline_events: List[Dict[str, Any]] = []
    prev_asr_text = ""

    num_samples = len(audio_data)
    offset = 0
    chunk_index = 0

    t_pipeline_start = time.perf_counter()

    while offset < num_samples:
        end_idx = min(offset + chunk_samples, num_samples)
        chunk = audio_data[offset:end_idx]

        t_audio_in = time.perf_counter()
        
        # 1. ASR Step
        t_asr_0 = time.perf_counter()
        asr_engine.push_audio(chunk)
        partial_hyp = asr_engine.get_partial()
        t_asr_1 = time.perf_counter()
        asr_latency_ms = (t_asr_1 - t_asr_0) * 1000.0

        current_asr_text = partial_hyp.text.strip()
        
        # 2. MT Step (triggered when ASR hypothesis updates)
        if current_asr_text and current_asr_text != prev_asr_text:
            t_mt_0 = time.perf_counter()
            ipc_glue_ms = (t_mt_0 - t_asr_1) * 1000.0
            
            mt_res = mt_engine.translate(current_asr_text, beam_size=1)
            t_mt_1 = time.perf_counter()
            mt_latency_ms = (t_mt_1 - t_mt_0) * 1000.0

            total_user_latency_ms = (t_mt_1 - t_audio_in) * 1000.0

            timeline_events.append({
                "chunk_index": chunk_index,
                "audio_timestamp_sec": round((offset + len(chunk)) / sample_rate, 2),
                "asr_text": current_asr_text,
                "english_translation": mt_res.target_text,
                "latency_breakdown_ms": {
                    "asr_ms": round(asr_latency_ms, 2),
                    "ipc_glue_ms": round(ipc_glue_ms, 3),
                    "mt_tokenizer_ms": mt_res.tokenizer_time_ms,
                    "mt_inference_ms": mt_res.inference_time_ms,
                    "mt_detokenizer_ms": mt_res.detokenizer_time_ms,
                    "mt_total_ms": round(mt_latency_ms, 2),
                    "total_user_visible_ms": round(total_user_latency_ms, 2)
                }
            })
            prev_asr_text = current_asr_text

        offset += chunk_samples
        chunk_index += 1

    # Finalization step
    t_fin_0 = time.perf_counter()
    final_asr = asr_engine.finalize_segment()
    t_fin_asr = time.perf_counter()
    asr_fin_ms = (t_fin_asr - t_fin_0) * 1000.0

    t_fin_mt_0 = time.perf_counter()
    final_mt = mt_engine.translate(final_asr.text, beam_size=1)
    t_fin_mt_1 = time.perf_counter()
    mt_fin_ms = (t_fin_mt_1 - t_fin_mt_0) * 1000.0
    total_fin_latency_ms = (t_fin_mt_1 - t_fin_0) * 1000.0

    asr_engine.stop_stream()
    total_pipeline_time_sec = time.perf_counter() - t_pipeline_start

    # Compute latency distributions across timeline events
    if timeline_events:
        user_lats = [e["latency_breakdown_ms"]["total_user_visible_ms"] for e in timeline_events]
        mt_lats = [e["latency_breakdown_ms"]["mt_total_ms"] for e in timeline_events]
        asr_lats = [e["latency_breakdown_ms"]["asr_ms"] for e in timeline_events]

        e2e_summary = {
            "total_user_visible_latency_p50_ms": round(float(np.percentile(user_lats, 50)), 2),
            "total_user_visible_latency_p95_ms": round(float(np.percentile(user_lats, 95)), 2),
            "total_user_visible_latency_p99_ms": round(float(np.percentile(user_lats, 99)), 2),
            "mt_latency_p50_ms": round(float(np.percentile(mt_lats, 50)), 2),
            "mt_latency_p95_ms": round(float(np.percentile(mt_lats, 95)), 2),
            "asr_latency_p50_ms": round(float(np.percentile(asr_lats, 50)), 2),
            "asr_latency_p95_ms": round(float(np.percentile(asr_lats, 95)), 2),
            "events_count": len(timeline_events)
        }
    else:
        e2e_summary = {}

    return {
        "benchmark_sample": Path(wav_path).name,
        "audio_duration_sec": round(total_audio_duration_sec, 2),
        "total_wall_clock_time_sec": round(total_pipeline_time_sec, 2),
        "real_time_factor": round(total_pipeline_time_sec / total_audio_duration_sec, 4),
        "transcripts": {
            "reference_ja": reference_ja,
            "asr_final_ja": final_asr.text,
            "reference_en": reference_en,
            "mt_final_en": final_mt.target_text
        },
        "e2e_latency_summary": e2e_summary,
        "finalization_latency_ms": {
            "asr_finalization_ms": round(asr_fin_ms, 2),
            "mt_finalization_ms": round(mt_fin_ms, 2),
            "total_finalization_ms": round(total_fin_latency_ms, 2)
        },
        "timeline_events": timeline_events
    }
