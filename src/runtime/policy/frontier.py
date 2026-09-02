"""
frontier.py - Adaptive Frontier controller and commit decision logic.
"""

from typing import List, Tuple, Dict, Any
from .state_model import PolicyConfig
from .agreement import detokenize_words


JA_SENTENCE_FINALS = {"。", "！", "？", "\n", "ます", "です", "でした", "ました", "ですね", "ですよ", "でしょうか"}
EN_CLAUSE_PUNCTUATION = {",", ".", "!", "?", ";", ":"}


class AdaptiveFrontierController:
    """
    Decides the safe commit frontier between the immutable committed prefix
    and the revisable provisional suffix.
    """

    def __init__(self, config: PolicyConfig):
        self.config = config

    def decide_frontier(
        self,
        committed_tokens: List[str],
        candidate_tokens: List[str],
        agreement_tokens: List[str],
        source_text: str,
        is_final: bool = False,
        consecutive_uncommitted_updates: int = 0
    ) -> Tuple[int, bool, bool]:
        """
        Determines the new token commit index into candidate_tokens.

        Returns:
            (new_commit_index, is_conflict, did_advance)
        """
        curr_committed_len = len(committed_tokens)

        # 1. Finalization / Endpoint Flush
        if is_final:
            # If candidate matches committed prefix, commit everything
            if candidate_tokens[:curr_committed_len] == committed_tokens:
                return len(candidate_tokens), False, len(candidate_tokens) > curr_committed_len
            else:
                # Conflict on finalization: keep committed tokens, force commit remainder
                return curr_committed_len, True, False

        # 2. Source Rewrite / Translation Inversion Conflict Check
        if curr_committed_len > 0:
            if len(candidate_tokens) < curr_committed_len or candidate_tokens[:curr_committed_len] != committed_tokens:
                # Conflict: Candidate diverged from already committed prefix!
                # Invariant: NEVER truncate or modify committed tokens.
                return curr_committed_len, True, False

        # 3. Normal Adaptive Frontier Calculation
        agreement_len = len(agreement_tokens)
        candidate_len = len(candidate_tokens)

        if agreement_len <= curr_committed_len:
            # No new agreed tokens beyond current committed prefix
            return curr_committed_len, False, False

        # Base candidate boundary with protected unstable suffix buffer
        buffer_tokens = self.config.unstable_buffer_tokens
        safe_boundary = max(curr_committed_len, min(agreement_len, candidate_len - buffer_tokens))

        # Check for clause / punctuation boundary acceleration
        if self.config.accelerate_on_punctuation:
            # Find the furthest punctuation mark in the agreed range [curr_committed_len, agreement_len]
            furthest_punct_idx = -1
            for idx in range(curr_committed_len, agreement_len):
                token = candidate_tokens[idx]
                if token in EN_CLAUSE_PUNCTUATION:
                    furthest_punct_idx = idx + 1  # include punctuation

            if furthest_punct_idx > safe_boundary:
                safe_boundary = furthest_punct_idx

            # Japanese sentence-final marker acceleration
            if any(source_text.endswith(marker) for marker in JA_SENTENCE_FINALS):
                safe_boundary = max(safe_boundary, agreement_len)

        # Max wait bound fallback
        if consecutive_uncommitted_updates >= self.config.max_wait_updates:
            safe_boundary = max(safe_boundary, agreement_len)

        safe_boundary = max(curr_committed_len, min(safe_boundary, candidate_len))
        did_advance = safe_boundary > curr_committed_len

        return safe_boundary, False, did_advance
