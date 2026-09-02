"""
s4_benchmark.py - Comparative evaluation benchmark between S3 Naive Retranslation and S4 Adaptive Frontier Stabilization.
"""

import time
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np

from policy.state_model import PolicyConfig, SubtitleState
from policy.streaming_translator import IncrementalTranslator
from metrics.s4_metrics import analyze_s4_session_stability

try:
    from sacrebleu.metrics import CHRF
    chrf_metric = CHRF(word_order=2)
except ImportError:
    chrf_metric = None


def run_comparative_s4_benchmark(
    mt_engine: Any,
    corpus_items: List[Dict[str, Any]],
    partial_variants: List[Dict[str, Any]],
    k_values: List[int] = [1, 2, 3],
    unstable_buffer: int = 2
) -> Dict[str, Any]:
    """
    Executes reproducible benchmark comparing:
    1. S3 Naive Retranslation Baseline (stateless retranslation on each partial)
    2. S4 Adaptive Frontier Translator across K in {1, 2, 3}
    """
    results: Dict[str, Any] = {
        "benchmark_metadata": {
            "num_utterances": len(corpus_items),
            "k_values": k_values,
            "unstable_buffer_tokens": unstable_buffer,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "baseline_s3_naive": {},
        "candidates_s4": {}
    }

    # -------------------------------------------------------------
    # 1. S3 Naive Retranslation Baseline
    # -------------------------------------------------------------
    baseline_tps_list = []
    baseline_destructive_revs = 0
    baseline_complete_rewrites = 0
    baseline_mt_calls = 0
    baseline_source_updates = 0
    baseline_latencies_ms = []

    for item in corpus_items:
        item_id = item["id"]
        variants = [v for v in partial_variants if v["parent_id"] == item_id and v["condition"].startswith("PARTIAL_")]
        variants.sort(key=lambda x: x.get("prefix_ratio", 0))

        hypotheses = []
        states_sim = []
        for step_idx, v in enumerate(variants):
            baseline_source_updates += 1
            src = v["source_text"]
            t0 = time.perf_counter()
            res = mt_engine.translate(src, beam_size=1)
            t1 = time.perf_counter()
            lat_ms = (t1 - t0) * 1000.0
            baseline_latencies_ms.append(lat_ms)
            baseline_mt_calls += 1

            hypotheses.append(res.target_text)
            states_sim.append(SubtitleState(
                segment_id=1,
                committed_text="",
                provisional_text=res.target_text,
                display_text=res.target_text,
                is_final=(step_idx == len(variants) - 1),
                source_text=src,
                source_revision=step_idx + 1,
                frontier_position=0,
                mt_calls_count=baseline_mt_calls,
                metrics={"policy_overhead_ms": 0.0, "total_step_ms": lat_ms}
            ))

        analysis = analyze_s4_session_stability(states_sim)
        baseline_tps_list.append(analysis["average_tps"])
        baseline_destructive_revs += analysis["destructive_revisions"]
        baseline_complete_rewrites += analysis["complete_rewrites"]

    results["baseline_s3_naive"] = {
        "policy_name": "S3 Naive Full Retranslation",
        "average_tps": round(float(np.mean(baseline_tps_list)), 4) if baseline_tps_list else 1.0,
        "destructive_revisions": baseline_destructive_revs,
        "complete_rewrites": baseline_complete_rewrites,
        "committed_prefix_revisions": "N/A (no committed prefix)",
        "source_updates": baseline_source_updates,
        "mt_calls": baseline_mt_calls,
        "mt_call_reduction_ratio": 0.0,
        "step_latency_p50_ms": round(float(np.percentile(baseline_latencies_ms, 50)), 2) if baseline_latencies_ms else 0.0,
        "step_latency_p95_ms": round(float(np.percentile(baseline_latencies_ms, 95)), 2) if baseline_latencies_ms else 0.0,
    }

    # -------------------------------------------------------------
    # 2. S4 Adaptive Frontier Candidates across K
    # -------------------------------------------------------------
    for k in k_values:
        config = PolicyConfig(
            agreement_k=k,
            unstable_buffer_tokens=unstable_buffer,
            enable_mt_deduplication=True
        )
        translator = IncrementalTranslator(mt_engine, config)

        cand_tps_list = []
        cand_destructive_revs = 0
        cand_complete_rewrites = 0
        cand_committed_prefix_revs = 0
        cand_provisional_revs = 0
        cand_frontier_advancements = 0
        cand_commit_delays = []
        cand_policy_overheads = []
        cand_step_latencies = []
        cand_final_chrf = []

        for item in corpus_items:
            item_id = item["id"]
            ref_en = item.get("reference_en", "")
            variants = [v for v in partial_variants if v["parent_id"] == item_id and v["condition"].startswith("PARTIAL_")]
            variants.sort(key=lambda x: x.get("prefix_ratio", 0))

            translator.start_segment()
            session_states = []

            for step_idx, v in enumerate(variants):
                is_last = (step_idx == len(variants) - 1)
                src = v["source_text"]

                t0 = time.perf_counter()
                if is_last:
                    state = translator.finalize_segment(src)
                else:
                    state = translator.update_partial(src)
                t1 = time.perf_counter()

                step_ms = (t1 - t0) * 1000.0
                cand_step_latencies.append(step_ms)
                session_states.append(state)

            analysis = analyze_s4_session_stability(session_states)
            cand_tps_list.append(analysis["display_tps"])
            cand_destructive_revs += analysis["display_revision_count"]
            cand_complete_rewrites += analysis["display_complete_rewrite_count"]
            cand_committed_prefix_revs += analysis["committed_prefix_revisions"]
            cand_provisional_revs += analysis["provisional_revisions"]
            cand_frontier_advancements += analysis["frontier_advancements"]
            cand_commit_delays.append(analysis["commit_delay_steps"])

            if session_states and ref_en and chrf_metric is not None:
                final_text = session_states[-1].display_text
                score = chrf_metric.sentence_score(final_text, [ref_en]).score
                cand_final_chrf.append(score)

        cand_overheads = translator.session_metrics.policy_overhead_times_ms
        p50_ov = round(float(np.percentile(cand_overheads, 50)), 3) if cand_overheads else 0.0
        p95_ov = round(float(np.percentile(cand_overheads, 95)), 3) if cand_overheads else 0.0

        p50_step = round(float(np.percentile(cand_step_latencies, 50)), 2) if cand_step_latencies else 0.0
        p95_step = round(float(np.percentile(cand_step_latencies, 95)), 2) if cand_step_latencies else 0.0

        p95_commit_delay = round(float(np.percentile(cand_commit_delays, 95)), 2) if cand_commit_delays else 0.0
        avg_commit_delay = round(float(np.mean(cand_commit_delays)), 2) if cand_commit_delays else 0.0

        total_provisional_opportunities = len(corpus_items) * 3  # 3 transition steps per utterance
        provisional_revision_rate = round(cand_provisional_revs / total_provisional_opportunities, 4) if total_provisional_opportunities > 0 else 0.0

        results["candidates_s4"][f"s4_k{k}"] = {
            "k": k,
            "unstable_buffer_tokens": unstable_buffer,
            "display_tps": round(float(np.mean(cand_tps_list)), 4) if cand_tps_list else 1.0,
            "display_revision_count": cand_destructive_revs,
            "display_complete_rewrite_count": cand_complete_rewrites,
            "committed_prefix_revision_count": cand_committed_prefix_revs,
            "provisional_revision_count": cand_provisional_revs,
            "provisional_revision_rate": provisional_revision_rate,
            "frontier_advancement_count": cand_frontier_advancements,
            "average_commit_delay_steps": avg_commit_delay,
            "p95_commit_delay_steps": p95_commit_delay,
            "source_update_count": translator.session_metrics.source_updates,
            "translation_update_count": translator.session_metrics.translation_updates,
            "mt_calls": translator.session_metrics.mt_calls,
            "mt_call_reduction_ratio": translator.session_metrics.mt_call_reduction_ratio,
            "policy_overhead_p50_ms": p50_ov,
            "policy_overhead_p95_ms": p95_ov,
            "total_step_p50_ms": p50_step,
            "total_step_p95_ms": p95_step,
            "average_final_chrf_pp": round(float(np.mean(cand_final_chrf)), 2) if cand_final_chrf else 0.0,
            "commit_conflict_count": translator.session_metrics.commit_conflict_count,
            "finalization_commit_count": translator.session_metrics.finalization_commit_count,
            "forced_commit_count": translator.session_metrics.forced_commit_count
        }

    return results



def run_streaming_audio_replay_benchmark(
    asr_engine: Any,
    mt_engine: Any,
    wav_path: str,
    k: int = 2,
    unstable_buffer: int = 2,
    chunk_ms: int = 128
) -> Dict[str, Any]:
    """
    Executes live audio streaming replay through the S2 Zipformer -> S4 Adaptive Frontier -> S3 Marian pipeline.
    """
    import soundfile as sf
    import scipy.signal

    data, sr = sf.read(wav_path, dtype="float32")
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    if sr != 16000:
        num_samples = int(len(data) * 16000 / sr)
        data = scipy.signal.resample(data, num_samples)

    sample_rate = 16000
    chunk_samples = int(sample_rate * (chunk_ms / 1000.0))
    total_audio_duration_sec = len(data) / sample_rate

    config = PolicyConfig(
        agreement_k=k,
        unstable_buffer_tokens=unstable_buffer,
        enable_mt_deduplication=True
    )
    translator = IncrementalTranslator(mt_engine, config)

    asr_engine.start_stream()
    translator.start_segment(segment_id=1)

    timeline = []
    t_start = time.perf_counter()

    offset = 0
    num_samples = len(data)
    chunk_idx = 0

    while offset < num_samples:
        end_idx = min(offset + chunk_samples, num_samples)
        chunk = data[offset:end_idx]

        asr_engine.push_audio(chunk)
        partial_hyp = asr_engine.get_partial()
        asr_text = partial_hyp.text.strip()

        state = translator.update_partial(asr_text)
        timeline.append({
            "chunk_idx": chunk_idx,
            "audio_sec": round((offset + len(chunk)) / sample_rate, 2),
            "asr_text": asr_text,
            "committed_text": state.committed_text,
            "provisional_text": state.provisional_text,
            "display_text": state.display_text,
            "metrics": state.metrics
        })

        offset += chunk_samples
        chunk_idx += 1

    final_asr = asr_engine.finalize_segment()
    final_state = translator.finalize_segment(final_asr.text)
    asr_engine.stop_stream()

    total_wall_time = time.perf_counter() - t_start

    session_stability = analyze_s4_session_stability([
        SubtitleState(
            segment_id=1,
            committed_text=ev["committed_text"],
            provisional_text=ev["provisional_text"],
            display_text=ev["display_text"],
            is_final=False,
            source_text=ev["asr_text"],
            source_revision=idx + 1,
            frontier_position=0,
            mt_calls_count=0,
            metrics=ev["metrics"]
        ) for idx, ev in enumerate(timeline)
    ] + [final_state])

    return {
        "audio_file": Path(wav_path).name,
        "audio_duration_sec": round(total_audio_duration_sec, 2),
        "total_wall_time_sec": round(total_wall_time, 2),
        "real_time_factor": round(total_wall_time / total_audio_duration_sec, 4),
        "total_audio_chunks": chunk_idx,
        "final_asr_ja": final_asr.text,
        "final_subtitle_en": final_state.committed_text,
        "session_metrics": translator.session_metrics.to_dict(),
        "stability_analysis": session_stability,
        "timeline_sample_count": len(timeline)
    }

