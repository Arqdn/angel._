# A N G E L

*An ancient celestial being living inside your computer.*

Angel is a fullscreen desktop AI assistant for Windows. He hears you, wakes to
his name, thinks with **Ox Alpha** (via OpenRouter), speaks in a calm male
anime-inspired voice (Fish Audio), and can act on your computer through safe,
explicit tools — open apps, take and *understand* screenshots, control volume
and media, type, click, and more. Dangerous actions always ask first.

The interface is not a chatbot. It is a dark, cinematic scene: a luminous
winged figure breathing in the dark, reacting to your voice and to his own.

---

## What Angel can do

- **"Angel, open Chrome."** — wakes on his name, launches the app, confirms aloud.
- **"Angel, what am I looking at?"** — captures the screen, sends it to Ox
  Alpha's vision, and explains what's there.
- **"Angel, turn the volume down to twenty."** / *"pause the music"* / *"what
  time is it?"* / *"copy this summary to my clipboard"*
- **"Angel, shut down the computer."** — he asks for confirmation first, by
  voice and on screen. Nothing destructive runs without your explicit *yes*.
- Conversation memory lasts the whole session; nothing you say is stored
  permanently.

All audio is processed **locally** (voice detection + [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
speech recognition). Sound only becomes an API request after you've actually
addressed Angel. Screenshots are captured only on demand.

---

## Requirements

- Windows 10/11
- Python **3.11 or 3.12** (3.10 minimum)
- A microphone and speakers/headphones
- [OpenRouter API key](https://openrouter.ai/settings/keys) — for the Ox Alpha model
- [Fish Audio API key](https://fish.audio/) — for the voice (the
  `s2.1-pro-free` model is free)
- GPU is optional. A laptop RTX 3060 (6 GB) runs speech recognition on CUDA
  comfortably (~1 GB VRAM); without CUDA it falls back to CPU automatically.

## Setup (PowerShell — copy/paste)

**1. Install Python** (skip if `python --version` already shows 3.10+):

```powershell
winget install Python.Python.3.12
```

Close and reopen PowerShell afterwards so `python` is on PATH.

**2. Get the code and enter the folder:**

```powershell
git clone https://github.com/arqdn/angel._.git angel
cd angel
```

**3. Create and activate a virtual environment:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> If activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**4. Install dependencies:**

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**5–7. Set your keys.** Copy the template and edit it:

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill in:

```
OPENROUTER_API_KEY=sk-or-v1-…      # from https://openrouter.ai/settings/keys
FISH_API_KEY=…                     # from your Fish Audio account
FISH_REFERENCE_ID=…                # optional: a MALE voice you picked on fish.audio
```

For the voice: browse [fish.audio](https://fish.audio/), pick a **male** voice
you like (calm/anime-leaning works beautifully), copy its reference ID into
`FISH_REFERENCE_ID`. Leave it empty to use the model's default male preset.
You can also change it later in Angel's settings panel (the ✦ in the corner).

**8. Run Angel:**

```powershell
python app.py
```

…or from then on just **double-click `run_angel.bat`** — it creates the venv,
installs dependencies, and launches, all on its own. `run_angel.ps1` does the
same with nicer output.

**First launch note:** faster-whisper downloads its speech model (~150 MB)
the first time Angel warms up his hearing. Give it a minute.

## Using Angel

| You do | Angel does |
|---|---|
| say **"Angel"** | chimes, brightens, listens |
| say **"Angel, open notepad"** | executes immediately (wake + request in one breath) |
| press **Space** | push-to-talk: listens right now |
| press **Ctrl+T** | type a request instead of speaking |
| press **F11** | toggle fullscreen |
| press **Esc** | close settings / deny a confirmation |
| press **Ctrl+Q** | Angel sleeps (quit) |
| click **✦** (top right) | settings: voice, microphone, wake word, sensitivity, personality, safety |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `OPENROUTER API KEY REQUIRED` on screen | Put your key in `.env` (same folder as `app.py`), restart Angel |
| `VOICE API KEY REQUIRED` | Add `FISH_API_KEY` to `.env`. Angel still works silently (text on screen) |
| `MICROPHONE UNAVAILABLE` | Check Windows Settings → Privacy → Microphone; pick the right device in Angel's settings; restart |
| Angel doesn't hear the wake word | Raise *speech sensitivity* in settings; speak the name clearly ("AYN-jel"); or use Space push-to-talk |
| Angel hears too much (TV, fans) | Lower *speech sensitivity* |
| `CONNECTION LOST` | Network/proxy issue reaching openrouter.ai — Angel retries on your next request |
| Speech recognition slow / laptop fans spin | In `config/settings.json` set `"stt": {"model_size": "tiny.en"}` or `"device": "cpu"` |
| CUDA errors from faster-whisper | Set `"stt": {"device": "cpu"}` in `config/settings.json` — CPU int8 is fast enough for short commands |
| Black window / rendering glitches | Run with software rendering: `set ANGEL_SOFTWARE_RENDER=1` then `python app.py` |
| Voice sounds female / wrong | Set a male `FISH_REFERENCE_ID` (env or settings panel) |
| Want Angel fully offline for the LLM too | Install [Ollama](https://ollama.com), `ollama pull qwen3:4b` (fits a 6 GB RTX 3060), then set `"llm": {"local_fallback": {"enabled": true}}` in `config/settings.json` — used automatically when OpenRouter is unreachable |

Logs live in `logs/angel.log` (API keys are masked). Screenshots Angel takes
are in `logs/screenshots/`.

## Tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -q
```

Manual checklist after setup: ask a question · "open notepad" · "take a
screenshot" · "what am I looking at?" · confirm the voice plays · watch the
figure react while he speaks · say "Angel, shut down the computer" and **deny** it.

## Make it a real app (optional)

Angel already launches from `run_angel.bat` (pin a shortcut to it, give the
shortcut the icon at `assets/angel/icon.ico`, or enable *start with Windows*
in the settings panel). To build a standalone `Angel.exe`:

```powershell
pip install pyinstaller
pyinstaller angel.spec
```

The app appears in `dist/Angel/Angel.exe`. Keep `.env` next to the exe.

## Architecture

```
app.py                  entry point — Qt scene + orchestrator threads
angel/
  orchestrator.py       mic → VAD → wake → STT → Ox Alpha (+tools) → TTS
  controller.py         Qt bridge (signals only; no secrets cross into QML)
  state.py              IDLE/LISTENING/THINKING/SPEAKING/CONFIRMING/ERROR
  settings.py           defaults.json ⊕ settings.json, secrets from .env only
  ai/                   OpenRouter client (tools+vision), memory, personality
  audio/                microphone, VAD, faster-whisper, Fish TTS, playback
  tools/                the ONLY doorway to your computer — typed, validated,
                        dangerous ones gated behind confirmation
ui/                     the celestial scene (QML): wings, light, particles
config/defaults.json    every tunable; user overrides go to settings.json
tests/                  77 automated tests incl. a headless UI load test
```

Angel never gets shell access. Ox Alpha can only call the registered tools,
every argument is validated, and anything that could hurt (shutdown, restart,
closing apps, emptying the recycle bin) requires your spoken or clicked
confirmation. Secrets stay in `.env`, are masked in logs, and never reach the UI.
