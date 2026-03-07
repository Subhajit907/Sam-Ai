# Alia AI Assistant

A voice-controlled AI assistant with a Jarvis-like animated GUI. Alia listens to your voice, speaks back using OpenAI's TTS (nova voice), remembers your conversation, and can control your computer, browse the web, play music, and create projects.

## Features

### Animated GUI
- Jarvis-style dark UI with rotating rings and state-reactive animations
- Visual states: Standby, Listening, Speaking, Processing
- Real-time display of what Alia says and hears

### Voice Interaction
- **Speech recognition** via Google Speech Recognition
- **Natural TTS** using OpenAI's `tts-1` model (nova voice)
- **Interruption detection** — speak over Alia mid-sentence and she stops and listens
- **Mic auto-calibration** for ambient noise on startup

### Conversation Memory
- Maintains full conversation history for natural back-and-forth
- Powered by `gpt-4o-mini` with a warm, conversational system prompt
- Say "reset" or "start over" to clear history and start fresh

### Music Playback
- "Play [song/artist]" — finds the top YouTube result via `yt-dlp` and opens it in the browser

### Web Browsing
- Open Google or YouTube
- Search Google or YouTube by voice
- Close browser

### System Control (Windows)
- Open Notepad, Calculator, File Explorer, Command Prompt, VS Code
- Lock screen, sleep, shutdown, restart
- Take a screenshot
- Type text programmatically

### Project Scaffolding
- Create Python projects with `src/`, `tests/`, `data/` structure
- Create Pygame game projects with AI-generated starter code
- Create HTML/CSS/JS web projects
- Auto-open generated projects in VS Code

### AI Q&A
- Ask anything — answers use full conversation context

---

## Installation

### Prerequisites
- Python 3.8+
- Microphone
- OpenAI API key (with credits for Chat + TTS)
- `yt-dlp` installed in your virtual environment
- macOS: `afplay` (built-in) — no extra setup needed
- Linux/Windows: `ffplay` from [FFmpeg](https://ffmpeg.org/download.html) must be on PATH

### Setup

1. Clone the repository and enter the directory:
```bash
git clone https://github.com/Subhajit907/Sam-Ai.git
cd Sam-Ai
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

3. Install system dependencies for audio (Linux only):
```bash
# Debian / Ubuntu
sudo apt install -y portaudio19-dev
# Fedora
sudo dnf install -y portaudio-devel
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
pip install yt-dlp
```

5. Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_api_key_here
```
Get your key from [platform.openai.com](https://platform.openai.com).

6. Run Alia:
```bash
python sam.py
```

---

## Voice Commands

### Music
```
"Play Blinding Lights"
"Play Arijit Singh"
"Play lo-fi music"
```

### Web Browsing
```
"Search for Python tutorials on Google"
"Find Coldplay on YouTube"
"Open YouTube"
"Close browser"
```

### System (Windows)
```
"Open VS Code"
"Open Notepad"
"Take a screenshot"
"Lock screen"
"Sleep"
"Shutdown"
"Restart"
```

### Project Creation
```
"Create python project calculator"
"Create game project snake game"
"Create web project portfolio"
```

### Conversation
```
"Who is Nikola Tesla?"
"Explain machine learning in simple terms"
"Tell me a joke"
"Reset" / "Start over" / "Forget everything"
```

### Exit
```
"Exit" / "Quit" / "Stop" / "Terminate"
```

---

## Project Structure

```
Sam-Ai/
├── sam.py              # Entry point — starts GUI + voice loop thread
├── requirements.txt    # Python dependencies
├── .env                # API keys (not committed)
└── modules/
    ├── ai.py           # OpenAI chat (gpt-4o-mini) with conversation history
    ├── voice.py        # OpenAI TTS, speech recognition, interruption detection
    ├── gui.py          # Jarvis-like animated tkinter GUI
    ├── state.py        # Shared state (GUI reference)
    ├── commands.py     # Voice command routing and execution
    └── projects.py     # Python / game / web project scaffolding
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `openai` | GPT-4o-mini chat + TTS-1 speech synthesis |
| `SpeechRecognition` | Microphone input and Google STT |
| `pyautogui` | Keyboard/mouse automation, screenshots |
| `python-dotenv` | Load `.env` API keys |
| `yt-dlp` | Resolve YouTube URLs for music playback |
| `tkinter` | GUI (Python built-in) |

---

## Troubleshooting

**No voice output**
- Verify your OpenAI API key has TTS access and available credits
- macOS: ensure `afplay` works — run `afplay /System/Library/Sounds/Ping.aiff` in terminal
- Linux/Windows: install FFmpeg and confirm `ffplay` is on PATH

**Microphone not detected**
- Check your mic is connected and set as default input
- Run `python -m speech_recognition` to test

**yt-dlp not found**
- Install it inside your venv: `pip install yt-dlp`

**OpenAI API errors**
- Confirm `.env` has the correct `OPENAI_API_KEY`
- Check your account has API credits at [platform.openai.com](https://platform.openai.com)

---

## License

MIT License — open source and free to use.
