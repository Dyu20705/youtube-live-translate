import time
from typing import Optional, Dict, Any, List
import numpy as np
from faster_whisper import WhisperModel

from .base import ASREngine, Hypothesis, ModelInfo


class FasterWhisperIncrementalEngine(ASREngine):
    def __init__(
        self,
        model_size: str = "tiny",
        language: Optional[str] = "en",
        device: str = "cpu",
        compute_type: str = "int8",
        num_threads: int = 4,
        decoding_interval_ms: int = 128,
        download_root: Optional[str] = None
    ):
        self.model_size = model_size
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self.num_threads = num_threads
        self.decoding_interval_ms = decoding_interval_ms
        self.download_root = download_root

        self.model: Optional[WhisperModel] = None
        self.audio_chunks: List[np.ndarray] = []
        self.total_samples_accumulated: int = 0
        self.last_decode_sample_count: int = 0
        self.current_hypothesis_text: str = ""
        self.sample_rate: int = 16000
        self.model_info: Optional[ModelInfo] = None

    def initialize(self) -> None:
        start_t = time.perf_counter()
        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            cpu_threads=self.num_threads,
            download_root=self.download_root
        )
        init_duration_ms = (time.perf_counter() - start_t) * 1000.0

        size_map = {"tiny": 75.0, "base": 145.0, "small": 480.0, "medium": 1500.0}
        size_mb = size_map.get(self.model_size, 100.0)

        self.model_info = ModelInfo(
            engine_name="Faster-Whisper",
            model_name=f"whisper-{self.model_size}",
            model_family="encoder-decoder-whisper",
            language=self.language or "multilingual",
            model_size_mb=size_mb,
            quantization=self.compute_type,
            sample_rate=self.sample_rate,
            is_native_streaming=False,
            parameters={
                "model_size": self.model_size,
                "compute_type": self.compute_type,
                "num_threads": self.num_threads,
                "decoding_interval_ms": self.decoding_interval_ms,
                "init_duration_ms": round(init_duration_ms, 2)
            }
        )

    def start_stream(self) -> None:
        if self.model is None:
            self.initialize()
        self.audio_chunks = []
        self.total_samples_accumulated = 0
        self.last_decode_sample_count = 0
        self.current_hypothesis_text = ""

    def push_audio(self, pcm_chunk: np.ndarray) -> None:
        if self.model is None:
            raise RuntimeError("Engine not initialized.")

        if pcm_chunk.dtype == np.int16:
            samples = pcm_chunk.astype(np.float32) / 32768.0
        elif pcm_chunk.dtype == np.float32:
            samples = pcm_chunk if pcm_chunk.flags['C_CONTIGUOUS'] else np.ascontiguousarray(pcm_chunk)
        else:
            samples = pcm_chunk.astype(np.float32)

        self.audio_chunks.append(samples)
        self.total_samples_accumulated += len(samples)

        samples_per_interval = int(self.sample_rate * (self.decoding_interval_ms / 1000.0))
        if self.total_samples_accumulated - self.last_decode_sample_count >= samples_per_interval:
            self._decode_current_buffer()
            self.last_decode_sample_count = self.total_samples_accumulated

    def _decode_current_buffer(self) -> None:
        if self.total_samples_accumulated < int(self.sample_rate * 0.3):
            return

        audio_arr = np.concatenate(self.audio_chunks) if len(self.audio_chunks) > 1 else self.audio_chunks[0]
        segments, _ = self.model.transcribe(
            audio_arr,
            beam_size=1,
            temperature=0.0,
            language=self.language,
            condition_on_previous_text=False,
            without_timestamps=True,
            vad_filter=False
        )

        texts = [seg.text.strip() for seg in segments if seg.text.strip()]
        self.current_hypothesis_text = " ".join(texts).strip()

    def get_partial(self) -> Hypothesis:
        return Hypothesis(
            text=self.current_hypothesis_text,
            is_final=False
        )

    def is_endpoint_detected(self) -> bool:
        return False

    def finalize_segment(self) -> Hypothesis:
        if self.model is None or not self.audio_chunks:
            return Hypothesis(text="", is_final=True)

        audio_arr = np.concatenate(self.audio_chunks) if len(self.audio_chunks) > 1 else self.audio_chunks[0]
        segments, _ = self.model.transcribe(
            audio_arr,
            beam_size=1,
            temperature=0.0,
            language=self.language,
            condition_on_previous_text=False,
            without_timestamps=True,
            vad_filter=False
        )

        texts = [seg.text.strip() for seg in segments if seg.text.strip()]
        final_text = " ".join(texts).strip()
        self.current_hypothesis_text = final_text
        return Hypothesis(
            text=final_text,
            is_final=True
        )

    def stop_stream(self) -> None:
        self.audio_chunks = []
        self.total_samples_accumulated = 0

    def get_model_info(self) -> ModelInfo:
        if self.model_info is None:
            self.initialize()
        return self.model_info
