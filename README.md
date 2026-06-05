# Alia AI — Voice Assistant

A real-time voice AI assistant with a Jarvis-style animated GUI. Alia listens through your microphone, thinks, and speaks back — like a natural two-way conversation. Supports local (free) and cloud (paid) AI backends, wake word activation, real-time translation, live vision, multi-file document understanding, role-based personas, and a mobile app for Android & iOS.

**Download installers → [GitHub Releases](https://github.com/Subhajit907/Sam-Ai/releases/tag/v1.0.0)**

---

## Features

### 🎙️ Natural Voice Conversation
- Live two-way voice conversation — speak naturally, Alia responds instantly
- Interrupt Alia mid-sentence and she stops, listens, then responds
- Microphone auto-calibration for ambient noise on startup
- Smart pause between listen attempts to prevent rapid re-triggering

### 🔊 Wake Word — "Hey Alia"
- Toggle always-on background listening from the **🎙 WAKE** button
- Alia sits silently until she hears her name — then activates automatically
- Stays in conversation until you say *"bye"* or go silent for 2 turns
- No button presses needed — fully hands-free

### 🤖 Three AI Backends
| | Free (Ollama) | Groq | OpenAI |
|---|---|---|---|
| Chat | llama3.2 — runs locally | LLaMA 3.1 (~500 tok/s) | GPT-4o mini |
| Vision | LLaVA (local) | GPT-4o (fallback) | GPT-4o |
| TTS | edge-tts (14 voices) | OpenAI TTS (nova) | OpenAI TTS (nova) |
| STT | Google Speech API | Google Speech API | Google Speech API |
| Cost | Free | Free tier available | Pay per use |

Switch between backends anytime from the **Settings** panel — no restart required.

### 🎭 Role Switching
Switch Alia's persona from the Settings panel:

- **General** — friendly everyday assistant
- **Customer Support** — empathetic product support agent. Opens with *"I'm so sorry this happened — let me help you fix this right away."* Guides customers step by step through product issues using uploaded documents and live camera.

Switching roles resets conversation history to match the new persona.

### 👁️ Live Camera Vision
- Turn on the camera — Alia sees what you show her in real time
- Describe objects, read text, analyse scenes
- **Customer Support mode**: when camera turns on, Alia proactively identifies the product and asks what's wrong — no prompting needed
- Camera vision uses `detail: auto` for accurate model number and label reading

### 📂 Multi-File Document Upload
- Upload multiple PDFs, Word docs, images, and text files at once
- Alia reads through all of them and holds that knowledge across the conversation
- Ask questions that span multiple documents — she references each one individually
- Click × to clear all documents at once

### 🌍 Real-Time Translator
- 14 languages: English, French, Spanish, German, Italian, Japanese, Korean, Chinese, Portuguese, Arabic, Hindi, Russian, Dutch, Bengali
- Speak in one language — Alia responds in another
- Each language has its own native TTS voice (edge-tts)
- Toggle on/off anytime without restarting

### 🧠 Persistent Memory
- Conversation history saved to SQLite — Alia remembers across sessions
- Restores up to 20 past messages on startup
- Say *"reset"* or *"start over"* to clear

### 🎭 Animated Avatar
- Jarvis-style holographic face with rotating rings and glow effects
- Real-time lip sync — mouth animates in sync with Alia's voice using audio amplitude analysis
- Blink animation, state-reactive glows (idle / listening / speaking / thinking / wake word)
- Glow layers pre-cached — no per-frame GaussianBlur overhead
- Adaptive frame rate: 100ms idle / 60ms listening+thinking / 30ms speaking

### 📱 Mobile App (Android & iOS)
- React Native (Expo) app connects to Alia's Python backend over local Wi-Fi
- Chat with Alia by voice or text from your phone
- TTS audio plays through the phone speaker
- Settings screen for API keys, model selection, and role switching
- Same AI logic — no duplication

---

## Installers

| Platform | File | Notes |
|---|---|---|
| macOS | `Alia-AI-Installer.dmg` | Drag to Applications. Right-click → Open on first launch. |
| Windows | `Alia-AI-Installer-Windows.exe` | Double-click installer, follow wizard. |

Download from **[Releases](https://github.com/Subhajit907/Sam-Ai/releases/tag/v1.0.0)**.

After installing, on first launch a setup dialog asks you to choose your AI backend and enter your API key (if using OpenAI or Groq). Config is saved to:
- macOS: `~/Library/Application Support/Alia AI/.env`
- Windows: `%APPDATA%\Alia AI\.env`

---

## Running from Source

### Prerequisites
- Python 3.11+
- Microphone
- macOS: `afplay` + `afconvert` (built-in)
- Windows / Linux: [FFmpeg](https://ffmpeg.org/download.html) on PATH
- **Free mode**: [Ollama](https://ollama.com) installed and running (`ollama serve`)
- **Groq mode**: Free API key from [console.groq.com](https://console.groq.com)
- **OpenAI mode**: OpenAI API key with GPT-4o + TTS access

### Setup

```bash
git clone https://github.com/Subhajit907/Sam-Ai.git
cd Sam-Ai
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\Activate.ps1       # Windows PowerShell
pip install -r requirements.txt
```

**Linux only — system audio library:**
```bash
sudo apt install -y portaudio19-dev     # Debian/Ubuntu
sudo dnf install -y portaudio-devel     # Fedora
```

**Free mode — pull Ollama models:**
```bash
ollama pull llama3.2
ollama pull llava    # only needed for vision features
```

**Run:**
```bash
python sam.py
```

On first launch a setup dialog will ask you to choose your AI backend. Config is saved to `.env` in the project root (source mode) or the platform Application Support folder (installed mode).

---

## Mobile App

The mobile app connects to a FastAPI backend that wraps the existing Python AI modules.

### Step 1 — Start the backend (on your PC/Mac)

```bash
pip install fastapi uvicorn
python mobile/backend/server.py
```

The server starts on `http://0.0.0.0:8000`. Find your machine's local IP:
- macOS/Linux: `ifconfig | grep "inet "`
- Windows: `ipconfig`

### Step 2 — Run the mobile app

```bash
cd mobile/app
npm install
npx expo start
```

Scan the QR code with **Expo Go** (free — [iOS](https://apps.apple.com/app/expo-go/id982107779) / [Android](https://play.google.com/store/apps/details?id=host.exp.exponent)).

### Step 3 — Connect

In the app's **Settings tab**, enter your PC's IP (e.g. `http://192.168.1.5:8000`) and tap **TEST**. Both devices must be on the same Wi-Fi.

---

## UI Overview

```
┌─────────────────────────────────────────────────────────┐
│  ALIA  ARTIFICIAL INTELLIGENCE ...        ⚙ Settings ●  │
│                                                          │
│              [Animated Avatar / HUD]                     │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                    LISTENING ...                         │
│                                                          │
│  VIDEO │ AVATAR │ ⬆ UPLOAD │ ⇄ TRANSLATOR │ 🎙 WAKE    │
│                                                          │
│       [doc badge or language dropdowns when active]      │
└──────────────────────────────────────────────────────────┘
```

- Conversation text is intentionally hidden from the UI — it prints to terminal only (clean for demos)
- **⚙ Settings** opens a floating panel for model and role switching
- **🎙 WAKE** toggles always-on wake word mode (turns orange when active)

---

## Voice Commands

### Conversation
```
"Who is Nikola Tesla?"
"Explain quantum computing simply"
"Tell me a joke"
"Reset" / "Start over" / "Forget everything"
```

### Wake Word
```
"Hey Alia"          → activates from standby
"Bye" / "Goodbye"   → returns to wake word standby
"Stop listening"    → returns to wake word standby
```

### Music
```
"Play Blinding Lights"
"Play Arijit Singh"
"Play lo-fi music"
```

### Web
```
"Search for Python tutorials on Google"
"Find Coldplay on YouTube"
"Open YouTube"
"Close browser"
```

### System (Windows)
```
"Open VS Code"
"Take a screenshot"
"Lock screen" / "Sleep" / "Shutdown" / "Restart"
```

### Projects
```
"Create Python project calculator"
"Create game project snake"
"Create web project portfolio"
```

### Exit
```
"Exit" / "Quit" / "Stop" / "Terminate"
```

---

## Project Structure

```
Sam-Ai/
├── sam.py                      # Entry point — GUI + voice loop + wake word setup
├── requirements.txt            # Python dependencies
├── alia.spec                   # PyInstaller spec — macOS .app bundle
├── alia_windows.spec           # PyInstaller spec — Windows .exe bundle
├── .env                        # API keys (not committed)
│
├── modules/
│   ├── ai.py                   # Chat + vision routing (Ollama / Groq / OpenAI)
│   ├── voice.py                # TTS, STT, mic management, interruption detection, lip sync
│   ├── wakeword.py             # Background wake word listener ("Hey Alia")
│   ├── gui.py                  # Animated tkinter GUI, avatar, settings panel
│   ├── role.py                 # Role/persona management and system prompts
│   ├── translator.py           # Language pair state and TTS voice mapping
│   ├── config.py               # Mode selection and API key persistence
│   ├── memory.py               # SQLite conversation history
│   ├── paths.py                # Writable path resolution (source vs .app bundle)
│   ├── state.py                # Shared GUI reference + wake_mode flag
│   ├── commands.py             # Voice command routing
│   ├── document.py             # PDF/DOCX/image text extraction
│   ├── vision.py               # Webcam capture and product identification
│   ├── projects.py             # Project scaffolding commands
│   └── assets/                 # Avatar image assets
│
├── mobile/
│   ├── backend/
│   │   ├── server.py           # FastAPI server wrapping existing modules
│   │   └── requirements.txt    # Backend-only dependencies (fastapi, uvicorn)
│   └── app/
│       ├── App.tsx             # React Native root (bottom tab navigation)
│       ├── package.json        # Expo / React Native dependencies
│       ├── app.json            # Expo config (permissions, bundle IDs)
│       └── src/
│           ├── api/client.ts   # All API calls to the backend
│           ├── screens/
│           │   ├── ChatScreen.tsx      # Main conversation UI
│           │   └── SettingsScreen.tsx  # Server URL, model, role config
│           └── components/
│               └── VoiceButton.tsx     # Hold-to-record mic button
│
├── hooks/
│   ├── rthook_portaudio.py     # macOS: DYLD_LIBRARY_PATH for bundled portaudio
│   └── rthook_windows.py       # Windows: PATH for bundled ffplay/ffmpeg
│
├── installer/
│   └── alia_setup.iss          # Inno Setup script for Windows installer
│
└── tools/
    └── make_icon.py            # Converts avatar JPEG to Windows .ico
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `openai` | GPT-4o chat, vision, TTS, and Groq-compatible client |
| `ollama` | Local LLM and vision (free mode) |
| `edge-tts` | Free multilingual TTS (14 voices) |
| `SpeechRecognition` | Microphone input + Google STT |
| `Pillow` | Avatar rendering, glow effects, image processing |
| `opencv-python` | Webcam capture |
| `PyMuPDF` | PDF text extraction |
| `python-docx` | Word document parsing |
| `python-dotenv` | `.env` API key loading |
| `pyautogui` | Screenshots and system automation |
| `yt-dlp` | YouTube URL resolution for music |
| `fastapi` + `uvicorn` | Mobile backend API server |
| `tkinter` | Desktop GUI (Python built-in) |

---

## Troubleshooting

**No voice output**
- Free mode: confirm `ollama serve` is running
- Paid/Groq mode: verify API key is set in Settings
- macOS: test with `afplay /System/Library/Sounds/Ping.aiff`
- Windows / Linux: install FFmpeg and confirm `ffplay` is on PATH

**Microphone not detected**
- Check mic is connected and set as default input device
- Linux: install `portaudio19-dev` and reinstall `pyaudio`

**Wake word not triggering**
- Speak clearly — say "Hey Alia" or just "Alia"
- Check the 🎙 WAKE button is orange (active)
- Make sure you're not speaking while Alia is already speaking or thinking

**Vision not working (free mode)**
- LLaVA pulls automatically in the background on first use
- Wait a few minutes then try again — check terminal for pull progress

**Ollama errors**
- Make sure Ollama is running: `ollama serve`
- Pull models manually: `ollama pull llama3.2 && ollama pull llava`

**OpenAI / Groq API errors**
- OpenAI: check credits at [platform.openai.com](https://platform.openai.com)
- Groq: get a free key at [console.groq.com](https://console.groq.com)
- Confirm the key is entered correctly in Settings

**macOS "unidentified developer" on first launch**
- Right-click the app → Open → Open anyway
- Caused by missing Apple notarization (requires $99/year developer account)

**Mobile app can't connect to backend**
- Both devices must be on the same Wi-Fi network
- Use your PC's local IP (not `localhost`) in the Settings screen
- Make sure `python mobile/backend/server.py` is running and not blocked by firewall

---

## License

MIT License — open source and free to use.
