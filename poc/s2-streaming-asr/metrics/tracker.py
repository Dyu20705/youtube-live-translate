"""
tracker.py - Telemetry and Realtime Performance Tracker for S2 streaming benchmark.
"""

import time
import os
import psutil
from typing import List, Dict, Any, Optional


class PerformanceTracker:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.baseline_ram_mb = self.process.memory_info().rss / (1024 * 1024)
        
        self.audio_start_time: Optional[float] = None
        self.audio_end_time: Optional[float] = None
        
        self.total_audio_duration_sec: float = 0.0
        self.total_processing_time_sec: float = 0.0
        
        self.ttft_ms: Optional[float] = None       # Time To First Transcript
        self.ttfuh_ms: Optional[float] = None      # Time To First Useful Hypothesis (>3 chars)
        self.final_latency_ms: Optional[float] = None # Latency after audio stream ends until final transcript
        
        self.hypotheses_timeline: List[Dict[str, Any]] = []
        
        self.cpu_samples: List[float] = []
        self.peak_ram_mb: float = self.baseline_ram_mb
        self.last_cpu_check = time.time()

    def start(self):
        self.audio_start_time = time.perf_counter()
        self.process.cpu_percent() # reset baseline

    def sample_system_resources(self):
        now = time.perf_counter()
        if now - self.last_cpu_check >= 0.05:
            self.last_cpu_check = now
            cpu = self.process.cpu_percent()
            self.cpu_samples.append(cpu)
            
            ram = self.process.memory_info().rss / (1024 * 1024)
            if ram > self.peak_ram_mb:
                self.peak_ram_mb = ram

    def record_chunk_processed(self, chunk_duration_sec: float, processing_time_sec: float):
        self.total_audio_duration_sec += chunk_duration_sec
        self.total_processing_time_sec += processing_time_sec
        self.sample_system_resources()

    def record_hypothesis(self, text: str, is_final: bool = False):
        now = time.perf_counter()
        elapsed_audio_ms = (now - self.audio_start_time) * 1000.0 if self.audio_start_time else 0.0
        
        trimmed = text.strip()
        
        if trimmed:
            if self.ttft_ms is None:
                self.ttft_ms = elapsed_audio_ms
            if self.ttfuh_ms is None and len(trimmed) >= 4:
                self.ttfuh_ms = elapsed_audio_ms

        self.hypotheses_timeline.append({
            "timestamp_ms": round(elapsed_audio_ms, 2),
            "text": text,
            "is_final": is_final
        })

    def finish_stream(self, final_text: str):
        now = time.perf_counter()
        self.audio_end_time = now
        
        # Calculate final latency (time taken to produce final transcript after last chunk)
        self.record_hypothesis(final_text, is_final=True)
        self.sample_system_resources()

    def set_finalization_latency(self, finalization_duration_sec: float):
        self.final_latency_ms = finalization_duration_sec * 1000.0
        self.total_processing_time_sec += finalization_duration_sec

    def compute_summary(self) -> Dict[str, Any]:
        rtf = (self.total_processing_time_sec / max(0.001, self.total_audio_duration_sec))
        
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0.0
        peak_cpu = max(self.cpu_samples) if self.cpu_samples else 0.0
        ram_delta = self.peak_ram_mb - self.baseline_ram_mb

        return {
            "ttft_ms": round(self.ttft_ms, 2) if self.ttft_ms is not None else -1.0,
            "ttfuh_ms": round(self.ttfuh_ms, 2) if self.ttfuh_ms is not None else -1.0,
            "final_latency_ms": round(self.final_latency_ms, 2) if self.final_latency_ms is not None else 0.0,
            "audio_duration_sec": round(self.total_audio_duration_sec, 2),
            "total_processing_time_sec": round(self.total_processing_time_sec, 3),
            "rtf": round(rtf, 4),
            "rtf_realtime_capable": bool(rtf < 1.0),
            "avg_cpu_percent": round(avg_cpu, 1),
            "peak_cpu_percent": round(peak_cpu, 1),
            "baseline_ram_mb": round(self.baseline_ram_mb, 1),
            "peak_ram_mb": round(self.peak_ram_mb, 1),
            "ram_delta_mb": round(ram_delta, 1)
        }
