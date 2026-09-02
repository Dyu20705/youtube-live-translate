"""
test_s4_integration.py - Integration test for Frozen S2 ASR -> S4 Streaming Translator -> S3 Marian INT8.
"""

import pytest
import time
from pathlib import Path
import soundfile as sf
import scipy.signal
import numpy as np

from policy.state_model import PolicyConfig, SegmentStatus
from policy.streaming_translator import IncrementalTranslator
from metrics.s4_metrics import analyze_s4_session_stability

WORKSPACE_DIR = Path(__file__).parent.parent.parent.parent.resolve()
S2_DIR = WORKSPACE_DIR / "poc" / "s2-streaming-asr"
S3_DIR = WORKSPACE_DIR / "poc" / "s3-local-mt"

import sys
import types
import importlib.util

def get_marian_engine_class():
    s3_pkg = "s3_local_mt_engines_isolated"
    if s3_pkg not in sys.modules:
        pkg_mod = types.ModuleType(s3_pkg)
        pkg_mod.__path__ = [str(S3_DIR / "engines")]
        sys.modules[s3_pkg] = pkg_mod

    base_file = S3_DIR / "engines" / "base.py"
    spec_base = importlib.util.spec_from_file_location(f"{s3_pkg}.base", str(base_file))
    mod_base = importlib.util.module_from_spec(spec_base)
    sys.modules[f"{s3_pkg}.base"] = mod_base
    spec_base.loader.exec_module(mod_base)

    eng_file = S3_DIR / "engines" / "marian_engine.py"
    spec_eng = importlib.util.spec_from_file_location(f"{s3_pkg}.marian_engine", str(eng_file))
    mod_eng = importlib.util.module_from_spec(spec_eng)
    sys.modules[f"{s3_pkg}.marian_engine"] = mod_eng
    spec_eng.loader.exec_module(mod_eng)
    return mod_eng.MarianCTranslate2Engine

def get_s2_sherpa_engine_class():
    s2_pkg = "s2_streaming_asr_engines_isolated"
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


def test_s2_s4_marian_streaming_integration():
    ja_asr_model = S2_DIR / "models" / "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10"
    marian_model = S3_DIR / "models" / "opus-mt-ja-en-ct2-int8"
    wav_path = S2_DIR / "datasets" / "ja_conversational.wav"

    assert ja_asr_model.exists(), f"ASR model not found at {ja_asr_model}"
    assert marian_model.exists(), f"Marian model not found at {marian_model}"
    assert wav_path.exists(), f"WAV not found at {wav_path}"

    # Initialize S2 ASR
    SherpaOnnxStreamingEngine = get_s2_sherpa_engine_class()
    asr_engine = SherpaOnnxStreamingEngine(str(ja_asr_model), language="multilingual", num_threads=2)
    asr_engine.initialize()

    # Initialize S3 Marian MT
    MarianCTranslate2Engine = get_marian_engine_class()
    mt_engine = MarianCTranslate2Engine(str(marian_model), num_threads=2)
    mt_engine.initialize()

    # Initialize S4 Translator
    config = PolicyConfig(agreement_k=2, unstable_buffer_tokens=2, enable_mt_deduplication=True)
    translator = IncrementalTranslator(mt_engine, config)

    audio_data = load_audio_16k_mono(str(wav_path))
    sample_rate = 16000
    chunk_ms = 128
    chunk_samples = int(sample_rate * (chunk_ms / 1000.0))
    total_audio_duration_sec = len(audio_data) / sample_rate

    asr_engine.start_stream()
    translator.start_segment(segment_id=1)

    timeline_states = []
    t_start = time.perf_counter()

    offset = 0
    num_samples = len(audio_data)
    while offset < num_samples:
        end_idx = min(offset + chunk_samples, num_samples)
        chunk = audio_data[offset:end_idx]

        asr_engine.push_audio(chunk)
        partial_hyp = asr_engine.get_partial()
        asr_text = partial_hyp.text.strip()

        # Update S4 policy
        state = translator.update_partial(asr_text)
        timeline_states.append(state)

        offset += chunk_samples

    # Finalization
    final_asr = asr_engine.finalize_segment()
    final_state = translator.finalize_segment(final_asr.text)
    timeline_states.append(final_state)
    asr_engine.stop_stream()

    total_wall_time = time.perf_counter() - t_start
    rtf = total_wall_time / total_audio_duration_sec

    # Evaluate S4 session metrics
    stability = analyze_s4_session_stability(timeline_states)

    assert rtf < 0.25, f"RTF too high: {rtf:.4f}"
    assert stability["committed_prefix_revisions"] == 0, "Committed prefix was mutated!"
    assert len(final_state.committed_text) > 0, "Final translation is empty!"
    assert final_state.is_final is True
    assert final_state.provisional_text == ""
    assert translator.session_metrics.mt_call_reduction_ratio > 0.0, "Deduplication did not reduce MT calls!"
