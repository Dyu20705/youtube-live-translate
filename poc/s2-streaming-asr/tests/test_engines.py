import pytest
import numpy as np
from pathlib import Path
from engines.sherpa_onnx_engine import SherpaOnnxStreamingEngine
from engines.faster_whisper_engine import FasterWhisperIncrementalEngine

MODELS_DIR = Path(__file__).parent.parent / "models"


def test_sherpa_onnx_engine_lifecycle():
    model_dir = MODELS_DIR / "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17"
    if not model_dir.exists():
        pytest.skip(f"Model dir {model_dir} not available")

    engine = SherpaOnnxStreamingEngine(str(model_dir), language="en", num_threads=2)
    engine.initialize()

    info = engine.get_model_info()
    assert info.engine_name == "Sherpa-ONNX"
    assert info.is_native_streaming is True
    assert info.model_size_mb > 0

    engine.start_stream()

    # Test with 1 second of silence (zeros float32)
    silence_float = np.zeros(16000, dtype=np.float32)
    engine.push_audio(silence_float)
    partial = engine.get_partial()
    assert isinstance(partial.text, str)

    # Test with int16 array
    silence_int16 = np.zeros(16000, dtype=np.int16)
    engine.push_audio(silence_int16)

    # Test finalization
    final_hyp = engine.finalize_segment()
    assert isinstance(final_hyp.text, str)
    assert final_hyp.is_final is True

    engine.stop_stream()


def test_faster_whisper_engine_lifecycle():
    engine = FasterWhisperIncrementalEngine(model_size="tiny", language="en", compute_type="int8", num_threads=2)
    engine.initialize()

    info = engine.get_model_info()
    assert info.engine_name == "Faster-Whisper"
    assert info.is_native_streaming is False

    engine.start_stream()

    # Push small chunks
    chunk = np.zeros(2048, dtype=np.float32)
    engine.push_audio(chunk)
    partial = engine.get_partial()
    assert isinstance(partial.text, str)

    final_hyp = engine.finalize_segment()
    assert isinstance(final_hyp.text, str)
    assert final_hyp.is_final is True

    engine.stop_stream()
