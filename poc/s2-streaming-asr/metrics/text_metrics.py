import re
import unicodedata
from typing import Dict, Any, Sequence

RE_EN_PUNCT = re.compile(r"[^\w\s']")
RE_WHITESPACE = re.compile(r"\s+")
RE_JA_PUNCT = re.compile(r"[\s、。！？\.,!?~〜「」『』（）()\[\]\-_:;・]+")


def normalize_text_en(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    stripped = RE_EN_PUNCT.sub(" ", normalized)
    return RE_WHITESPACE.sub(" ", stripped).strip()


def normalize_text_ja(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return RE_JA_PUNCT.sub("", normalized)


def levenshtein_distance(seq1: Sequence, seq2: Sequence) -> int:
    if seq1 == seq2:
        return 0

    len1, len2 = len(seq1), len(seq2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    # Optimize to O(min(m, n)) space complexity
    if len1 > len2:
        seq1, seq2 = seq2, seq1
        len1, len2 = len2, len1

    current_row = list(range(len1 + 1))

    for i in range(1, len2 + 1):
        previous_row = current_row
        current_row = [i] + [0] * len1
        s2_char = seq2[i - 1]

        for j in range(1, len1 + 1):
            add = previous_row[j] + 1
            delete = current_row[j - 1] + 1
            change = previous_row[j - 1] if seq1[j - 1] == s2_char else previous_row[j - 1] + 1
            current_row[j] = min(add, delete, change)

    return current_row[len1]


def compute_wer(reference: str, hypothesis: str) -> float:
    ref_words = normalize_text_en(reference).split()
    hyp_words = normalize_text_en(hypothesis).split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    distance = levenshtein_distance(ref_words, hyp_words)
    return float(distance) / len(ref_words)


def compute_cer(reference: str, hypothesis: str) -> float:
    ref_chars = normalize_text_ja(reference)
    hyp_chars = normalize_text_ja(hypothesis)

    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0

    distance = levenshtein_distance(ref_chars, hyp_chars)
    return float(distance) / len(ref_chars)


def evaluate_accuracy(reference: str, hypothesis: str, language: str = "en") -> Dict[str, Any]:
    if language.lower().startswith("ja"):
        cer = compute_cer(reference, hypothesis)
        return {
            "primary_error_metric": "CER",
            "cer": round(cer, 4),
            "wer": None,
            "char_accuracy": round(max(0.0, 1.0 - cer), 4),
            "ref_normalized": normalize_text_ja(reference),
            "hyp_normalized": normalize_text_ja(hypothesis)
        }

    wer = compute_wer(reference, hypothesis)
    cer = compute_cer(reference, hypothesis)
    return {
        "primary_error_metric": "WER",
        "wer": round(wer, 4),
        "cer": round(cer, 4),
        "word_accuracy": round(max(0.0, 1.0 - wer), 4),
        "ref_normalized": normalize_text_en(reference),
        "hyp_normalized": normalize_text_en(hypothesis)
    }
