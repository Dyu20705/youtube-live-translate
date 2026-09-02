"""
asr_engine.py - Sherpa-ONNX streaming Zipformer Transducer ASR Engine.
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np
import sherpa_onnx

from .base import ASREngine, Hypothesis

SCALE_INT16_TO_FLOAT32 = 1.0 / 32768.0


class SherpaOnnxStreamingEngine(ASREngine):
    def __init__(
        self,
        model_dir: str,
        language: str = "ja",
        num_threads: int = 2,
        decoding_method: str = "greedy_search",
        sample_rate: int = 16000
    ):
        self.model_dir = Path(model_dir)
        self.language = language
        self.num_threads = num_threads
        self.decoding_method = decoding_method
        self.sample_rate = sample_rate

        self.recognizer: Optional[sherpa_onnx.OnlineRecognizer] = None
        self.stream: Optional[sherpa_onnx.OnlineStream] = None

    def initialize(self) -> None:
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {self.model_dir}")

        tokens_path = self.model_dir / "tokens.txt"
        if not tokens_path.exists():
            raise FileNotFoundError(f"tokens.txt not found in {self.model_dir}")

        encoder_files = list(self.model_dir.glob("encoder*.onnx"))
        decoder_files = list(self.model_dir.glob("decoder*.onnx"))
        joiner_files = list(self.model_dir.glob("joiner*.onnx"))

        if not encoder_files or not decoder_files or not joiner_files:
            raise FileNotFoundError(f"Missing ONNX encoder/decoder/joiner in {self.model_dir}")

        encoder_path = encoder_files[0]
        decoder_path = decoder_files[0]
        joiner_path = joiner_files[0]

        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(tokens_path),
            encoder=str(encoder_path),
            decoder=str(decoder_path),
            joiner=str(joiner_path),
            num_threads=self.num_threads,
            sample_rate=self.sample_rate,
            feature_dim=80,
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=1.2,
            rule3_min_utterance_length=20.0,
            decoding_method=self.decoding_method,
            provider="cpu"
        )

    def start_stream(self) -> None:
        if self.recognizer is None:
            self.initialize()
        self.stream = self.recognizer.create_stream()

    def push_audio(self, pcm_chunk: np.ndarray) -> None:
        if self.stream is None or self.recognizer is None:
            raise RuntimeError("Stream is not started. Call start_stream() first.")

        if pcm_chunk.dtype == np.int16:
            samples = pcm_chunk.astype(np.float32) * SCALE_INT16_TO_FLOAT32
        elif pcm_chunk.dtype == np.float32:
            samples = pcm_chunk if pcm_chunk.flags['C_CONTIGUOUS'] else np.ascontiguousarray(pcm_chunk)
        else:
            samples = pcm_chunk.astype(np.float32)

        self.stream.accept_waveform(self.sample_rate, samples)

        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)

    def get_partial(self) -> Hypothesis:
        if self.stream is None or self.recognizer is None:
            return Hypothesis(text="", is_final=False)

        res = self.recognizer.get_result(self.stream)
        text = res.text.strip() if hasattr(res, 'text') else str(res).strip()
        return Hypothesis(
            text=text,
            is_final=False
        )

    def is_endpoint_detected(self) -> bool:
        if self.stream is None or self.recognizer is None:
            return False
        return bool(self.recognizer.is_endpoint(self.stream))

    def finalize_segment(self) -> Hypothesis:
        if self.stream is None or self.recognizer is None:
            return Hypothesis(text="", is_final=True)

        self.stream.input_finished()
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)

        res = self.recognizer.get_result(self.stream)
        final_text = res.text.strip() if hasattr(res, 'text') else str(res).strip()
        return Hypothesis(
            text=final_text,
            is_final=True
        )

    def stop_stream(self) -> None:
        self.stream = None
