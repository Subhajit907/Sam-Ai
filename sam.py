"""
Alia AI Assistant - Main Entry Point
A voice-controlled AI assistant with a Jarvis-like GUI.
"""

import threading
from modules import state
from modules.gui import AliaGUI
from modules.voice import speak, listen, _calibrate
from modules.commands import handle_command


def voice_loop():
    """Runs in a background thread — listens and responds continuously."""
    _calibrate()   # warm up mic before first greeting
    speak("Hey, I'm Alia. What's up?")
    while True:
        command = listen()
        if command:
            handle_command(command)


if __name__ == "__main__":
    # Create and register GUI before starting voice loop
    gui = AliaGUI()
    state.gui = gui

    # Voice loop runs in background; GUI must own the main thread
    t = threading.Thread(target=voice_loop, daemon=True)
    t.start()

    gui.run()   # blocks until window is closed
