# Third-party components

The application's original source and artwork are licensed under the MIT
license in [LICENSE](LICENSE). The assets below are external dependencies; their
licenses are separate, and `runtime/` is excluded from the public source repository.

Parliamo's runtime uses these independently installed open-source components:

- **Ollama / Gemma 4:** the system's existing service and model files; not copied
  into this source checkout. Model/version details are in README.md.
- **Piper TTS 1.4.2:** copied local Python runtime. Its GPL-3.0 license and the
  other packages' notices remain under `runtime/piper/` (including
  `piper_tts-1.4.2.dist-info/licenses/COPYING`). No Piper source is imported into
  the application's Python process; it runs as a local subprocess.
- **Piper voices:** Paola (Italian), UPMC/Jessica (French, speaker 0), and
  Jenny Dioco (British English). Copied from the installed Voice Studio assets.
  Original ONNX JSON metadata is preserved beside each voice. Upstream model
  cards and dataset terms are available in the
  [Piper voices repository](https://huggingface.co/rhasspy/piper-voices/tree/main).
  These assets are local runtime files, excluded from the source repository.
- **whisper.cpp:** copied executable, shared libraries and multilingual small
  weights. Its MIT license is preserved in `runtime/whisper/LICENSE`.
- **Additional Italian voice — Serena:** created by
  [committa / it_IT-serena-high](https://huggingface.co/committa/it_IT-serena-high),
  published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Trained on the author's `serena-synthetic-it-28h` dataset, generated with
  Qwen3-TTS. The optional installer downloads unmodified ONNX
  weights and configuration from revision
  `c704759b2286f5f8c56eb4476169c4e2cda10b02`, preserving the upstream model card
  and source attribution locally. Local filenames are changed only for lookup.
  The author describes female Standard Italian with no regional accent.
  These runtime files are excluded from the source repository. The previous
  Aurora/Leonardo voice models are no longer installed or offered.
- **GemRadio:** local implementation reference for the audio input protocol,
  GPU-aware context configuration, and persistent speech worker. Relevant
  permission notice is reproduced below. The tutor uses independent local
  implementations and has no imports from GemRadio or Voice Studio.

## GemRadio permission notice

MIT License

Copyright (c) 2026 Amir Maimon

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
