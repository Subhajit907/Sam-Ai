"""
Alia AI Assistant - Main Entry Point
A voice-controlled AI assistant with a Jarvis-like GUI.
"""

import threading
import time
from modules import state
from modules.config import is_configured
from modules.setup_dialog import show_setup_dialog
from modules.gui import AliaGUI
from modules.voice import speak, listen, _calibrate
from modules.commands import handle_command

# Fired by the wakeword listener when "Hey Alia" is heard
_wake_triggered = threading.Event()

_DEACTIVATE_WORDS = {"bye", "goodbye", "that's all", "stop listening", "go to sleep"}


def _on_wake_detected():
    _wake_triggered.set()


def voice_loop():
    """Runs in a background thread — listens and responds continuously."""
    _calibrate()

    if not state.wake_mode:
        speak("Hey, I'm Alia. What's up?")

    while True:
        if state.wake_mode:
            # ── Wake-word mode: wait silently until "Hey Alia" is heard ──
            if state.gui:
                state.gui.set_state("wake_word", "Say 'Hey Alia'...")
            _wake_triggered.wait()
            _wake_triggered.clear()
            speak("Hey! How can I help?")

            # ── Active conversation until timeout or deactivation phrase ──
            consecutive_timeouts = 0
            while True:
                command = listen()
                if not command:
                    consecutive_timeouts += 1
                    if consecutive_timeouts >= 2:
                        speak("I'll keep listening. Just say Hey Alia when you need me.")
                        from modules import wakeword
                        wakeword.resume()
                        break
                    continue

                consecutive_timeouts = 0

                if any(w in command.lower() for w in _DEACTIVATE_WORDS):
                    speak("Got it. Say Hey Alia whenever you need me!")
                    from modules import wakeword
                    wakeword.resume()
                    break

                handle_command(command)

        else:
            # ── Normal always-on mode (original behaviour) ──
            command = listen()
            if command:
                handle_command(command)
            else:
                time.sleep(0.4)


if __name__ == "__main__":
    if not is_configured():
        show_setup_dialog()

    gui = AliaGUI()
    state.gui = gui

    # If wake mode was already enabled (restored from settings), start the listener now
    if state.wake_mode:
        from modules import wakeword
        wakeword.start(_on_wake_detected)

    t = threading.Thread(target=voice_loop, daemon=True)
    t.start()

    gui.run()
