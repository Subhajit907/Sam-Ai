"""
Sam AI Assistant - Main Entry Point
A voice-controlled AI assistant that can create projects, control your computer, and answer questions.
"""

from modules.voice import speak, listen
from modules.commands import handle_command


def main():
    """Main application loop"""
    speak("Hello, I am Sam. How can I help you?")
    while True:
        command = listen()
        if command:
            handle_command(command)


if __name__ == "__main__":
    main()
