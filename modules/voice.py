"""Voice and Audio Module - Handles speech synthesis and recognition"""

import speech_recognition as sr
import pyttsx3
import sounddevice as sd
from comtypes.client import CreateObject
import time

# Initialize recognizer
recognizer = sr.Recognizer()

# Initialize speaker (SAPI5)
try:
    speaker = CreateObject("SAPI.SpVoice")
except Exception as e:
    print(f"Warning: Could not initialize SAPI speaker: {e}")
    speaker = None


def speak(text):
    """Convert text to speech using Windows SAPI5"""
    print("🤖 Sam:", text)
    try:
        if speaker:
            # Use SAPI5 directly
            speaker.Speak(text, 0)
            time.sleep(0.5)  # Give it time to speak
        else:
            # Fallback to pyttsx3
            engine = pyttsx3.init('sapi5')
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 1.0)
            engine.say(text)
            engine.runAndWait()
    except Exception as e:
        print(f"Voice error: {e}")


def listen():
    """Listen for voice commands using the microphone"""
    try:
        print("🎧 Listening...")
        duration = 10  # Increased to 10 seconds for longer sentences
        sample_rate = 16000
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        
        # Convert to audio format for recognition
        audio_bytes = audio_data.tobytes()
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
