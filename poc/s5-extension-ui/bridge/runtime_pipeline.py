"""
runtime_pipeline.py - Orchestrates S2 ASR -> S4 Incremental Translation -> S5 Wire Messages.
"""

from typing import Optional, Dict, Any, List
import os
import sys
import types
import importlib.util
import time
import numpy as np

try:
    from .protocol import (
        SubtitleUpdateMessage,
        SubtitleFinalMessage,
        StatusMessage,
        ErrorMessage,
        serialize_wire_message
    )
except (ImportError, ValueError):
    from protocol import (
        SubtitleUpdateMessage,
        SubtitleFinalMessage,
        StatusMessage,
        ErrorMessage,
        serialize_wire_message
    )

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
S2_DIR = os.path.join(WORKSPACE_DIR, "poc", "s2-streaming-asr")
S3_DIR = os.path.join(WORKSPACE_DIR, "poc", "s3-local-mt")
S4_DIR = os.path.join(WORKSPACE_DIR, "poc", "s4-incremental-translation")



def get_s2_asr_engine(model_dir: str, num_threads: int = 2):
    s2_pkg = "s2_streaming_asr_engines_isolated_s5"
    if s2_pkg not in sys.modules:
        pkg_mod = types.ModuleType(s2_pkg)
        pkg_mod.__path__ = [os.path.join(S2_DIR, "engines")]
        sys.modules[s2_pkg] = pkg_mod

    base_file = os.path.join(S2_DIR, "engines", "base.py")
    spec_base = importlib.util.spec_from_file_location(f"{s2_pkg}.base", base_file)
    mod_base = importlib.util.module_from_spec(spec_base)
    sys.modules[f"{s2_pkg}.base"] = mod_base
    spec_base.loader.exec_module(mod_base)

    eng_file = os.path.join(S2_DIR, "engines", "sherpa_onnx_engine.py")
    spec_eng = importlib.util.spec_from_file_location(f"{s2_pkg}.sherpa_onnx_engine", eng_file)
    mod_eng = importlib.util.module_from_spec(spec_eng)
    sys.modules[f"{s2_pkg}.sherpa_onnx_engine"] = mod_eng
    spec_eng.loader.exec_module(mod_eng)

    engine = mod_eng.SherpaOnnxStreamingEngine(model_dir, language="multilingual", num_threads=num_threads)
    engine.initialize()
    return engine


def get_s3_marian_engine(model_dir: str, num_threads: int = 2):
    s3_pkg = "s3_local_mt_engines_isolated_s5"
    if s3_pkg not in sys.modules:
        pkg_mod = types.ModuleType(s3_pkg)
        pkg_mod.__path__ = [os.path.join(S3_DIR, "engines")]
        sys.modules[s3_pkg] = pkg_mod

    base_file = os.path.join(S3_DIR, "engines", "base.py")
    spec_base = importlib.util.spec_from_file_location(f"{s3_pkg}.base", base_file)
    mod_base = importlib.util.module_from_spec(spec_base)
    sys.modules[f"{s3_pkg}.base"] = mod_base
    spec_base.loader.exec_module(mod_base)

    eng_file = os.path.join(S3_DIR, "engines", "marian_engine.py")
    spec_eng = importlib.util.spec_from_file_location(f"{s3_pkg}.marian_engine", eng_file)
    mod_eng = importlib.util.module_from_spec(spec_eng)
    sys.modules[f"{s3_pkg}.marian_engine"] = mod_eng
    spec_eng.loader.exec_module(mod_eng)

    engine = mod_eng.MarianCTranslate2Engine(model_dir, num_threads=num_threads)
    engine.initialize()
    return engine


def get_s4_incremental_translator(mt_engine: Any, k: int = 2, buffer: int = 2):
    # Ensure S4 policy modules are loaded
    s4_pkg = "s4_policy_isolated_s5"
    if s4_pkg not in sys.modules:
        pkg_mod = types.ModuleType(s4_pkg)
        pkg_mod.__path__ = [os.path.join(S4_DIR, "policy")]
        sys.modules[s4_pkg] = pkg_mod

    for mod_name in ["state_model", "agreement", "frontier", "streaming_translator"]:
        m_file = os.path.join(S4_DIR, "policy", f"{mod_name}.py")
        spec = importlib.util.spec_from_file_location(f"{s4_pkg}.{mod_name}", m_file)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"{s4_pkg}.{mod_name}"] = mod
        spec.loader.exec_module(mod)

    state_mod = sys.modules[f"{s4_pkg}.state_model"]
    trans_mod = sys.modules[f"{s4_pkg}.streaming_translator"]

    config = state_mod.PolicyConfig(
        agreement_k=k,
        unstable_buffer_tokens=buffer,
        enable_mt_deduplication=True
    )
    return trans_mod.IncrementalTranslator(mt_engine, config)


class StreamingTranslationRuntime:
    """
    Stateful streaming pipeline managing S2 ASR and S4 Incremental Translator.
    Emits serialized JSON wire protocol messages.
    """
    def __init__(
        self,
        asr_engine: Optional[Any] = None,
        mt_engine: Optional[Any] = None,
        k: int = 2,
        buffer: int = 2
    ):
        self.asr_engine = asr_engine
        self.mt_engine = mt_engine
        self.k = k
        self.buffer = buffer
        
        self.translator: Optional[Any] = None
        if self.mt_engine is not None:
            self.translator = get_s4_incremental_translator(self.mt_engine, k=self.k, buffer=self.buffer)

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
