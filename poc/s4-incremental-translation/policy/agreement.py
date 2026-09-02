"""
agreement.py - Tokenization, longest common prefix, and Local Agreement calculation.
"""

import re
from typing import List, Optional


PUNCTUATION_NO_SPACE_BEFORE = {",", ".", "!", "?", ":", ";", "%", "}", "]", ")", "'", "\"", "…"}
PUNCTUATION_NO_SPACE_AFTER = {"{", "[", "(", "\"", "'", "$", "@"}


def tokenize_words(text: str) -> List[str]:
    """
    Tokenizes English text into words, contractions, and punctuation symbols.
    Example: "Hello, I'm here." -> ["Hello", ",", "I'm", "here", "."]
    """
    if not text:
        return []
    # Matches words including apostrophes for contractions, or individual non-whitespace characters
    tokens = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|[^\w\s]", text, re.UNICODE)
    return tokens


def detokenize_words(tokens: List[str]) -> str:
    """
    Reconstructs natural English text from a token sequence with proper punctuation spacing.
    """
    if not tokens:
        return ""

    result = []
    for i, token in enumerate(tokens):
        if i == 0:
            result.append(token)
            continue

        prev = tokens[i - 1]
        if token in PUNCTUATION_NO_SPACE_BEFORE:
            result.append(token)
        elif prev in PUNCTUATION_NO_SPACE_AFTER:
            result.append(token)
        else:
            result.append(" " + token)

    return "".join(result).strip()


def longest_common_prefix_tokens(tokens_a: List[str], tokens_b: List[str]) -> List[str]:
    """
    Computes the Longest Common Prefix (LCP) between two token sequences.
    """
    min_len = min(len(tokens_a), len(tokens_b))
    prefix = []
    for i in range(min_len):
        if tokens_a[i] == tokens_b[i]:
            prefix.append(tokens_a[i])
        else:
            break
    return prefix


class LocalAgreementTracker:
    """
    Tracks consecutive translation hypotheses and computes the stable local agreement prefix.
    A prefix is considered agreed if it remains identical across K consecutive updates.
    """

    def __init__(self, k: int = 2, max_history: int = 10):
        if k < 1:
            raise ValueError(f"Agreement K must be >= 1, got {k}")
        self.k = k
        self.max_history = max_history
        self.history: List[List[str]] = []

    def add_hypothesis(self, tokens: List[str]) -> None:
        """
        Appends a new candidate hypothesis token list to history.
        """
        self.history.append(tokens)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_agreement_prefix(self, k: Optional[int] = None) -> List[str]:
        """
        Computes the LCP across the last K hypotheses in history.
        If history has fewer than K items, returns an empty list.
        """
        effective_k = k if k is not None else self.k
        if len(self.history) < effective_k:
            return []

        recent = self.history[-effective_k:]
        common = recent[0]
        for next_tokens in recent[1:]:
            common = longest_common_prefix_tokens(common, next_tokens)
            if not common:
                break
        return common

    def reset(self) -> None:
        """
        Clears hypothesis history.
        """
        self.history.clear()
