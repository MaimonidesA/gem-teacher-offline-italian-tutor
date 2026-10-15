"""Isolated, persistent Piper runtime. JSON lines in/out; never imports another app."""
import json
import sys
import wave

def main():
    from piper import PiperVoice, SynthesisConfig
    voices = {}
    print(json.dumps({"ready": True}), flush=True)
    for line in sys.stdin:
        try:
            req = json.loads(line)
            if req.get("quit"):
                break
            model = req["model"]
            if model not in voices:
                voices[model] = PiperVoice.load(model, use_cuda=False)
            voice = voices[model]
            syn = SynthesisConfig(speaker_id=req.get("speaker"), length_scale=req.get("rate", 1.0), normalize_audio=True)
            with wave.open(req["output"], "wb") as wav:
                first = True
                for chunk in voice.synthesize(req["text"], syn_config=syn):
                    if first:
                        wav.setframerate(chunk.sample_rate)
                        wav.setsampwidth(chunk.sample_width)
                        wav.setnchannels(chunk.sample_channels)
                        first = False
                    wav.writeframes(chunk.audio_int16_bytes)
                if first:
                    raise RuntimeError("Piper n’a pas produit d’audio.")
            print(json.dumps({"ok": True}), flush=True)
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), flush=True)

if __name__ == "__main__":
    main()
