from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("PARLIAMO_DATA", ROOT / "data")).resolve()
RUNTIME = ROOT / "runtime"
PORT = int(os.environ.get("PARLIAMO_PORT", "8765"))
HTTPS_PORT = int(os.environ.get("PARLIAMO_HTTPS_PORT", "9443"))
OLLAMA = "http://127.0.0.1:11434"
DEFAULT_MODEL = os.environ.get("PARLIAMO_MODEL", "gemma4:latest")
VOICES = {
    "it": (RUNTIME / "voices/it.onnx", None),
    "fr": (RUNTIME / "voices/fr.onnx", 0),
    "en": (RUNTIME / "voices/en.onnx", None),
}
LANGUAGES = {"it": "Italian", "fr": "French", "en": "English"}
LEVELS = ["A0", "A1", "A2", "B1", "B2"]

def prepare():
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "speech").mkdir(exist_ok=True)
