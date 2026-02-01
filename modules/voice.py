"""Voice and Audio Module - cross-platform speech synthesis and recognition"""

import sys
import time
import speech_recognition as sr
import pyttsx3
import sounddevice as sd

# Initialize recognizer
recognizer = sr.Recognizer()

# Initialize speaker only on Windows (SAPI). On other platforms use pyttsx3.
speaker = None
if sys.platform == "win32":
    try:
        from comtypes.client import CreateObject
        speaker = CreateObject("SAPI.SpVoice")
    except Exception as e:
        print(f"Warning: Could not initialize SAPI speaker: {e}")
        speaker = None


def speak(text):
    """Convert text to speech (platform-aware)."""
    print("🤖 Sam:", text)
    try:
        if speaker and sys.platform == "win32":
            # Use SAPI5 on Windows when available
            speaker.Speak(text, 0)
            time.sleep(0.5)  # Give it time to speak
        else:
            # Cross-platform fallback to pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            engine.setProperty("volume", 1.0)
            engine.say(text)
            engine.runAndWait()
    except Exception as e:
        print(f"Voice error: {e}")


def listen():
    """Listen for voice commands using the microphone"""
    try:
        print("🎧 Listening...")
        duration = 10  # seconds
        sample_rate = 16000
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()

        # Convert to audio format for recognition
        audio_bytes = audio_data.tobytes()
        # sample_width=2 (bytes) for int16
        audio = sr.AudioData(audio_bytes, sample_rate, 2)

        try:
            text = recognizer.recognize_google(audio)
            print("🗣️ You:", text)
            return text
        except sr.UnknownValueError:
            print("Sorry, I didn't catch that. Please try again.")
            return ""
        except sr.RequestError:
            print("Error with the speech recognition service.")
            return ""
    except Exception as e:
        print(f"Microphone error: {e}")
        return ""
