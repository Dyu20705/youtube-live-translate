"""
runtime_pipeline.py - Orchestrates ASR -> Incremental Translation -> Wire Messages.
"""

import sys
import os
import time
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np

# Ensure sibling packages are discoverable
RUNTIME_ROOT = Path(__file__).resolve().parent.parent
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from host.protocol import (
    SubtitleUpdateMessage,
    SubtitleFinalMessage,
    StatusMessage,
    ErrorMessage,
    serialize_wire_message
)
from engines.asr_engine import SherpaOnnxStreamingEngine
from engines.mt_engine import MarianCTranslate2Engine
from policy.state_model import PolicyConfig
from policy.streaming_translator import IncrementalTranslator


class StreamingTranslationRuntime:
    """
    Stateful streaming pipeline managing Sherpa-ONNX ASR and S4 Incremental Translator.
    Emits serialized JSON wire protocol messages.
    """
    def __init__(
        self,
        asr_engine: Optional[SherpaOnnxStreamingEngine] = None,
        mt_engine: Optional[MarianCTranslate2Engine] = None,
        k: int = 2,
        buffer: int = 2
    ):
        self.asr_engine = asr_engine
        self.mt_engine = mt_engine
        self.k = k
        self.buffer = buffer

        self.translator: Optional[IncrementalTranslator] = None
        if self.mt_engine is not None:
            config = PolicyConfig(
                agreement_k=self.k,
                unstable_buffer_tokens=self.buffer,
                enable_mt_deduplication=True
            )
            self.translator = IncrementalTranslator(self.mt_engine, config)

        self.segment_id = 1
        self.source_revision = 0
        self.is_running = False

    def start(self):
        """Initializes state and starts streaming session."""
        self.is_running = True
        self.segment_id = 1
        self.source_revision = 0
        if self.asr_engine:
            self.asr_engine.start_stream()
        if self.translator:
            self.translator.start_segment(segment_id=self.segment_id)

    def stop(self):
        """Stops streaming session."""
        self.is_running = False
        if self.asr_engine:
            self.asr_engine.stop_stream()

    def process_pcm_chunk(self, pcm_bytes: bytes) -> Optional[str]:
        """
        Ingests a 16kHz mono 16-bit PCM chunk, performs ASR and incremental translation,
        and returns a serialized JSON wire message if state changed.
        """
        if not self.is_running or not self.asr_engine or not self.translator:
            return None

        # Convert int16 bytes to float32 samples [-1.0, 1.0]
        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        self.asr_engine.push_audio(samples)

        partial_hyp = self.asr_engine.get_partial()
        asr_text = partial_hyp.text.strip() if partial_hyp else ""

        if asr_text:
            state = self.translator.update_partial(asr_text)
            self.source_revision += 1

            msg = SubtitleUpdateMessage(
                segment_id=state.segment_id,
                source_revision=self.source_revision,
                committed_text=state.committed_text,
                provisional_text=state.provisional_text,
                display_text=state.display_text,
                is_final=False,
                timestamp_ms=int(time.time() * 1000)
            )
            return serialize_wire_message(msg)

        return None

    def process_encoded_audio(self, encoded_data: str) -> Optional[str]:
        """Accepts base64 or hex encoded PCM chunk from native messaging port."""
        if not encoded_data:
            return None
        try:
            # Try base64 first (standard)
            pcm_bytes = base64.b64decode(encoded_data)
        except Exception:
            try:
                # Fallback to hex
                pcm_bytes = bytes.fromhex(encoded_data)
            except Exception as e:
                raise ValueError(f"Could not decode audio chunk: {e}")

        return self.process_pcm_chunk(pcm_bytes)

    def finalize_stream(self) -> Optional[str]:
        """Flushes the active ASR segment and emits final subtitle message."""
        if not self.is_running or not self.asr_engine or not self.translator:
            return None

        final_asr = self.asr_engine.finalize_segment()
        asr_text = final_asr.text.strip() if final_asr else ""

        self.source_revision += 1
        final_state = self.translator.finalize_segment(asr_text)

        msg = SubtitleFinalMessage(
            segment_id=final_state.segment_id,
            source_revision=self.source_revision,
            committed_text=final_state.committed_text,
            provisional_text="",
            display_text=final_state.display_text,
            is_final=True,
            timestamp_ms=int(time.time() * 1000)
        )

        self.segment_id += 1
        self.source_revision = 0
        self.translator.start_segment(segment_id=self.segment_id)
        self.asr_engine.start_stream()
        return serialize_wire_message(msg)

    def process_text_partial(self, text: str, is_final: bool = False) -> str:
        """
        Direct text processing method for testing and synthetic event streaming.
        """
        if not self.translator:
            raise RuntimeError("IncrementalTranslator is not initialized")

        self.source_revision += 1
        if is_final:
            final_state = self.translator.finalize_segment(text)
            msg = SubtitleFinalMessage(
                segment_id=final_state.segment_id,
                source_revision=self.source_revision,
                committed_text=final_state.committed_text,
                provisional_text="",
                display_text=final_state.display_text,
                is_final=True,
                timestamp_ms=int(time.time() * 1000)
            )
            self.segment_id += 1
            self.source_revision = 0
            self.translator.start_segment(segment_id=self.segment_id)
            return serialize_wire_message(msg)
        else:
            state = self.translator.update_partial(text)
            msg = SubtitleUpdateMessage(
                segment_id=state.segment_id,
                source_revision=self.source_revision,
                committed_text=state.committed_text,
                provisional_text=state.provisional_text,
                display_text=state.display_text,
                is_final=False,
                timestamp_ms=int(time.time() * 1000)
            )
            return serialize_wire_message(msg)
