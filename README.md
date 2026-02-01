# Sam AI Assistant 🤖

A powerful voice-controlled AI assistant that can create projects, control your computer, search the web, and answer questions using OpenAI's GPT models.

## Features ✨

### Voice Control
- **Speech Recognition** - Understand voice commands
- **Text-to-Speech** - Respond with natural voice output using Windows SAPI5
- **Real-time Processing** - Instant command execution

### Project Development
- **Python Projects** - Auto-generate project structure with src/, tests/, data/ folders
- **Game Development** - AI-powered game creation using Pygame
- **Web Projects** - Create HTML/CSS/JS projects with proper structure
- **Auto-open in VS Code** - Projects open automatically in your editor

### System Control
- **Application Management** - Open Notepad, Calculator, File Explorer, VS Code
- **Web Browsing** - Open Google, YouTube with custom searches
- **System Operations** - Lock screen, sleep mode, shutdown, restart
- **Screenshots** - Capture screen automatically
- **Text Input** - Type content programmatically

### AI Capabilities
- **Question Answering** - Ask anything and get intelligent responses
- **Code Generation** - Generate complete game code automatically
- **Natural Conversation** - Chat with an intelligent assistant

## Installation 🚀

### Prerequisites
- Python 3.8+
- Windows OS (for SAPI5 speech synthesis)
- Microphone for voice input
- VS Code (optional, for project development)

### Setup
1. Clone or download this repository:
```bash
cd Sam-Ai
```

2. Create a virtual environment (use `python3` if `python` points to Python 2 on your system):
```bash
python -m venv .venv
```

3. Activate the virtual environment (choose the command for your OS/shell):
- macOS / Linux (bash, zsh):
```bash
source .venv/bin/activate
```
- Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```
- Windows CMD:
```cmd
.venv\Scripts\activate.bat
```

4. Install system dependencies (required for audio libraries) — platform-specific:
- macOS (Homebrew):
```bash
brew install portaudio
```
- Debian/Ubuntu:
```bash
sudo apt update
sudo apt install -y portaudio19-dev libsndfile1 libsndfile1-dev build-essential
```
- Fedora:
```bash
sudo dnf install -y portaudio-devel libsndfile
```
Note: These packages are required for `sounddevice`, `soundfile` or `pyaudio` to build/install correctly.

5. Install Python dependencies:
```bash
pip install -r requirements.txt
```

6. Set up your OpenAI API key:
   - Create a `.env` file in the project root
   - Add your API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
   - Get your key from [OpenAI Platform](https://platform.openai.com)

7. Run Sam:
```bash
python sam.py
```

## Usage 📋

Once running, Sam is always listening. Here are example commands:

### Project Creation
```
"Create python project calculator"
"Create game project snake game"
"Create web project portfolio"
```

### Web Browsing
```
"Search for Python on Google"
"Find Arijit Singh on YouTube"
```

### System Control
```
"Open VS Code"
"Open Notepad"
"Take a screenshot"
"Lock screen"
"Sleep"
"Shutdown"
```

### General Queries
```
"Who is Alia Bhatt?"
"What is machine learning?"
"Tell me a joke"
```

### Exit
```
"Exit" / "Quit" / "Terminate" / "Stop"
```

## Project Structure 📁

```
Sam-Ai/
├── sam.py                    # Main entry point
├── requirements.txt          # Project dependencies
├── README.md                 # This file
├── .env                      # API keys (not included in repo)
├── sam_old.py               # Backup of original code
└── modules/
    ├── __init__.py
    ├── voice.py             # Speech recognition & synthesis
    ├── ai.py                # OpenAI API interactions
    ├── projects.py          # Project creation functions
    └── commands.py          # Command processing & handling
```

## Module Documentation 📚

### voice.py
- `speak(text)` - Convert text to speech
- `listen()` - Listen for voice commands

### ai.py
- `ask_openai(prompt)` - Send prompt to OpenAI
- `generate_game_code(project_name, game_type)` - Generate game code

### projects.py
- `create_python_project(project_name)` - Create Python project
- `create_game_project(project_name, game_type)` - Create game project
- `create_web_project(project_name)` - Create web project
- `open_vscode_project(project_path)` - Open project in VS Code

### commands.py
- `handle_command(command)` - Process voice commands

## System Requirements 💻

- **OS**: Windows (SAPI5 for speech synthesis)
- **Python**: 3.8 or higher
- **RAM**: 2GB minimum
- **Microphone**: Required for voice input
- **Internet**: Required for OpenAI API and web searches

## Dependencies 📦

- `openai` - OpenAI API client
- `speech-recognition` - Speech recognition
- `pyttsx3` - Text-to-speech fallback
- `sounddevice` - Audio input
- `soundfile` - Audio file handling
- `pyautogui` - Keyboard/mouse automation
- `python-dotenv` - Environment variable management

## Troubleshooting 🔧

### No Voice Output
- Ensure Windows speakers are enabled
- Check volume level
- Verify SAPI5 installation

### Microphone Not Detected
- Check microphone connection
- Run: `python -m speech_recognition`
- Ensure microphone is set as default input

### OpenAI API Errors
- Verify API key in `.env` file
- Check internet connection
- Ensure account has API credits

### VS Code Not Opening
- Install VS Code: https://code.visualstudio.com
- Add VS Code to PATH
- Run: `code .` from terminal to verify installation

## Contributing 🤝

Feel free to fork, modify, and improve Sam! Some ideas:
- Add email integration
- Support for more project types
- Database management
- File operations
- Custom voice profiles

## License 📄

This project is open source and available under the MIT License.

## Author 👨‍💻

Created with ❤️ for automation and AI enthusiasts.

---

**Last Updated**: January 2026