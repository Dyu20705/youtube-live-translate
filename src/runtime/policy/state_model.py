"""
state_model.py - Data models, enums, configuration, and output contracts for Stage S4.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class SegmentStatus(Enum):
    RESET = "RESET"
    ACTIVE = "ACTIVE"
    ENDPOINT = "ENDPOINT"
    FLUSHED = "FLUSHED"


@dataclass
class PolicyConfig:
    """
    Configuration for Local Agreement and Adaptive Frontier policies.
    """
    agreement_k: int = 2
    unstable_buffer_tokens: int = 2
    max_wait_updates: int = 10
    accelerate_on_punctuation: bool = True
    min_source_delta_chars: int = 1
    enable_mt_deduplication: bool = True


@dataclass
class SubtitleState:
    """
    Output contract emitted to UI/renderers and evaluation benchmarks.
    Invariant: display_text is constructed from committed_text + provisional_text.
    committed_text must be strictly immutable within the active segment.
    """
    segment_id: int
    committed_text: str
    provisional_text: str
    display_text: str
    is_final: bool
    source_text: str
    source_revision: int
    frontier_position: int
    mt_calls_count: int
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "committed_text": self.committed_text,
            "provisional_text": self.provisional_text,
            "display_text": self.display_text,
            "is_final": self.is_final,
            "source_text": self.source_text,
            "source_revision": self.source_revision,
            "frontier_position": self.frontier_position,
            "mt_calls_count": self.mt_calls_count,
            "metrics": self.metrics,
        }


@dataclass
class SessionMetrics:
    """
    Telemetry and diagnostic metrics accumulated over a streaming session or segment.
    """
    source_updates: int = 0
    translation_updates: int = 0
    mt_calls: int = 0
    committed_prefix_revision_count: int = 0
    provisional_revision_count: int = 0
    frontier_advancement_count: int = 0
    commit_conflict_count: int = 0
    finalization_commit_count: int = 0
    forced_commit_count: int = 0
    policy_overhead_times_ms: List[float] = field(default_factory=list)

    @property
    def mt_call_reduction_ratio(self) -> float:
        if self.source_updates == 0:
            return 0.0
        return round(1.0 - (self.mt_calls / self.source_updates), 4)

    def to_dict(self) -> Dict[str, Any]:
        overhead_p50 = 0.0
        overhead_p95 = 0.0
        if self.policy_overhead_times_ms:
            sorted_ov = sorted(self.policy_overhead_times_ms)
            overhead_p50 = round(float(sorted_ov[len(sorted_ov) // 2]), 3)
            p95_idx = min(int(len(sorted_ov) * 0.95), len(sorted_ov) - 1)
            overhead_p95 = round(float(sorted_ov[p95_idx]), 3)

        return {
            "source_updates": self.source_updates,
            "translation_updates": self.translation_updates,
            "mt_calls": self.mt_calls,
            "mt_call_reduction_ratio": self.mt_call_reduction_ratio,
            "committed_prefix_revision_count": self.committed_prefix_revision_count,
            "provisional_revision_count": self.provisional_revision_count,
            "frontier_advancement_count": self.frontier_advancement_count,
            "commit_conflict_count": self.commit_conflict_count,
            "finalization_commit_count": self.finalization_commit_count,
            "forced_commit_count": self.forced_commit_count,
            "policy_overhead_p50_ms": overhead_p50,
            "policy_overhead_p95_ms": overhead_p95,
        }
