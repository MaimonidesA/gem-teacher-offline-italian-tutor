#!/usr/bin/env python3
"""One-time, offline copy of already-installed runtimes; no cross-project imports."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
runtime = ROOT / "runtime"
runtime.mkdir(exist_ok=True)

def copy(source, target):
    if not source.exists():
        raise SystemExit(f"Missing local asset: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    else:
        shutil.copy2(source, target, follow_symlinks=True)

copy(HOME / "piper-gpu/site", runtime / "piper")
voices = HOME / "Voice_typing/piper_voices"
sources = {"it": "it/it_IT/paola/medium/it_IT-paola-medium.onnx",
           "fr": "fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx",
           "en": "en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium.onnx"}
for lang, name in sources.items():
    copy(voices / name, runtime / f"voices/{lang}.onnx")
    copy(voices / (name + ".json"), runtime / f"voices/{lang}.onnx.json")
whisper = HOME / "whisper.cpp"
copy(whisper / "build/bin/whisper-cli", runtime / "whisper/bin/whisper-cli")
copy(whisper / "models/ggml-small.bin", runtime / "whisper/ggml-small.bin")
for lib in (whisper / "build").rglob("*.so*"):
    if lib.is_file():
        copy(lib, runtime / "whisper/lib" / lib.name)
copy(whisper / "LICENSE", runtime / "whisper/LICENSE")
(runtime / "assets.json").write_text(json.dumps({"voices": sources, "note": "Copied locally; no app imports. Ollama models remain managed by the system Ollama service."}, indent=2))
print(f"Offline speech runtime ready in {runtime}")
