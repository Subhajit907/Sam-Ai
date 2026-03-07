"""Voice and Audio Module - cross-platform speech synthesis and recognition"""

import sys
import subprocess
import tempfile
import os
import threading
import speech_recognition as sr
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_tts_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

from modules import state

# Recognizer — calibrated once at startup, not on every call
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 1.2       # wait 1.2s of silence before ending phrase
recognizer.phrase_threshold = 0.3
recognizer.non_speaking_duration = 0.4

_calibrated = False

def _calibrate():
    """Calibrate mic for ambient noise once at startup."""
    global _calibrated
    if _calibrated:
        return
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
        _calibrated = True
    except Exception:
        pass

# Audio captured when user interrupts Alia mid-speech
_interrupted_audio = None


def speak(text):
    """Speak text. If user talks over Alia, stop and capture their audio."""
    global _interrupted_audio
    print("Alia:", text)
    if state.gui:
        state.gui.set_state("speaking", f"Alia: {text}")

    try:
        response = _tts_client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text,
            speed=1.05,
        )
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
            f.write(response.content)

        # Start playback as a non-blocking process
        if sys.platform == "darwin":
            process = subprocess.Popen(["afplay", tmp_path])
        else:
            process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", tmp_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        # Watch mic in parallel — if user speaks, kill playback
        captured = [None]

        def watch_for_interruption():
            watcher = sr.Recognizer()
            watcher.energy_threshold = recognizer.energy_threshold * 1.5
            watcher.dynamic_energy_threshold = False
            watcher.pause_threshold = 1.2
            try:
                with sr.Microphone() as source:
                    while process.poll() is None:   # while audio still playing
                        try:
                            audio = watcher.listen(source, timeout=0.4, phrase_time_limit=20)
                            # User spoke — cut Alia off
                            process.kill()
                            captured[0] = audio
                            break
                        except sr.WaitTimeoutError:
                            continue
            except Exception:
                pass

        watcher_thread = threading.Thread(target=watch_for_interruption, daemon=True)
        watcher_thread.start()
        process.wait()
        watcher_thread.join(timeout=1.0)

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        if captured[0]:
            _interrupted_audio = captured[0]
            if state.gui:
                state.gui.set_state("thinking", "You interrupted...")
            return  # don't set idle — listen() will handle it

    except Exception as e:
        print(f"Voice error: {e}")
        if sys.platform == "darwin":
            subprocess.run(["say", text])

    if state.gui:
        state.gui.set_state("idle")


def listen():
    """Listen for voice input. Uses interrupted audio first if available."""
    global _interrupted_audio

    # If user talked over Alia, transcribe that captured audio immediately
    if _interrupted_audio:
        audio = _interrupted_audio
        _interrupted_audio = None
        try:
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            if state.gui:
                state.gui.set_state("thinking", f"You: {text}")
            return text
        except sr.UnknownValueError:
            pass  # fall through to normal listen
        except Exception:
            pass

    if state.gui:
        state.gui.set_state("listening", "Listening...")

    _calibrate()  # no-op after first call

    try:
        with sr.Microphone() as source:
            print("Listening...")
            try:
                # timeout=8: wait up to 8s for speech to start
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=25)
            except sr.WaitTimeoutError:
                if state.gui:
                    state.gui.set_state("idle")
                return ""

        try:
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            if state.gui:
                state.gui.set_state("thinking", f"You: {text}")
            return text
        except sr.UnknownValueError:
            if state.gui:
                state.gui.set_state("idle")
            return ""
        except sr.RequestError:
            print("Speech recognition service error.")
            if state.gui:
                state.gui.set_state("idle")
            return ""
    except Exception as e:
        print(f"Microphone error: {e}")
        if state.gui:
            state.gui.set_state("idle")
        return ""
