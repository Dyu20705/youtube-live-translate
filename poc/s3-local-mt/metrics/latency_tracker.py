"""
latency_tracker.py - Latency profiling, distribution statistics, and phase breakdown.
"""

from typing import List, Dict, Any, Optional
import numpy as np


def compute_distribution_stats(values: List[float]) -> Dict[str, float]:
    """Computes min, p50, p90, p95, p99, max, mean, and stddev from a list of latencies in ms."""
    if not values:
        return {
            "min": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "stddev": 0.0,
            "count": 0
        }

    arr = np.array(values, dtype=np.float64)
    return {
        "min": round(float(np.min(arr)), 2),
        "p50": round(float(np.percentile(arr, 50)), 2),
        "p90": round(float(np.percentile(arr, 90)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "p99": round(float(np.percentile(arr, 99)), 2),
        "max": round(float(np.max(arr)), 2),
        "mean": round(float(np.mean(arr)), 2),
        "stddev": round(float(np.std(arr)), 2),
        "count": len(values)
    }


class LatencyTracker:
    def __init__(self):
        self.cold_start_ms: float = 0.0
        self.total_times_ms: List[float] = []
        self.tokenizer_times_ms: List[float] = []
        self.inference_times_ms: List[float] = []
        self.detokenizer_times_ms: List[float] = []

    def set_cold_start(self, duration_ms: float) -> None:
        self.cold_start_ms = round(duration_ms, 2)

    def record_run(
        self,
        total_ms: float,
        tok_ms: float,
        infer_ms: float,
        detok_ms: float
    ) -> None:
        self.total_times_ms.append(total_ms)
        self.tokenizer_times_ms.append(tok_ms)
        self.inference_times_ms.append(infer_ms)
        self.detokenizer_times_ms.append(detok_ms)

    def compute_summary(self) -> Dict[str, Any]:
        return {
            "cold_start_ms": self.cold_start_ms,
            "total_latency": compute_distribution_stats(self.total_times_ms),
            "tokenizer_latency": compute_distribution_stats(self.tokenizer_times_ms),
            "inference_latency": compute_distribution_stats(self.inference_times_ms),
            "detokenizer_latency": compute_distribution_stats(self.detokenizer_times_ms)
        }
