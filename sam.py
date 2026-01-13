from openai import OpenAI
import speech_recognition as sr
import pyttsx3
import pyautogui
import webbrowser
import os
from dotenv import load_dotenv
import sounddevice as sd
import soundfile as sf
import numpy as np
from comtypes.client import CreateObject
import time

load_dotenv()

# ===================== CONFIG =====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable is not set!")
    print("Please add your API key to the .env file")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# Use Windows SAPI5 directly via comtypes
try:
    speaker = CreateObject("SAPI.SpVoice")
except Exception as e:
    print(f"Warning: Could not initialize SAPI speaker: {e}")
    speaker = None

recognizer = sr.Recognizer()

# ===================== SPEAK =====================
def speak(text):
    print("Sam:", text)
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

# LISTEN
def listen():
    try:
       
        print("Listening...")
        duration = 5 
        sample_rate = 16000
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        
        
        from io import BytesIO
        audio_bytes = audio_data.tobytes()
        audio = sr.AudioData(audio_bytes, sample_rate, 2)
        
        try:
            text = recognizer.recognize_google(audio)
            print("You:", text)
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

# OPENAI
def ask_openai(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are Sam, a smart AI assistant that can control the computer."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# COMMANDS 
def handle_command(command):
    cmd = command.lower()

    if "open google" in cmd:
        webbrowser.open("https://google.com")
        speak("Opening Google")

    elif "open youtube" in cmd:
        webbrowser.open("https://youtube.com")
        speak("Opening YouTube")

    elif "open notepad" in cmd:
        os.system("notepad")
        speak("Opening Notepad")

    elif "type" in cmd:
        text = cmd.replace("type", "")
        pyautogui.write(text)
        speak("Done typing")

    elif "shutdown" in cmd:
        speak("Shutting down in 5 seconds")
        os.system("shutdown /s /t 5")

    else:
        reply = ask_openai(command)
        speak(reply)

def main():
    speak("Hello, I am Sam. How can I help you?")
    while True:
        command = listen()
        if command:
            handle_command(command)

if __name__ == "__main__":
    main()
