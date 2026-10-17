#!/usr/bin/env python3
"""One-time download of two pinned Piper voices; normal app use stays offline."""
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
REVISION = "37020d3892ae230be3b8da27cec260459ecb0594"
BASE = f"https://huggingface.co/kirys79/piper_italiano/resolve/{REVISION}/"
MODELS = {
    "aurora": ("Aurora/it_IT-aurora-medium.onnx", "Aurora/it_IT-aurora-medium.onnx.json",
               "15528ee12e6c2a29bb67109e8306eb41cf3a02ff80bd835bdba2d4e8f82b38b2"),
    "leonardo": ("Leonardo/leonardo-epoch=2024-step=996300.onnx", "Leonardo/leonardo-epoch=2024-step=996300.json",
                 "e693ab78e13790d7440ecaad8f886570ca2b2918af5f8c7bf700d509f0629361"),
}

def download(name, path):
    with urllib.request.urlopen(BASE + name, timeout=60) as response, path.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)

def main():
    folder = ROOT / "runtime/voices"
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        temp = Path(temp)
        for teacher, (model, metadata, checksum) in MODELS.items():
            target = folder / f"it-{teacher}.onnx"
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == checksum and target.with_suffix(".onnx.json").is_file():
                print(f"{teacher.title()} already installed.", flush=True)
                continue
            print(f"Installing {teacher.title()} (64 MB)…", flush=True)
            download(model, temp / "voice.onnx")
            if hashlib.sha256((temp / "voice.onnx").read_bytes()).hexdigest() != checksum:
                raise ValueError(f"Checksum mismatch for {teacher}; original voice kept.")
            download(metadata, temp / "voice.json")
            info = json.loads((temp / "voice.json").read_text())
            if info.get("espeak", {}).get("voice") != "it" or info.get("num_speakers") != 1:
                raise ValueError(f"Unexpected metadata for {teacher}")
            (temp / "voice.onnx").replace(target)
            (temp / "voice.json").replace(target.with_suffix(".onnx.json"))
        download("README.md", temp / "MODEL_CARD.md")
        (temp / "MODEL_CARD.md").replace(folder / "piper-italiano-MODEL_CARD.md")
    (folder / "piper-italiano-source.json").write_text(json.dumps({
        "author": "kirys79", "repository": "https://huggingface.co/kirys79/piper_italiano",
        "revision": REVISION, "license": "CC-BY-4.0", "modified": False,
        "models": {key: {"source": model, "sha256": checksum} for key, (model, _, checksum) in MODELS.items()},
    }, indent=2))
    print("Both voices are ready for offline use. Restart Gem Teacher if it is running.")

if __name__ == "__main__":
    main()
