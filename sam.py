import openai
import speech_recognition as sr
import pyttsx3
import pyautogui
import webbrowser
import os

# ===================== CONFIG =====================
DEEPSEEK_API_KEY = "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"

openai.api_key = DEEPSEEK_API_KEY
openai.api_base = "https://api.deepseek.com"

engine = pyttsx3.init()
recognizer = sr.Recognizer()

# ===================== SPEAK =====================
def speak(text):
    print("🤖 Sam:", text)
    engine.say(text)
    engine.runAndWait()

# ===================== LISTEN =====================
def listen():
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

# ===================== DEEPSEEK =====================
def ask_deepseek(prompt):
    response = openai.ChatCompletion.create(
        model="deepseek-reasoner",
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
        reply = ask_deepseek(command)
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
