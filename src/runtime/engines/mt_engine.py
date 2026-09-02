"""
mt_engine.py - CTranslate2 INT8 runtime for Helsinki-NLP/opus-mt-ja-en (Marian).
"""

import time
from pathlib import Path
from typing import List, Optional
import ctranslate2
from transformers import MarianTokenizer

from .base import MTEngine, TranslationResult


class MarianCTranslate2Engine(MTEngine):
    def __init__(
        self,
        model_dir: str,
        num_threads: int = 2,
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        self.model_dir = Path(model_dir)
        self.num_threads = num_threads
        self.device = device
        self.compute_type = compute_type

        self.translator: Optional[ctranslate2.Translator] = None
        self.tokenizer: Optional[MarianTokenizer] = None

    def initialize(self) -> None:
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Marian model directory not found: {self.model_dir}")

        # Load local tokenizer & CTranslate2 translator
        self.tokenizer = MarianTokenizer.from_pretrained(str(self.model_dir))
        self.translator = ctranslate2.Translator(
            model_path=str(self.model_dir),
            device=self.device,
            compute_type=self.compute_type,
            intra_threads=self.num_threads,
            inter_threads=1
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

        return TranslationResult(
            target_text=target_text,
            source_text=text,
            tokenizer_time_ms=round((t1 - t0) * 1000.0, 3),
            inference_time_ms=round((t2 - t1) * 1000.0, 3),
            detokenizer_time_ms=round((t3 - t2) * 1000.0, 3),
            total_time_ms=round((t3 - t0) * 1000.0, 3),
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
