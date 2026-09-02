"""
marian_engine.py - CTranslate2 INT8 runtime for Helsinki-NLP/opus-mt-ja-en (Marian).
"""

import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import ctranslate2
from transformers import MarianTokenizer

try:
    from .base import MTEngine, TranslationResult, MTModelInfo
except (ImportError, ValueError):
    from engines.base import MTEngine, TranslationResult, MTModelInfo


class MarianCTranslate2Engine(MTEngine):
    def __init__(
        self,
        model_dir: str,
        num_threads: int = 4,
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        self.model_dir = Path(model_dir)
        self.num_threads = num_threads
        self.device = device
        self.compute_type = compute_type
        
        self.translator: Optional[ctranslate2.Translator] = None
        self.tokenizer: Optional[MarianTokenizer] = None
        self.model_info: Optional[MTModelInfo] = None
        self.model_size_mb: float = 0.0

    def initialize(self) -> None:
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Marian model directory not found: {self.model_dir}")

        total_bytes = sum(f.stat().st_size for f in self.model_dir.glob("*") if f.is_file())
        self.model_size_mb = round(total_bytes / (1024 * 1024), 2)

        start_t = time.perf_counter()
        
        # Load local tokenizer
        self.tokenizer = MarianTokenizer.from_pretrained(str(self.model_dir))
        
        # Load CTranslate2 translator
        self.translator = ctranslate2.Translator(
            model_path=str(self.model_dir),
            device=self.device,
            compute_type=self.compute_type,
            intra_threads=self.num_threads,
            inter_threads=1
        )
        init_duration_ms = (time.perf_counter() - start_t) * 1000.0

        self.model_info = MTModelInfo(
            engine_name="CTranslate2-Marian",
            model_name="opus-mt-ja-en",
            model_family="MarianMT / OPUS-MT",
            quantization=self.compute_type,
            model_size_mb=self.model_size_mb,
            src_lang="ja",
            tgt_lang="en",
            is_multilingual=False,
            parameters={
                "num_threads": self.num_threads,
                "device": self.device,
                "compute_type": self.compute_type,
                "init_duration_ms": round(init_duration_ms, 2)
            }
        )

    def translate(
        self,
        text: str,
        beam_size: int = 1,
        max_decoding_length: int = 256
    ) -> TranslationResult:
        if self.translator is None or self.tokenizer is None:
            self.initialize()

        if not text.strip():
            return TranslationResult(
                target_text="",
                source_text=text,
                tokenizer_time_ms=0.0,
                inference_time_ms=0.0,
                detokenizer_time_ms=0.0,
                total_time_ms=0.0,
                src_tokens_count=0,
                tgt_tokens_count=0,
                raw_tokens=[]
            )

        # 1. Tokenize
        t0 = time.perf_counter()
        token_ids = self.tokenizer.encode(text)
        src_tokens = self.tokenizer.convert_ids_to_tokens(token_ids)
        t1 = time.perf_counter()

        # 2. Translate with CTranslate2
        results = self.translator.translate_batch(
            [src_tokens],
            beam_size=beam_size,
            max_decoding_length=max_decoding_length,
            sampling_topk=1,
            repetition_penalty=1.0
        )
        t2 = time.perf_counter()

        # 3. Detokenize
        tgt_tokens = results[0].hypotheses[0]
        tgt_ids = self.tokenizer.convert_tokens_to_ids(tgt_tokens)
        target_text = self.tokenizer.decode(tgt_ids, skip_special_tokens=True).strip()
        t3 = time.perf_counter()

        tok_ms = (t1 - t0) * 1000.0
        infer_ms = (t2 - t1) * 1000.0
        detok_ms = (t3 - t2) * 1000.0
        total_ms = (t3 - t0) * 1000.0

        return TranslationResult(
            target_text=target_text,
            source_text=text,
            tokenizer_time_ms=round(tok_ms, 3),
            inference_time_ms=round(infer_ms, 3),
            detokenizer_time_ms=round(detok_ms, 3),
            total_time_ms=round(total_ms, 3),
            src_tokens_count=len(src_tokens),
            tgt_tokens_count=len(tgt_tokens),
            raw_tokens=tgt_tokens
        )

    def translate_batch(
        self,
        texts: List[str],
        beam_size: int = 1,
        max_decoding_length: int = 256
    ) -> List[TranslationResult]:
        return [self.translate(t, beam_size=beam_size, max_decoding_length=max_decoding_length) for t in texts]

    def get_model_info(self) -> MTModelInfo:
        if self.model_info is None:
            self.initialize()
        return self.model_info
