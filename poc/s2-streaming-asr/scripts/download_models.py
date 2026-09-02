import tarfile
import urllib.request
from pathlib import Path
from tqdm import tqdm

MODELS_DIR = Path(__file__).parent.parent / "models"

SHERPA_MODELS = {
    "sherpa-zipformer-en-20M": {
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2",
        "folder_name": "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17",
        "type": "zipformer",
        "lang": "en"
    },
    "sherpa-zipformer-multilingual-8lang": {
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10.tar.bz2",
        "folder_name": "sherpa-onnx-streaming-zipformer-ar_en_id_ja_ru_th_vi_zh-2025-02-10",
        "type": "zipformer",
        "lang": "multilingual"
    }
}


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_url(url: str, output_path: Path):
    with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=output_path.name) as t:
        urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)


def setup_sherpa_models():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    for model_key, info in SHERPA_MODELS.items():
        target_dir = MODELS_DIR / info["folder_name"]
        if target_dir.exists():
            continue

        tar_path = MODELS_DIR / f"{info['folder_name']}.tar.bz2"
        try:
            download_url(info["url"], tar_path)
            with tarfile.open(tar_path, "r:bz2") as tar:
                tar.extractall(path=MODELS_DIR)
            if tar_path.exists():
                tar_path.unlink()
        except Exception as e:
            print(f"Error downloading {model_key}: {e}")


def setup_whisper_models():
    from faster_whisper import WhisperModel
    whisper_dir = MODELS_DIR / "whisper"
    whisper_dir.mkdir(parents=True, exist_ok=True)
    
    for size in ["tiny", "base"]:
        try:
            WhisperModel(size, device="cpu", compute_type="int8", download_root=str(whisper_dir))
        except Exception as e:
            print(f"Error caching Whisper {size}: {e}")


def main():
    setup_sherpa_models()
    setup_whisper_models()


if __name__ == "__main__":
    main()
