# Gem Teacher · Parliamo

A standalone, offline language tutor for Linux. Learn Italian
through short conversations with Sofia, with French as your support language
and English help when you need it. The learning path, daily goal, notebook and
reviews take inspiration from language-learning apps; the lessons are real
conversations with your local Gemma model.

Switch French/English support whenever you like, practise in guided lessons or
the coffee room, get written phrase corrections, save expressions, and keep
separate local learner profiles for the whole household.

## Install from source

The repository contains the application, artwork, launchers and tests. Model
weights, speech runtimes and personal learning records are **not included**.

Requirements:

- Linux and Python 3.10 or newer. The application server uses the standard library.
- A local Ollama service on `127.0.0.1:11434` with an installed Gemma model.
  The default model tag is `gemma4:latest`; the app never downloads it automatically.
  Direct microphone input needs a model and Ollama version that support audio.
- A recent browser. The optional desktop window uses Brave, Chrome or Chromium;
  dock installation targets GNOME. A GPU with enough memory is recommended.

```bash
git clone https://github.com/MaimonidesA/gem-teacher-offline-italian-tutor.git
cd gem-teacher-offline-italian-tutor
./start_teacher.sh
```

Open `http://127.0.0.1:8765`. Typed conversations work with the local model;
disable **Écouter les réponses de Sofia / Play Sofia’s replies** in preferences
until speech assets are installed. Use `./run_teacher.sh doctor` to check them.
No Python package installation or JavaScript build is needed for the server.

For spoken output, prepare these local files before enabling voice playback:

```text
runtime/piper/                 Piper Python package and its dependencies
runtime/voices/it.onnx         Italian Piper voice
runtime/voices/it.onnx.json    matching voice configuration
runtime/voices/fr.onnx         French Piper voice (speaker 0)
runtime/voices/fr.onnx.json    matching voice configuration
runtime/voices/en.onnx         English Piper voice
runtime/voices/en.onnx.json    matching voice configuration
```

The tested Piper runtime is 1.4.2 and must match the Python interpreter running
the app. Keep its license notices and each voice's model card with the assets.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the tested components.
Whisper is optional: only its fallback mode needs `runtime/whisper/bin/whisper-cli`,
`runtime/whisper/lib/` and `runtime/whisper/ggml-small.bin`. Native Gemma audio
does not use Whisper. Asset installation may need an internet connection once;
the prepared application runs offline.

`scripts/bootstrap_local.py` is an optional copy helper for the author's existing
local asset layout, documented below. It is not a general dependency installer.
You can supply compatible assets directly without installing GemRadio or Voice
Typing. Desktop installation is optional: run `./install_desktop.sh` after setup.

## Start

After running `./install_desktop.sh`, **Gem Teacher** appears in the applications
menu and GNOME side dock. Click its green book-and-speech icon to start the tutor
in its own window. The window uses a dedicated browser profile, separate from
your normal browser. It starts the local server automatically.

```bash
./open_teacher.sh             # open the dedicated desktop window
./install_desktop.sh          # install/reinstall the launcher and pin it
./install_desktop.sh --uninstall  # remove the shortcut; keep learning data
```

Closing the window leaves the lightweight local server available; the model
keeps its normal idle timeout. Right-click the dock icon and choose **Stop teacher
service**, or run `./stop_teacher.sh`, to stop the service.

The original browser/terminal launchers are also available:

```bash
./start_teacher.sh       # starts the local service and opens your browser
./stop_teacher.sh        # stops only Parliamo and its speech worker
```

Open **http://127.0.0.1:8765**. The application is bound to loopback; it is not
published or exposed to your network. A recent Chromium-based browser is
recommended for microphone capture. Grant microphone permission when you want
to speak. The app also works with typed replies.

Other commands:

```bash
./run_teacher.sh          # foreground server; Ctrl-C to stop
./run_teacher.sh doctor   # actual model, GPU placement and speech availability
./start_teacher.sh --no-browser
python3 scripts/launcher.py status
```

The existing system Ollama service must be running on `127.0.0.1:11434`.
No API key, online account, Python package installation, JavaScript build, CDN,
or internet connection is required to run the prepared project.

## Local learner profiles

Click the profile name at the top (or at the bottom of the sidebar), then
**Ajouter un profil / Add a profile**. Enter a name and choose French or English
support. There is no fixed profile limit, and no online account or password is
needed. Profiles separate learning records on this computer; they are not
password-protected logins.

Your original history belongs to **Mon profil**. Use **Renommer mon profil /
Rename my profile** to give it your name. New profiles start with their own empty
history, notebook and teacher memory, Italian at A1, and independent preferences.
Conversations, corrections, XP, streaks, levels, review schedules, feedback and
exports stay with their learner. Returning to a profile restores its last chat;
an unsent reply is kept while switching profiles in the same window. The browser
remembers the last selected profile when reopened. Separate open windows keep
their own active profile, and an ongoing reply always saves to its original
learner. Finish or stop a reply before switching in that window.

All profiles share the installed model and voices, so adding learners does not
duplicate model files or require more GPU memory. One model response runs at a
time, as before.

## Learning

- Italian is selected initially. Switch to French or English at the top.
  Each language has separate practice progress, notebook and working level.
- Choose one of eight topics: introductions, cafés, directions, food,
  daily life, travel, storytelling and free conversation. Every topic is open.
- French is the default support language. **Help in English** explains the
  current exchange; **Plus simple** revisits the basics; **Un petit indice**
  provides a hint. The **Langue d’appui / Support language** selector at the top
  switches the entire teaching support between French and English immediately
  for the next reply, including existing lessons, resumed chats and the coffee room.
  English mode uses English instructions, hints, feedback and new notes, with
  English conversation controls. French mode retains **Help in English** as a
  temporary aid; it does not change your saved support-language choice. You can
  also change the same preference in settings. Switching keeps your current chat,
  progress and unsent draft. Earlier messages remain in their original language.
- A completed learner reply earns 10 XP. Greetings and help requests do not.
  After at least three replies, **Valider et continuer** completes the guided
  lesson and keeps the same chat and microphone available. Sofia can also mark
  the objective complete after demonstrated progress. Completion is shown in a
  banner; it never closes the conversation. Failed or incomplete generations
  earn no XP. Practice streaks follow the computer's local date.
- Each new learner reply receives a written feedback card beneath the sentence:
  a score out of 5, meaning clarity, a corrected phrase when needed, and a short
  French explanation (or English with English as the support language). Correct
  phrases receive 5/5. Replay a correction using its speaker button. Scores are
  model estimates based on the typed phrase or audio transcript, not acoustic
  pronunciation measurements. Historical replies without ratings stay unrated.
- **Le fil avec Sofia** shows a compact summary, strengths, points to revisit and
  a next practice step. Notes carry into later lessons and update as you talk.
  Resume completed lessons directly from the home page or progress history.
- Sofia adjusts task difficulty using recent responses and carries relevant
  corrections into later lessons. A lesson can suggest a different working
  level; you choose whether to adopt it. These are practice estimates, not CEFR
  certification or an objective pronunciation test.
- **Garder** opens an editable phrase card with translations and a note.
  **Traduire cette expression avec Sofia** runs a focused local translation
  into your support language and English, independently of the lesson response.
  Notebook reviews use intervals of 1, 3, 7, 14 and 30 days for remembered
  expressions; missed expressions remain due.
- **Une touche d’humour** enables occasional gentle humor; it is on initially.
- **Ce que Sofia devrait retenir** supplies persistent teaching preferences.
  **Une remarque** saves feedback alongside a response. Export includes both
  for future lesson design with a better model.

## Coffee room

Open **Le salon café** in the sidebar or from the home page. Enter any topic in
French, English or Italian, choose a conversation starter, or simply join Sofia
and begin talking. Discuss your mathematics books, a novel, cinema, an idea or
your day. This is an open conversation at your chosen language level, without a
lesson agenda or completion target.

Sofia follows the content while the existing phrase feedback, corrections,
translations, microphone, notebook and compact memory remain available. **Changer
de sujet** starts a new thread of discussion inside the same saved chat. Subject
selection and switching are not graded and earn no XP; actual replies count as
language practice, without increasing the number of completed lessons. **Les
autres tables** returns to the coffee-room entrance, where previous chats can be
resumed. Guided lessons remain in the normal learning path.

## Voice conversation

Click the microphone, speak, then click again to send. **Voix ouverte** sends
your turn after a short pause (650 ms by default; adjustable). The mic pauses
while Sofia generates and speaks, then reopens. The stop button interrupts the
response/playback and disables open-mic mode. Use headphones for the best sound.
Switching tabs or hiding the browser pauses microphone capture.

Ordinary replies speak the target language. Lesson introductions and requested
help can speak French or English. **Écouter FR** and **Listen EN** beneath each
Italian sentence translate and play that exact sentence when clicked, with the
translation also displayed. Translations are cached locally. Automatic translation
playback is off initially and can be enabled in preferences. Replaying Sofia also
respects this setting; the small language speaker button plays a selected segment
explicitly.

```text
microphone → local 16 kHz mono WAV → Gemma native audio input
                                         ↓
                         transcript + streamed teaching sentences
                              ↓                         ↓
                    local phrase review       persistent Piper worker
                              ↓                         ↓
                    score + correction             browser playback
```

Gemma receives one bounded utterance, not repeated overlapping buffers.
Clips stop at 28 seconds, below the model's 30-second limit. Text and complete
sentences stream progressively; Piper can speak the first sentence while Gemma
finishes the response. A short, separate local Gemma review evaluates the current
phrase after the dialogue streams, so it can overlap speech playback. Audio is transported through Ollama's `images` field,
as supported by the installed runtime. The app verifies the selected model's
`audio` capability rather than assuming all models accept it.

The optional **Whisper puis Gemma** mode uses the copied multilingual Whisper
small model. This installed Whisper build runs on CPU. Running both listeners
simultaneously is intentionally not part of the default pipeline: it would
increase contention and create competing interpretations of your turn.

Gemma generates text; **Piper** supplies the Italian, French and English voices.
Piper runs on CPU, leaving GPU memory for Gemma. There is no browser/cloud speech
recognition or remote speech synthesis. This is turn-based voice conversation,
not full-duplex continuous audio streaming.

## Model and measured performance

The default is the existing local **`gemma4:latest`**, reported by Ollama as
**8.0B Q4_K_M**. No model was downloaded, replaced, or silently substituted.
The installed model digest begins `c6eb396dbd59`; the local Ollama version is
`0.30.7`. The `latest` tag is not automatically refreshed from the internet.

On this RTX 4070 Laptop GPU (8 GB), Ollama reported **100% GPU model placement**
with the tutor's 4,096-token context. Requests explicitly set `think:false`,
bound conversation history, and keep the model warm for 15 minutes. Other
applications can still contend for resources; close them yourself for the most
consistent performance. Parliamo does not stop other apps or unload their models.

Validation on 15 October 2026 with phrase feedback enabled: warm text replies
started streaming a complete teaching segment in about **1.0–1.2 seconds**;
full responses including the separate phrase review took about **5.9–6.4 seconds**
in the sampled conversation. Generation was around 56–58 tokens/s. The focused
review itself took approximately 1.4–2.3 seconds in isolated checks.

These are sample measurements, not latency guarantees. They exclude recording,
silence detection, synthesis and playback. A cold model takes longer. The UI shows
first-token and complete-turn timings, including review, for each turn. A complete
sentence takes longer than the first token because synthesis needs its text.

## Data and independence

```text
teacher/              Python standard-library server, model, speech and SQLite
web/                  HTML, CSS, JS, local SVG artwork and audio worklet
runtime/              copied Piper packages, three voices, Whisper binary/libs/model
data/learning.sqlite3  conversations, progress, phrases, reviews and preferences
data/speech/          generated voice cache, capped at approximately 150 MB
data/server.log       local service request log (no request bodies)
scripts/              launcher, one-time bootstrap and opt-in validation
tests/                persistence, streaming, audio and HTTP boundary tests
```

No runtime code imports Voice Studio or GemRadio, and no app code points into
either checkout. The system Ollama service/model store, Python and OS libraries
are normal shared runtimes. Speech packages and model files are copied, not
symlinked. This prepared runtime is for this Linux/Python installation; copying
it to a different operating system may require compatible native packages.

On a computer with the author's existing asset layout, rebuild the speech
runtime with:

```bash
python3 scripts/bootstrap_local.py
```

Only that bootstrap reads the installed assets in `~/piper-gpu`,
`~/Voice_typing/piper_voices`, and `~/whisper.cpp`. After copying, those source
projects are not needed by the tutor. `runtime/` and personal `data/` are ignored
by Git. Keep `runtime/` when making an offline copy of the prepared application.

Recordings are processed in memory; the Whisper fallback uses temporary files
that are deleted after processing. Transcripts and conversations persist in
SQLite. Teaching memory replaces a fixed-size note (at most 1,700 characters of
JSON per language and session; up to 1,000 characters supplied to the model).
Only eight recent messages enter the bounded model context. The conversation UI
loads the latest 80 messages; older exchanges stay in SQLite and in the export.
The complete lifetime transcript is never loaded into the model. Speech output
is cached locally. Browser localStorage remembers the selected profile and each
profile's last session ID; sessionStorage keeps drafts when switching profiles.
HTTP requests to Ollama bypass proxy environment variables;
cloud models and non-loopback application requests are rejected.

Use **Exporter mes données** for a portable JSON export of the current learner,
including their profile name and ID. The original profile stays in
`data/learning.sqlite3`; the profile directory is `data/profiles.sqlite3`, and
additional learners have separate databases in `data/profiles/`. For a complete
backup, stop the app and copy these files and directory together; restore them
while the app is stopped. Keep private learning data out of shared source copies.

## Validation

```bash
python3 -m unittest discover -s tests -v
node --check web/app.js
```

Real model checks deliberately use an isolated learner profile:

```bash
PARLIAMO_DATA=/tmp/parliamo-validation PARLIAMO_PORT=8766 ./start_teacher.sh --no-browser
python3 scripts/live_smoke.py --url http://127.0.0.1:8766
PARLIAMO_DATA=/tmp/parliamo-validation PARLIAMO_PORT=8766 ./stop_teacher.sh
```

Optional browser checks use an already installed Playwright/Chromium runtime;
neither is an application dependency. Set `PLAYWRIGHT_MODULE` and
`CHROMIUM_PATH`, then run `node scripts/browser_check.cjs` (clean main profile)
or `node scripts/browser_flow.cjs` (isolated test server and generated test WAV).
The continuity checks use a separate test server at port 8767:
`python3 scripts/live_continuity.py --url http://127.0.0.1:8767`, followed by
`node scripts/browser_continuity.cjs`. The microphone check accepts
`PARLIAMO_TEST_URL=http://127.0.0.1:8767 node scripts/browser_voice_check.cjs`.
For the coffee-room flow, start an isolated profile on port 8768, then run
`node scripts/browser_coffee.cjs` with the same Playwright environment variables.
Support-language checks use an isolated profile on port 8769:
`node scripts/browser_support_language.cjs` verifies both directions, English help,
existing chats, preferences, draft preservation and mobile layout.
Profile checks use an empty isolated data directory on port 8770:
`node scripts/browser_profiles.cjs` checks three learners, account switching,
separate memories/progress/preferences, exports, multiple windows and mobile layout.
Reports/screenshots are saved under ignored `artifacts/`.

## Technical references and attribution

- [Google Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
  and [native audio guidance](https://ai.google.dev/gemma/docs/capabilities/audio).
- [Ollama Gemma 4 model library](https://ollama.com/library/gemma4).
- Local Voice Studio translation flow inspired explicit language handling and
  streamed responses. GemRadio inspired the native audio adapter, small explicit
  context, `think:false`, and isolated persistent Piper worker.
- See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for component attribution.

The interface and artwork are original; Parliamo is not affiliated with
Duolingo or Talkpal.

## License

The application source and original artwork are available under the
[MIT License](LICENSE). External model weights, voices and runtime packages
retain their own licenses and are not distributed in this repository.

Related projects by the same author:
[GemRadio](https://github.com/MaimonidesA/gemradio-offline-ai-radio) and
[Voice Typing / Voice Studio](https://github.com/MaimonidesA/open-source-voice-typing-and-text-to-speech-linux-ubuntu22-gui).
