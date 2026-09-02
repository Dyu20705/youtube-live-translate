import json
import shutil
import urllib.request
from pathlib import Path

DATASETS_DIR = Path(__file__).parent.parent / "datasets"
MODELS_DIR = Path(__file__).parent.parent / "models"

DATASET_MANIFEST = {
    "en_clean_speech": {
        "filename": "en_clean_speech.wav",
        "language": "en",
        "category": "clean_speech",
        "reference_text": "AFTER EARLY NIGHTFALL THE YELLOW LAMPS WOULD LIGHT UP HERE AND THERE THE SQUALID QUARTER OF THE BROTHELS",
        "description": "Standard clean English speech sample (LibriSpeech clean test set)"
    },
    "en_conversational": {
        "filename": "en_conversational.wav",
        "language": "en",
        "category": "conversational",
        "reference_text": "I THOUGHT OF PURSUING THE SUBJECT FURTHER WITH DR RUSSELL ON THE NEXT AFTERNOON",
        "description": "Conversational English speech with natural pacing and proper nouns"
    },
    "ja_conversational": {
        "filename": "ja_conversational.wav",
        "language": "ja",
        "category": "conversational",
        "reference_text": "持ち主とはぐれた傘が風で舞い看板もなぎ倒されてしまったようです",
        "description": "Natural Japanese speech (weather/news report broadcast)"
    }
}


def prepare_datasets():
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    en_model_dir = MODELS_DIR / "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17" / "test_wavs"
    if en_model_dir.exists():
        wav0 = en_model_dir / "0.wav"
        wav1 = en_model_dir / "1.wav"
        if wav0.exists():
            shutil.copy(wav0, DATASETS_DIR / "en_clean_speech.wav")
        if wav1.exists():
            shutil.copy(wav1, DATASETS_DIR / "en_conversational.wav")

    multi_model_dir = MODELS_DIR / "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10" / "test_wavs"
    if multi_model_dir.exists():
        ja_wav = multi_model_dir / "ja.wav"
        if ja_wav.exists():
            shutil.copy(ja_wav, DATASETS_DIR / "ja_conversational.wav")

    if not (DATASETS_DIR / "en_clean_speech.wav").exists():
        url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/0.wav"
        urllib.request.urlretrieve(url, DATASETS_DIR / "en_clean_speech.wav")

    if not (DATASETS_DIR / "ja_conversational.wav").exists():
        url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/ja.wav"
        try:
            urllib.request.urlretrieve(url, DATASETS_DIR / "ja_conversational.wav")
        except Exception:
            pass

    manifest_path = DATASETS_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(DATASET_MANIFEST, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    prepare_datasets()
