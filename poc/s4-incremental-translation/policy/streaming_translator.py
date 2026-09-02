"""
streaming_translator.py - State-machine controller for S4 incremental translation.
"""

import time
from typing import Optional, Dict, Any, List
from .state_model import SegmentStatus, PolicyConfig, SubtitleState, SessionMetrics
from .agreement import tokenize_words, detokenize_words, LocalAgreementTracker
from .frontier import AdaptiveFrontierController

try:
    from ...s3_local_mt.engines.base import MTEngine, TranslationResult
except (ImportError, ValueError):
    try:
        from engines.base import MTEngine, TranslationResult
    except (ImportError, ValueError):
        from typing import Any as MTEngine, Any as TranslationResult


class IncrementalTranslator:
    """
    Deterministic, stateful streaming translation controller that manages the
    transition from unstable ASR partials to an immutable committed prefix and
    revisable provisional suffix.
    """

    def __init__(
        self,
        mt_engine: Any,
        config: Optional[PolicyConfig] = None
    ):
        self.mt_engine = mt_engine
        self.config = config or PolicyConfig()
        
        self.agreement_tracker = LocalAgreementTracker(
            k=self.config.agreement_k,
            max_history=self.config.max_wait_updates + 5
        )
        self.frontier_controller = AdaptiveFrontierController(self.config)
        
        self.session_metrics = SessionMetrics()
        self.segment_id: int = 1
        self.segment_status: SegmentStatus = SegmentStatus.RESET
        
        # Segment state
        self.latest_source_text: str = ""
        self.source_revision: int = 0
        self.consecutive_uncommitted_updates: int = 0
        
        self.committed_tokens: List[str] = []
        self.committed_text: str = ""
        self.provisional_tokens: List[str] = []
        self.provisional_text: str = ""
        self.display_text: str = ""
        self.candidate_tokens: List[str] = []
        self.candidate_text: str = ""
        
        self.last_emitted_state: Optional[SubtitleState] = None

    def reset(self) -> None:
        """
        Clears all segment-level state and prepares for the next segment.
        """
        self.agreement_tracker.reset()
        self.segment_status = SegmentStatus.RESET
        self.latest_source_text = ""
        self.source_revision = 0
        self.consecutive_uncommitted_updates = 0
        self.committed_tokens.clear()
        self.committed_text = ""
        self.provisional_tokens.clear()
        self.provisional_text = ""
        self.display_text = ""
        self.candidate_tokens.clear()
        self.candidate_text = ""
        self.last_emitted_state = None

    def start_segment(self, segment_id: Optional[int] = None) -> None:
        """
        Initializes a new segment, incrementing segment_id if not specified.
        """
        self.reset()
        if segment_id is not None:
            self.segment_id = segment_id
        else:
            self.segment_id += 1
        self.segment_status = SegmentStatus.ACTIVE

    def update_partial(self, source_text: str) -> SubtitleState:
        """
        Processes a streaming partial ASR transcript update.
        """
        t_start = time.perf_counter()

        # If previous segment was flushed, automatically advance segment_id
        if self.segment_status == SegmentStatus.FLUSHED:
            self.start_segment()
        elif self.segment_status == SegmentStatus.RESET:
            self.segment_status = SegmentStatus.ACTIVE

        clean_source = source_text.strip()
        self.session_metrics.source_updates += 1

        # 1. Deduplication & Empty Handling
        if not clean_source:
            t_end = time.perf_counter()
            overhead_ms = (t_end - t_start) * 1000.0
            self.session_metrics.policy_overhead_times_ms.append(overhead_ms)
            return SubtitleState(
                segment_id=self.segment_id,
                committed_text=self.committed_text,
                provisional_text="",
                display_text=self.committed_text,
                is_final=False,
                source_text="",
                source_revision=self.source_revision,
                frontier_position=len(self.committed_tokens),
                mt_calls_count=self.session_metrics.mt_calls,
                metrics={"policy_overhead_ms": round(overhead_ms, 3), "mt_ms": 0.0}
            )

        if self.config.enable_mt_deduplication and clean_source == self.latest_source_text and self.last_emitted_state is not None:
            # Source text has not changed - skip MT call
            t_end = time.perf_counter()
            overhead_ms = (t_end - t_start) * 1000.0
            self.session_metrics.policy_overhead_times_ms.append(overhead_ms)
            return SubtitleState(
                segment_id=self.segment_id,
                committed_text=self.committed_text,
                provisional_text=self.provisional_text,
                display_text=self.display_text,
                is_final=False,
                source_text=clean_source,
                source_revision=self.source_revision,
                frontier_position=len(self.committed_tokens),
                mt_calls_count=self.session_metrics.mt_calls,
                metrics={"policy_overhead_ms": round(overhead_ms, 3), "mt_ms": 0.0, "deduplicated": True}
            )

        # 2. MT Inference
        self.latest_source_text = clean_source
        self.source_revision += 1

        t_mt_start = time.perf_counter()
        mt_res = self.mt_engine.translate(clean_source, beam_size=1)
        t_mt_end = time.perf_counter()
        mt_ms = (t_mt_end - t_mt_start) * 1000.0
        
        self.session_metrics.mt_calls += 1
        self.session_metrics.translation_updates += 1

        self.candidate_text = mt_res.target_text.strip()
        self.candidate_tokens = tokenize_words(self.candidate_text)

        # 3. Local Agreement Tracking
        self.agreement_tracker.add_hypothesis(self.candidate_tokens)
        agreement_tokens = self.agreement_tracker.get_agreement_prefix()

        # 4. Adaptive Frontier Decision
        prev_committed_tokens = list(self.committed_tokens)
        prev_provisional_text = self.provisional_text

        new_commit_idx, is_conflict, did_advance = self.frontier_controller.decide_frontier(
            committed_tokens=self.committed_tokens,
            candidate_tokens=self.candidate_tokens,
            agreement_tokens=agreement_tokens,
            source_text=clean_source,
            is_final=False,
            consecutive_uncommitted_updates=self.consecutive_uncommitted_updates
        )

        if is_conflict:
            self.session_metrics.commit_conflict_count += 1
            # Hard Invariant: NEVER modify committed tokens
            # Determine best provisional suffix from candidate
            if len(self.candidate_tokens) > len(self.committed_tokens):
                self.provisional_tokens = self.candidate_tokens[len(self.committed_tokens):]
            else:
                self.provisional_tokens = self.candidate_tokens
            self.consecutive_uncommitted_updates += 1
        elif did_advance:
            self.committed_tokens = self.candidate_tokens[:new_commit_idx]
            self.provisional_tokens = self.candidate_tokens[new_commit_idx:]
            self.session_metrics.frontier_advancement_count += 1
            self.consecutive_uncommitted_updates = 0
        else:
            self.provisional_tokens = self.candidate_tokens[len(self.committed_tokens):]
            self.consecutive_uncommitted_updates += 1

        # Hard invariant validation: committed tokens MUST be a prefix extension of prev_committed_tokens
        if self.committed_tokens[:len(prev_committed_tokens)] != prev_committed_tokens or len(self.committed_tokens) < len(prev_committed_tokens):
            self.session_metrics.committed_prefix_revision_count += 1
            # Enforce recovery: keep previous committed tokens
            self.committed_tokens = prev_committed_tokens

        self.committed_text = detokenize_words(self.committed_tokens)
        self.provisional_text = detokenize_words(self.provisional_tokens)

        # Construct unified display text
        all_display_tokens = self.committed_tokens + self.provisional_tokens
        self.display_text = detokenize_words(all_display_tokens)

        if self.provisional_text != prev_provisional_text:
            self.session_metrics.provisional_revision_count += 1

        t_end = time.perf_counter()
        total_step_ms = (t_end - t_start) * 1000.0
        overhead_ms = max(0.0, total_step_ms - mt_ms)
        self.session_metrics.policy_overhead_times_ms.append(overhead_ms)

        state = SubtitleState(
            segment_id=self.segment_id,
            committed_text=self.committed_text,
            provisional_text=self.provisional_text,
            display_text=self.display_text,
            is_final=False,
            source_text=clean_source,
            source_revision=self.source_revision,
            frontier_position=len(self.committed_tokens),
            mt_calls_count=self.session_metrics.mt_calls,
            metrics={
                "policy_overhead_ms": round(overhead_ms, 3),
                "mt_inference_ms": round(mt_ms, 2),
                "total_step_ms": round(total_step_ms, 2),
                "is_conflict": is_conflict,
                "did_advance": did_advance,
            }
        )
        self.last_emitted_state = state
        return state

    def finalize_segment(self, final_source_text: Optional[str] = None) -> SubtitleState:
        """
        Finalizes the active segment, flushes all remaining provisional text into
        the committed prefix, emits the final SubtitleState, and transitions status to FLUSHED.
        """
        t_start = time.perf_counter()
        clean_final_src = (final_source_text or self.latest_source_text).strip()

        mt_ms = 0.0
        # If a new or non-empty final source is provided and differs from latest
        if clean_final_src and clean_final_src != self.latest_source_text:
            self.session_metrics.source_updates += 1
            self.latest_source_text = clean_final_src
            self.source_revision += 1
            t_mt_0 = time.perf_counter()
            mt_res = self.mt_engine.translate(clean_final_src, beam_size=1)
            t_mt_1 = time.perf_counter()
            mt_ms = (t_mt_1 - t_mt_0) * 1000.0
            self.session_metrics.mt_calls += 1
            self.candidate_text = mt_res.target_text.strip()
            self.candidate_tokens = tokenize_words(self.candidate_text)


        prev_committed = list(self.committed_tokens)
        new_commit_idx, is_conflict, did_advance = self.frontier_controller.decide_frontier(
            committed_tokens=self.committed_tokens,
            candidate_tokens=self.candidate_tokens,
            agreement_tokens=self.candidate_tokens,
            source_text=clean_final_src,
            is_final=True,
            consecutive_uncommitted_updates=self.consecutive_uncommitted_updates
        )

        if not is_conflict:
            self.committed_tokens = list(self.candidate_tokens)
        else:
            # Append non-conflicting remainder
            if len(self.candidate_tokens) > len(self.committed_tokens):
                self.committed_tokens = self.committed_tokens + self.candidate_tokens[len(self.committed_tokens):]

        self.provisional_tokens.clear()
        self.committed_text = detokenize_words(self.committed_tokens)
        self.provisional_text = ""
        self.display_text = self.committed_text
        self.segment_status = SegmentStatus.FLUSHED
        self.session_metrics.finalization_commit_count += 1

        t_end = time.perf_counter()
        total_step_ms = (t_end - t_start) * 1000.0
        overhead_ms = max(0.0, total_step_ms - mt_ms)
        self.session_metrics.policy_overhead_times_ms.append(overhead_ms)

        state = SubtitleState(
            segment_id=self.segment_id,
            committed_text=self.committed_text,
            provisional_text="",
            display_text=self.display_text,
            is_final=True,
            source_text=clean_final_src,
            source_revision=self.source_revision,
            frontier_position=len(self.committed_tokens),
            mt_calls_count=self.session_metrics.mt_calls,
            metrics={
                "policy_overhead_ms": round(overhead_ms, 3),
                "mt_inference_ms": round(mt_ms, 2),
                "total_step_ms": round(total_step_ms, 2),
                "is_finalization": True,
            }
        )
        self.last_emitted_state = state
        return state
