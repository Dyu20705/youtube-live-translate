#!/usr/bin/env python3
"""
download_and_convert.py - Downloads and converts Marian and NLLB models to local CTranslate2 INT8 format.
"""

import os
import sys
import shutil
import time
from pathlib import Path
import ctranslate2
from transformers import AutoTokenizer, MarianTokenizer

MODELS_DIR = Path(__file__).parent.resolve()
MARIAN_SRC = "Helsinki-NLP/opus-mt-ja-en"
MARIAN_DEST = MODELS_DIR / "opus-mt-ja-en-ct2-int8"

NLLB_SRC = "facebook/nllb-200-distilled-600M"
NLLB_DEST = MODELS_DIR / "nllb-200-600m-ct2-int8"


def convert_marian(force: bool = False):
    print(f"\n[1/2] Preparing Marian model: {MARIAN_SRC} -> {MARIAN_DEST}")
    if MARIAN_DEST.exists() and not force:
        print(f"  Model directory already exists at {MARIAN_DEST}. Skipping conversion.")
        return

    MARIAN_DEST.mkdir(parents=True, exist_ok=True)
    
    # Save tokenizer assets
    print("  Downloading and saving Marian tokenizer...")
    tokenizer = MarianTokenizer.from_pretrained(MARIAN_SRC)
    tokenizer.save_pretrained(str(MARIAN_DEST))

    # Convert model to CTranslate2 INT8
    print("  Converting Marian model to CTranslate2 INT8...")
    start_t = time.perf_counter()
    converter = ctranslate2.converters.TransformersConverter(MARIAN_SRC)
    converter.convert(
        output_dir=str(MARIAN_DEST),
        quantization="int8",
        force=True
    )
    duration = time.perf_counter() - start_t
    print(f"  Marian conversion completed in {duration:.2f}s.")


def convert_nllb(force: bool = False):
    print(f"\n[2/2] Preparing NLLB model: {NLLB_SRC} -> {NLLB_DEST}")
    if NLLB_DEST.exists() and not force:
        print(f"  Model directory already exists at {NLLB_DEST}. Skipping conversion.")
        return

    NLLB_DEST.mkdir(parents=True, exist_ok=True)

    # Save tokenizer assets
    print("  Downloading and saving NLLB tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(NLLB_SRC, src_lang="jpn_Jpan")
    tokenizer.save_pretrained(str(NLLB_DEST))

    # Convert model to CTranslate2 INT8
    print("  Converting NLLB model to CTranslate2 INT8...")
    start_t = time.perf_counter()
    converter = ctranslate2.converters.TransformersConverter(NLLB_SRC)
    converter.convert(
        output_dir=str(NLLB_DEST),
        quantization="int8",
        force=True
    )
    duration = time.perf_counter() - start_t
    print(f"  NLLB conversion completed in {duration:.2f}s.")


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    convert_marian()
    convert_nllb()
    print("\nAll MT models downloaded and converted successfully.")


if __name__ == "__main__":
    main()
