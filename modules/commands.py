"""Commands Module - Handles all voice commands"""

import webbrowser
import os
import subprocess
import pyautogui
import time

from modules.voice import speak
from modules.ai import ask_openai
from modules.projects import (
    create_python_project,
    create_game_project,
    create_web_project,
    open_vscode_project
)

# Track open browser instance
open_browser = None


def open_youtube():
    """Open YouTube in browser"""
    global open_browser
    webbrowser.open("https://www.youtube.com")
    open_browser = "youtube"
    speak("Opening YouTube")
    time.sleep(2)  # Wait for browser to load


def open_google():
    """Open Google in browser"""
    global open_browser
    webbrowser.open("https://www.google.com")
    open_browser = "google"
    speak("Opening Google")
    time.sleep(2)  # Wait for browser to load


def search_youtube(query):
    """Search on YouTube - opens in new tab and uses search bar"""
    global open_browser
    speak(f"Searching for {query} on YouTube")
    webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
    open_browser = "youtube"


def search_google(query):
    """Search on Google - opens in new tab and uses search bar"""
    global open_browser
    speak(f"Searching for {query} on Google")
    webbrowser.open(f"https://www.google.com/search?q={query}")
    open_browser = "google"


def close_browser():
    """Close the open browser window"""
    try:
        # Try to close Chrome
        os.system("taskkill /f /im chrome.exe 2>nul")
        # Try to close Firefox
        os.system("taskkill /f /im firefox.exe 2>nul")
        # Try to close Edge
        os.system("taskkill /f /im msedge.exe 2>nul")
        # Try to close Internet Explorer
        os.system("taskkill /f /im iexplore.exe 2>nul")
        
        speak("Closing browser")
        return True
    except Exception as e:
        speak(f"Error closing browser: {e}")
        return False


def perform_calculation(expression):
    """Perform calculation in Windows Calculator"""
    try:
        # Open calculator
        os.system("calc")
        time.sleep(1.5)  # Wait for calculator to open
        
        # Parse the expression
        calculation = expression.lower()
        
        # Replace spoken words with operators
        calculation = calculation.replace("plus", "+")
        calculation = calculation.replace("minus", "-")
        calculation = calculation.replace("multiply by", "*")
        calculation = calculation.replace("times", "*")
        calculation = calculation.replace("divide by", "/")
        calculation = calculation.replace("divided by", "/")
        calculation = calculation.replace("power", "**")
        calculation = calculation.replace("squared", "**2")
        
        # Extract numbers and operator from various formats
        # e.g., "5 multiply by 5", "5 times 3", "10 plus 20"
        import re
        
        # Try to evaluate the expression safely
        try:
            result = eval(calculation)
            speak(f"Calculating {expression}")
            
            # Type the calculation in calculator
            pyautogui.typewrite(str(result), interval=0.05)
            
            speak(f"The answer is {result}")
        except:
            speak("Could not perform that calculation")
        
    except Exception as e:
        speak(f"Error opening calculator: {e}")


def write_to_notepad(content):
    """Write content to Notepad with natural human-like typing"""
    try:
        time.sleep(1)  # Wait for notepad to be ready
        import random
        
        # Type content with natural human delays
        for char in content:
            if char == '\n':
                # For newlines, press enter
                pyautogui.press('enter')
                time.sleep(random.uniform(0.05, 0.15))  # Small delay after newline
            elif char == '\t':
                # For tabs, press tab
                pyautogui.press('tab')
                time.sleep(random.uniform(0.05, 0.15))
            else:
                # For regular characters, type with natural variation
                pyautogui.typewrite(char, interval=0.001)
                # Add random delays to simulate natural typing (faster for most chars, slower for punctuation)
                if char in '.,!?;:':
                    time.sleep(random.uniform(0.08, 0.15))  # Slower for punctuation
                else:
                    time.sleep(random.uniform(0.02, 0.08))  # Normal typing speed
        
        speak("Content written to Notepad successfully")
    except Exception as e:
        speak(f"Error writing to Notepad: {e}")


def handle_command(command):
    """Process and execute voice commands"""
    cmd = command.lower()

    if "exit" in cmd or "quit" in cmd or "terminate" in cmd or "stop" in cmd:
        speak("Goodbye!")
        exit(0)

    elif "close browser" in cmd or "close this browser" in cmd or "close youtube" in cmd or "close google" in cmd:
        close_browser()

    elif "create python project" in cmd:
        # Extract project name
        project_name = cmd.replace("create python project", "").replace("called", "").replace("named", "").strip()
        if not project_name:
            speak("Please provide a project name")
            return
        project_name = project_name.split()[0] if project_name else "my_project"
        create_python_project(project_name)
        open_vscode_project(project_name)

    elif "create game project" in cmd or "develop game" in cmd or "create game" in cmd:
        # Extract game type and project name
        parts = cmd.replace("create game project", "").replace("develop game", "").replace("create game", "").strip()
        words = parts.split()
        
        if len(words) >= 2:
            game_type = words[0]  # e.g., "flappy" or "snake"
            project_name = words[1]  # e.g., "bird" or "game"
        elif len(words) == 1:
            game_type = words[0]
            project_name = f"{game_type}_game"
        else:
            speak("Please specify a game type and project name")
            return
        
        create_game_project(project_name, game_type)
        open_vscode_project(project_name)

    elif "create web project" in cmd:
        # Extract project name
        project_name = cmd.replace("create web project", "").replace("called", "").replace("named", "").strip()
        if not project_name:
            speak("Please provide a project name")
            return
        project_name = project_name.split()[0] if project_name else "web_project"
        create_web_project(project_name)
        open_vscode_project(project_name)

    elif "open vscode" in cmd:
        subprocess.Popen(["code"])
        speak("Opening VS Code")

    elif "google" in cmd and ("search" in cmd or "find" in cmd):
        # Extract search query
        if "search for" in cmd:
            search_query = cmd.split("search for", 1)[1].strip()
        elif "find" in cmd:
            search_query = cmd.split("find", 1)[1].strip()
        else:
            search_query = cmd.replace("google", "").strip()
        
        # Remove extra words
        search_query = search_query.replace("on google", "").replace("google", "").strip()
        
        if search_query:
            search_google(search_query)
        else:
            open_google()

    elif "youtube" in cmd and ("search" in cmd or "find" in cmd):
        # Extract search query
        if "search for" in cmd:
            search_query = cmd.split("search for", 1)[1].strip()
        elif "find" in cmd:
            search_query = cmd.split("find", 1)[1].strip()
        else:
            search_query = cmd.replace("youtube", "").strip()
        
        # Remove extra words
        search_query = search_query.replace("on youtube", "").replace("youtube", "").strip()
        
        if search_query:
            search_youtube(search_query)
        else:
            open_youtube()

    elif "open google" in cmd:
        open_google()

    elif "open youtube" in cmd:
        open_youtube()

    elif "write" in cmd and "notepad" in cmd:
        # Extract what to write about - be more careful with extraction
        # Keep more of the original text and only remove essential keywords
        import re
        
        # Try to find the topic after "about" or "write"
        write_request = ""
        
        # Look for pattern: "write ... about [TOPIC]" or "write [TOPIC]"
        if "about" in cmd:
            # Extract everything after "about"
            parts = cmd.split("about", 1)
            if len(parts) > 1:
                write_request = parts[1].strip()
        
        # If no "about" found, extract after "write"
        if not write_request and "write" in cmd:
            parts = cmd.split("write", 1)
            if len(parts) > 1:
                # Remove common phrases but keep the topic
                temp = parts[1].strip()
                temp = re.sub(r'in notepad|inside notepad|an article|a poem|open nodepad|open|and', '', temp, flags=re.IGNORECASE)
                write_request = temp.strip()
        
        # Clean up any remaining extra spaces
        write_request = re.sub(r'\s+', ' ', write_request).strip()
        
        if write_request and len(write_request) > 2:  # Make sure we have a meaningful topic
            # Open notepad
            notepad_process = subprocess.Popen("notepad")
            time.sleep(3)  # Wait for notepad to fully open and be in focus
            
            speak(f"Generating article about {write_request}")
            
            # Generate content using AI with clear instruction
            content = ask_openai(f"Write a comprehensive, well-formatted article about: {write_request}. Make it engaging, detailed, and about 500 words. Include proper paragraphs and structure.")
            
            if content:
                speak("Writing to Notepad, please wait")
                time.sleep(1)
                
                # Type content naturally like a human
                write_to_notepad(content)
            else:
                speak("Could not generate content")
        else:
            os.system("notepad")
            speak("Opening Notepad")

    elif "open notepad" in cmd:
        os.system("notepad")
        speak("Opening Notepad")

    elif "open calculator" in cmd or ("calculator" in cmd and ("do" in cmd or "calculate" in cmd or "multiply" in cmd or "plus" in cmd or "minus" in cmd or "divide" in cmd)):
        # Check if there's a calculation to perform
        if any(op in cmd for op in ["multiply", "plus", "minus", "divide", "times", "power", "squared"]):
            # Extract calculation part
            calc_text = cmd.replace("open calculator", "").replace("calculate", "").replace("do", "").strip()
            if calc_text:
                perform_calculation(calc_text)
            else:
                os.system("calc")
                speak("Opening Calculator")
        else:
            os.system("calc")
            speak("Opening Calculator")

    elif "open file explorer" in cmd or "open explorer" in cmd:
        os.system("explorer")
        speak("Opening File Explorer")

    elif "open command prompt" in cmd or "open cmd" in cmd:
        os.system("cmd")
        speak("Opening Command Prompt")

    elif "screenshot" in cmd or "take screenshot" in cmd:
        pyautogui.screenshot()
        speak("Screenshot taken")

    elif "lock screen" in cmd or "lock laptop" in cmd:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        speak("Locking the screen")

    elif "sleep" in cmd or "go to sleep" in cmd:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        speak("Putting laptop to sleep")

    elif "type" in cmd:
        text = cmd.replace("type", "")
        pyautogui.write(text)
        speak("Done typing")

    elif "shutdown" in cmd:
        speak("Shutting down in 5 seconds")
        os.system("shutdown /s /t 5")

    elif "restart" in cmd:
        speak("Restarting in 5 seconds")
        os.system("shutdown /r /t 5")

    else:
        reply = ask_openai(command)
        speak(reply)
