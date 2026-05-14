# Alia AI — Voice Assistant

A real-time voice AI assistant with a Jarvis-style animated GUI. Alia listens through your microphone, thinks, and speaks back — like a natural two-way conversation. Supports local (free) and cloud (paid) AI backends, real-time translation, live vision, multi-file document understanding, and role-based personas.

---

## Features

### 🎙️ Natural Voice Conversation
- Live two-way voice conversation — speak naturally, Alia responds instantly
- Interrupt Alia mid-sentence and she stops, listens, then responds
- Microphone auto-calibration for ambient noise on startup
- 0.4s smart pause between listen attempts to prevent rapid re-triggering

### 🤖 Dual AI Backend
| | Free Mode | Paid Mode |
|---|---|---|
| Chat | Ollama (llama3.2) — runs locally | OpenAI GPT-4o |
| Vision | Ollama (LLaVA) | OpenAI GPT-4o Vision |
| TTS | edge-tts (14 language voices) | OpenAI TTS (nova) |
| STT | Google Speech API | Google Speech API |

Switch between modes anytime from the **Settings** panel — no restart required.

### 🎭 Role Switching
Switch Alia's persona from the Settings panel:

- **General** — friendly everyday assistant
- **Customer Support** — empathetic product support agent. Opens with *"I'm so sorry this happened — let me help you fix this right away."* Guides customers step by step through product issues using uploaded documents and live video.

Switching roles resets conversation history to match the new persona.

### 👁️ Live Vision Mode (Webcam)
- Turn on the camera — Alia sees what you show her in real time
- Describe objects, read text, analyse scenes
- In Customer Support role: identifies product damage and guides repairs live

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
- Blink animation, state-reactive glows (idle / listening / speaking / thinking)
- Glow layers pre-cached — no per-frame GaussianBlur overhead
- Adaptive frame rate: 100ms idle / 60ms listening+thinking / 30ms speaking

### ⚙️ Settings Panel
- Hidden from the main UI — click **⚙ Settings** in the top bar
- Switch AI model (Free/Paid) without exposing it during demos
- Switch role (General / Customer Support)

### 🎵 Music & Web
- *"Play [song/artist]"* — opens YouTube in browser
- *"Search Google/YouTube for..."*
- *"Open YouTube / Google"*

### 🗂️ Project Scaffolding
- *"Create Python project [name]"* — generates `src/`, `tests/`, `data/` structure
- *"Create game project [name]"* — AI-generated pygame starter code
- *"Create web project [name]"* — HTML/CSS/JS scaffold

---

## Installation

### Prerequisites
- Python 3.11+
- Microphone
- macOS: `afplay` (built-in), `afconvert` (built-in)
- Linux/Windows: [FFmpeg](https://ffmpeg.org/download.html) on PATH
- **Free mode**: [Ollama](https://ollama.com) installed and running (`ollama serve`)
- **Paid mode**: OpenAI API key with GPT-4o + TTS access

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Subhajit907/Sam-Ai.git
cd Sam-Ai
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\Activate.ps1     # Windows PowerShell
```

3. Install system dependencies (Linux only):
```bash
sudo apt install -y portaudio19-dev     # Debian/Ubuntu
sudo dnf install -y portaudio-devel     # Fedora
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

5. (Optional) Create a `.env` file for Paid mode:
```
OPENAI_API_KEY=your_api_key_here
```

6. (Free mode only) Pull the required Ollama models:
```bash
ollama pull llama3.2
ollama pull llava          # only needed for vision features
```

7. Run Alia:
```bash
python sam.py
```

On first launch a setup dialog will ask you to choose Free or Paid mode.

---

## UI Overview

```
┌─────────────────────────────────────┐
│ ALIA  ARTIFICIAL INTELLIGENCE ...  ⚙ Settings ●  │
│                                     │
│         [Animated Avatar / HUD]     │
│                                     │
├─────────────────────────────────────┤
│           LISTENING ...             │
│                                     │
│  VIDEO  │ AVATAR │ ⬆ UPLOAD │ ⇄ TRANSLATOR  │
│                                     │
│  [doc badge or language dropdowns]  │
└─────────────────────────────────────┘
```

- Conversation text is intentionally hidden from the UI — it prints to terminal only (clean for demos)
- ⚙ Settings opens a floating panel with model and role switching

---

## Voice Commands

### Conversation
```
"Who is Nikola Tesla?"
"Explain quantum computing simply"
"Tell me a joke"
"Reset" / "Start over" / "Forget everything"
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
├── sam.py                  # Entry point — starts GUI + voice loop thread
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not committed)
└── modules/
    ├── ai.py               # Chat + vision routing (Ollama / OpenAI), doc context
    ├── voice.py            # TTS, STT, mic management, interruption detection, lip sync
    ├── gui.py              # Animated tkinter GUI, avatar, settings panel
    ├── role.py             # Role/persona management and system prompts
    ├── translator.py       # Language pair state and TTS voice mapping
    ├── config.py           # Mode selection and API key persistence
    ├── memory.py           # SQLite conversation memory
    ├── state.py            # Shared GUI reference across threads
    ├── commands.py         # Voice command routing
    ├── document.py         # PDF/DOCX/image text extraction and base64 encoding
    ├── projects.py         # Project scaffolding
    └── assets/             # Avatar image assets
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `openai` | GPT-4o chat, vision, TTS |
| `ollama` | Local LLM and vision (free mode) |
| `edge-tts` | Free multilingual TTS |
| `SpeechRecognition` | Microphone input + Google STT |
| `Pillow` | Avatar rendering, glow effects, image processing |
| `opencv-python` | Webcam capture |
| `PyMuPDF` | PDF text extraction |
| `python-docx` | Word document parsing |
| `python-dotenv` | `.env` API key loading |
| `pyautogui` | Screenshots and system automation |
| `yt-dlp` | YouTube URL resolution for music |
| `tkinter` | GUI (Python built-in) |

---

## Troubleshooting

**No voice output**
- Free mode: confirm `ollama serve` is running
- Paid mode: verify `OPENAI_API_KEY` in `.env` has TTS access
- macOS: test with `afplay /System/Library/Sounds/Ping.aiff`
- Linux/Windows: install FFmpeg and confirm `ffplay` is on PATH

**Microphone not detected**
- Check mic is connected and set as default input device
- Linux: install `portaudio19-dev` and reinstall `pyaudio`

**Vision not working (free mode)**
- LLaVA pulls automatically in the background on first use
- Wait a few minutes then try again — check terminal for pull progress

**Ollama errors**
- Make sure Ollama is running: `ollama serve`
- Pull models manually: `ollama pull llama3.2 && ollama pull llava`

**OpenAI API errors**
- Check credits at [platform.openai.com](https://platform.openai.com)
- Confirm key is correct in `.env`

---

## License

MIT License — open source and free to use.
