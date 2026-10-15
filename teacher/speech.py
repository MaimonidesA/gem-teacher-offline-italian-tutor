import hashlib
import json
import os
import select
import subprocess
import sys
import tempfile
import threading
from . import config

class Speech:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()

    def _line(self, timeout):
        if not select.select([self.process.stdout], [], [], timeout)[0]:
            self.close()
            raise ValueError("La voix locale a mis trop de temps à répondre.")
        line = self.process.stdout.readline()
        if not line:
            self.close()
            raise ValueError("La voix locale n’a pas démarré. Lancez le diagnostic.")
        return json.loads(line)

    def close(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None

    def synthesize(self, text, language, rate=1.0):
        model, speaker = config.VOICES[language]
        if not model.is_file():
            raise ValueError("Voix absente. Lancez python3 scripts/bootstrap_local.py.")
        digest = hashlib.sha256(f"{language}|{rate}|{text}".encode()).hexdigest()
        output = config.DATA / "speech" / f"{digest}.wav"
        with self.lock:
            if output.exists():
                return output
            if self.process is None or self.process.poll() is not None:
                env = dict(os.environ, PYTHONPATH=str(config.RUNTIME / "piper"), OMP_NUM_THREADS="2")
                log = open(config.DATA / "piper.log", "a")
                try:
                    self.process = subprocess.Popen([sys.executable, "-u", str(config.ROOT / "teacher/piper_worker.py")],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, env=env, text=True, bufsize=1)
                finally:
                    log.close()
                self._line(20)
            self.process.stdin.write(json.dumps({"model": str(model), "speaker": speaker, "text": text,
                                                "rate": rate, "output": str(output)}) + "\n")
            self.process.stdin.flush()
            result = self._line(30)
            if not result.get("ok"):
                output.unlink(missing_ok=True)
                raise ValueError(result.get("error", "La synthèse vocale a échoué."))
            # Cache is regenerable. Bound its disk usage to 150 MB.
            files = sorted(output.parent.glob("*.wav"), key=lambda p: p.stat().st_mtime)
            total = sum(p.stat().st_size for p in files)
            for path in files:
                if total <= 150 * 1024 * 1024:
                    break
                if path != output:
                    total -= path.stat().st_size
                    path.unlink(missing_ok=True)
        return output

def transcribe(audio, language):
    binary = config.RUNTIME / "whisper/bin/whisper-cli"
    model = config.RUNTIME / "whisper/ggml-small.bin"
    if not binary.exists() or not model.exists():
        raise ValueError("Whisper n’est pas installé. Utilisez l’audio natif ou lancez le bootstrap.")
    with tempfile.TemporaryDirectory(prefix="parliamo-") as folder:
        from pathlib import Path
        wav = Path(folder) / "input.wav"
        wav.write_bytes(audio)
        env = dict(os.environ, LD_LIBRARY_PATH=str(config.RUNTIME / "whisper/lib"))
        result = subprocess.run([str(binary), "-m", str(model), "-f", str(wav), "-l", "auto", "-nt", "-np", "-t", "4"],
                                env=env, capture_output=True, text=True, timeout=90)
        if result.returncode:
            raise ValueError("Whisper n’a pas pu transcrire cet enregistrement.")
        text = result.stdout.strip()
        if not text or text in ("[BLANK_AUDIO]", "[Silence]"):
            raise ValueError("Je n’ai pas entendu de phrase. Réessayez un peu plus près du micro.")
        return text
