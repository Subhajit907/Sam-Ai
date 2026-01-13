from openai import OpenAI
import speech_recognition as sr
import pyttsx3
import pyautogui
import webbrowser
import os
from dotenv import load_dotenv

load_dotenv()

# ===================== CONFIG =====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable is not set!")
    print("Please add your API key to the .env file")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

engine = pyttsx3.init()
recognizer = sr.Recognizer()

# ===================== SPEAK =====================
def speak(text):
    print("🤖 Sam:", text)
    engine.say(text)
    engine.runAndWait()

# ===================== LISTEN =====================
def listen():
    try:
        with sr.Microphone() as source:
            print("🎧 Listening...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)

        try:
            text = recognizer.recognize_google(audio)
            print("🗣️ You:", text)
            return text
        except:
            return ""
    except:
        # Fallback to text input if microphone is not available
        text = input("🗣️ You (text input): ")
        return text

# ===================== OPENAI =====================
def ask_openai(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are Jarvis, a smart AI assistant that can control the computer."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# ===================== COMMANDS =====================
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

# ===================== MAIN =====================
def main():
    speak("Hello, I am Jarvis. How can I help you?")
    while True:
        command = listen()
        if command:
            handle_command(command)

if __name__ == "__main__":
    main()
