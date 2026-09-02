"""
quality_metrics.py - Translation quality metrics evaluation (BLEU, chrF++, COMET).
"""

from typing import List, Dict, Any, Optional
import sacrebleu

# Lazy COMET model holder
_COMET_MODEL = None
_COMET_LOAD_ATTEMPTED = False


def get_comet_model():
    global _COMET_MODEL, _COMET_LOAD_ATTEMPTED
    if not _COMET_LOAD_ATTEMPTED:
        _COMET_LOAD_ATTEMPTED = True
        try:
            from comet import download_model, load_from_checkpoint
            model_path = download_model("Unbabel/wmt22-comet-da")
            _COMET_MODEL = load_from_checkpoint(model_path)
        except Exception as e:
            print(f"[Warning] COMET model could not be loaded: {e}")
            _COMET_MODEL = None
    return _COMET_MODEL


def evaluate_translation_quality(
    sources: List[str],
    hypotheses: List[str],
    references: List[str]
) -> Dict[str, Any]:
    """
    Computes corpus-level and sentence-level BLEU, chrF++, and COMET scores.
    """
    if len(hypotheses) != len(references) or len(hypotheses) == 0:
        return {
            "bleu": 0.0,
            "chrf": 0.0,
            "chrf_plus_plus": 0.0,
            "comet": None,
            "sample_count": len(hypotheses)
        }

    # Ensure clean non-empty string lists
    hyps_clean = [h.strip() if h.strip() else "." for h in hypotheses]
    refs_clean = [r.strip() if r.strip() else "." for r in references]
    srcs_clean = [s.strip() if s.strip() else "." for s in sources]

    # 1. SacreBLEU BLEU
    bleu_res = sacrebleu.corpus_bleu(hyps_clean, [refs_clean], smooth_method="exp")
    bleu_score = round(float(bleu_res.score), 2)

    # 2. chrF and chrF++ (word_order=2)
    chrf_res = sacrebleu.corpus_chrf(hyps_clean, [refs_clean], word_order=0)
    chrf_pp_res = sacrebleu.corpus_chrf(hyps_clean, [refs_clean], word_order=2)
    
    chrf_score = round(float(chrf_res.score), 2)
    chrf_pp_score = round(float(chrf_pp_res.score), 2)

    # 3. COMET
    comet_score: Optional[float] = None
    comet_model = get_comet_model()
    if comet_model is not None:
        try:
            comet_data = [
                {"src": s, "mt": h, "ref": r}
                for s, h, r in zip(srcs_clean, hyps_clean, refs_clean)
            ]
            pred = comet_model.predict(comet_data, batch_size=4, gpus=0)
            if hasattr(pred, "system_score"):
                comet_score = round(float(pred.system_score), 4)
            elif isinstance(pred, dict) and "system_score" in pred:
                comet_score = round(float(pred["system_score"]), 4)
            elif isinstance(pred, tuple) and len(pred) >= 2:
                comet_score = round(float(pred[1]), 4)
        except Exception as e:
            print(f"[Warning] COMET prediction failed: {e}")
            comet_score = None

    return {
        "bleu": bleu_score,
        "chrf": chrf_score,
        "chrf_plus_plus": chrf_pp_score,
        "comet": comet_score,
        "sample_count": len(hypotheses),
        "details": {
            "bleu_signature": str(bleu_res),
            "chrf_signature": str(chrf_res)
        }
    }


def compute_sentence_metrics(
    source: str,
    hypothesis: str,
    reference: str
) -> Dict[str, float]:
    """Computes sentence-level BLEU and chrF++."""
    hyp_clean = hypothesis.strip() if hypothesis.strip() else "."
    ref_clean = reference.strip() if reference.strip() else "."

    s_bleu = sacrebleu.sentence_bleu(hyp_clean, [ref_clean], smooth_method="exp")
    s_chrf = sacrebleu.sentence_chrf(hyp_clean, [ref_clean], word_order=2)

    return {
        "sentence_bleu": round(float(s_bleu.score), 2),
        "sentence_chrf_pp": round(float(s_chrf.score), 2)
    }
