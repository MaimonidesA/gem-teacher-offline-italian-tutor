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

Open **http://127.0.0.1:8765**. By default, the application is bound to loopback.
Optional Wi-Fi sharing is described below. A recent Chromium-based browser is
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

## Use your phone on the same Wi-Fi

On the computer, enable the saved LAN setting:

```bash
./stop_teacher.sh
./start_teacher.sh --lan --no-browser
```

Open **Preferences → On my phone** on the computer and enter the displayed
setup address in your phone's browser. It looks like
`http://COMPUTER_WIFI_IP:8765/phone.html`. The setup page explains how to download
and trust this computer's **Gem Teacher Local CA** certificate on iPhone/iPad or
Android. This is a one-time step on each phone. Then open and bookmark the secure
address shown there, `https://COMPUTER_WIFI_IP:9443`, choose your profile, and allow
the microphone. Typing, recordings, hands-free conversation and local speech use
the same backend as the desktop. If the browser blocks playback, **Tap to listen**
resumes the prepared audio.

The HTTP desktop address remains available. Phone microphone capture needs a
trusted HTTPS origin; simply bypassing a certificate warning is not the setup.
See [MDN's microphone requirements](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia),
[Apple's certificate trust instructions](https://support.apple.com/102390) and
[Google's certificate installation instructions](https://support.google.com/pixelphone/answer/2844832).

Wi-Fi sharing uses Linux `ip` and `openssl`, creates its certificates locally,
and contacts no certificate service. The private CA and keys stay under ignored
`data/tls/` with restricted file permissions. Keep that folder in private backups
to preserve existing phone trust. If the computer's Wi-Fi IP changes, restart the
teacher; its server certificate renews for the new address while retaining the
same CA. The setup address and secure address in Preferences update at startup.

Only the local Wi-Fi/Ethernet subnets are accepted; VPN and virtual-network
interfaces are excluded. Host and Origin checks still apply. Profiles are shared
with devices on that network, without account passwords. No router port forwarding
is needed. Keep the computer awake and both devices on the same non-guest Wi-Fi.
If a host firewall is enabled, allow TCP 8765 and 9443 from your Wi-Fi subnet.

Both listeners run in one process, sharing one speech worker and the same Ollama
model. No second model or extra GPU allocation is created. Model calls are
serialized, so a second device waits or receives a busy message while the first
is generating; it does not compete with another teacher generation. Wi-Fi adds
transport latency, which depends on the network. A microphone selection saved on
the desktop falls back to the phone's default microphone if that device is absent.

To return to computer-only access, stop the service and run
`./start_teacher.sh --localhost`. `--lan`/`--localhost` are remembered in
`data/network.json`; `PARLIAMO_LAN=1` and `PARLIAMO_HTTPS_PORT` provide process-level
overrides for isolated testing. Neither mode exposes the Ollama service itself.

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
  **Explanation EN / Explication EN** reads the feedback explanation in English.
  French explanations are translated locally on demand and cached with that
  learner's message; English explanations play directly. The score and progress
  do not change when listening, and the original written feedback stays intact.
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

**Slow IT / IT lent** repeats the original Italian sentence with slower local
speech synthesis. It is also available beside corrected Italian phrases. This
does not change the voice-speed preference, score or conversation. The ordinary
Italian replay and French/English translation buttons remain available.

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
cloud models are rejected. Application requests are limited to loopback or the
explicitly enabled LAN interfaces, with matching Host and Origin checks.

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
Phone validation uses isolated HTTP port 8771 and HTTPS port 9444 with
`PARLIAMO_DATA=/tmp/parliamo-phone-validation PARLIAMO_PORT=8771 PARLIAMO_HTTPS_PORT=9444 ./start_teacher.sh --lan --no-browser`.
`scripts/browser_phone.cjs` exercises slower Italian replay, English explanation
audio, blocked-playback recovery, layouts from 320 to 1440 pixels, and a synthetic
HTTPS microphone conversation. It expects a synthetic input WAV at
`/tmp/parliamo-phone-microphone.wav`. Browser certificate errors are ignored only
in this isolated browser test; certificate-chain and IP validation are checked
separately using the generated CA with a verifying TLS client. Real phones must
complete the trust steps themselves.
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
