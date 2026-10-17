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
TEACHERS = {
    "sofia": {"name": "Sofia", "initial": "S", "description": "Voix italienne familière · Paola",
              "persona": "patient, reassuring and gently humorous", "voice": VOICES["it"][0]},
    "serena": {"name": "Serena", "initial": "S", "description": "Voix féminine · italien standard",
               "persona": "warm, curious and encouraging", "voice": RUNTIME / "voices/it-serena.onnx"},
}
# Preserve historical speaker labels without exposing the retired voices.
TEACHER_NAMES = {"aurora": "Aurora", "leonardo": "Leonardo", **{key: value["name"] for key, value in TEACHERS.items()}}

def teacher_catalog():
    return [{"id": key, **{k: value[k] for k in ("name", "initial", "description")},
             "available": value["voice"].is_file() and value["voice"].with_suffix(".onnx.json").is_file()}
            for key, value in TEACHERS.items()]

LANGUAGES = {"it": "Italian", "fr": "French", "en": "English"}
LEVELS = ["A0", "A1", "A2", "B1", "B2"]

def prepare():
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "speech").mkdir(exist_ok=True)
