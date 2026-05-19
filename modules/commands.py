"""Commands Module - Handles all voice commands"""

import webbrowser
import os
import re
import subprocess
import pyautogui
import time
import sys

from modules.voice import speak
from modules.ai import ask_openai, ask_openai_stream, ask_openai_with_vision, reset_conversation
from modules.projects import (
    create_python_project,
    create_game_project,
    create_web_project,
    open_vscode_project
)

# Track open browser instance
open_browser = None

# Pending music request — set when Alia asks "what song?" and waits for name
_pending_music = False

# Path to yt-dlp inside the venv
_YT_DLP = os.path.join(os.path.dirname(sys.executable), "yt-dlp")


def play_youtube_music(query):
    """Find the top YouTube result for query and open it directly in browser."""
    speak(f"Playing {query} on YouTube.")
    try:
        if os.path.exists(_YT_DLP):
            result = subprocess.run(
                [_YT_DLP, f"ytsearch1:{query}", "--print", "webpage_url", "--no-download"],
                capture_output=True, text=True, timeout=15
            )
            url = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
            if url.startswith("https://"):
                webbrowser.open(url)
                return
        # Fallback: open YouTube search directly
        import urllib.parse
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
    except Exception as e:
        import urllib.parse
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        print(f"yt-dlp error: {e}")


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


# ── Lead management handlers ──────────────────────────────────────────────────

def _handle_send_all_leads():
    """Read all pending leads from Google Sheet and send personalised emails."""
    from modules import sheets, gmail_integration
    speak("Let me check the leads in your sheet.")
    try:
        leads = sheets.get_pending_leads()
    except Exception as e:
        speak(f"I couldn't connect to your Google Sheet. {e}")
        return

    if not leads:
        speak("There are no pending leads right now. Everyone has already been contacted.")
        return

    speak(f"I found {len(leads)} pending lead{'s' if len(leads) != 1 else ''}. "
          f"Should I go ahead and send personalised emails to all of them?")

    # Wait for confirmation
    from modules.voice import listen
    confirm = listen().lower()
    if not any(w in confirm for w in ("yes", "yeah", "go ahead", "sure", "do it", "send")):
        speak("Okay, I'll hold off for now.")
        return

    sent_count = 0
    failed = []
    for lead in leads:
        speak(f"Writing email for {lead['name']}…")
        try:
            subject, _ = gmail_integration.send_to_lead(lead)
            sheets.mark_email_sent(lead["row"])
            speak(f"Email sent to {lead['name']} at {lead['company'] or lead['email']}.")
            sent_count += 1
        except Exception as e:
            print(f"Failed to email {lead['name']}: {e}")
            failed.append(lead["name"])

    summary = f"Done! I sent {sent_count} email{'s' if sent_count != 1 else ''}."
    if failed:
        summary += f" I couldn't reach: {', '.join(failed)}."
    speak(summary)


def _handle_send_single_lead(name_hint: str):
    """Send email to a specific lead matched by name."""
    from modules import sheets, gmail_integration
    try:
        leads = sheets.get_pending_leads()
    except Exception as e:
        speak(f"I couldn't connect to your Google Sheet. {e}")
        return

    if not leads:
        speak("No pending leads found in your sheet.")
        return

    # Match by name (case-insensitive partial match)
    matched = [l for l in leads if name_hint and name_hint.lower() in l["name"].lower()]
    if not matched:
        speak(f"I couldn't find a pending lead named {name_hint}. "
              f"Available: {', '.join(l['name'] for l in leads[:5])}.")
        return

    lead = matched[0]
    speak(f"Sending personalised email to {lead['name']} at "
          f"{lead['company'] or lead['email']}.")
    try:
        subject, _ = gmail_integration.send_to_lead(lead)
        sheets.mark_email_sent(lead["row"])
        speak(f"Done! Email sent to {lead['name']} with subject: {subject}")
    except Exception as e:
        speak(f"Something went wrong while emailing {lead['name']}. {e}")


def _handle_check_replies():
    """Check which sent leads have replied and update the sheet."""
    from modules import sheets, gmail_integration
    speak("Checking your inbox for replies from leads. Give me a moment.")
    try:
        sent_leads = sheets.get_sent_leads()
    except Exception as e:
        speak(f"I couldn't access your sheet. {e}")
        return

    if not sent_leads:
        speak("No sent leads to check — either no emails have gone out yet, "
              "or everyone has already been marked.")
        return

    try:
        results = gmail_integration.check_all_replies(sent_leads)
    except Exception as e:
        speak(f"I had trouble checking your inbox. {e}")
        return

    replied     = []
    no_reply    = []
    lead_by_email = {l["email"]: l for l in sent_leads}

    for email, has_replied in results.items():
        lead = lead_by_email[email]
        sheets.update_reply_status(lead["row"], has_replied)
        if has_replied:
            replied.append(lead["name"])
        else:
            no_reply.append(lead["name"])

    if replied:
        speak(f"Great news! These leads replied: {', '.join(replied)}.")
    if no_reply:
        speak(f"No reply yet from: {', '.join(no_reply)}.")
    if not replied and not no_reply:
        speak("I checked but couldn't find any updates.")


def _handle_lead_summary():
    """Read out a quick summary of the lead sheet."""
    from modules import sheets
    speak("Pulling up your lead summary.")
    try:
        s = sheets.get_all_leads_summary()
    except Exception as e:
        speak(f"Couldn't read the sheet. {e}")
        return

    speak(
        f"You have {s['total']} total leads. "
        f"{s['pending']} pending, "
        f"{s['sent']} emails sent, "
        f"{s['replied']} replied, "
        f"and {s['no reply']} with no reply yet."
    )


def _handle_send_followup():
    """Send follow-up emails to leads who were emailed but haven't replied."""
    from modules import sheets, gmail_integration
    speak("Checking for leads that need a follow-up.")
    try:
        sent_leads = sheets.get_sent_leads()
    except Exception as e:
        speak(f"Couldn't access your sheet. {e}")
        return

    if not sent_leads:
        speak("No leads need a follow-up right now.")
        return

    speak(f"I found {len(sent_leads)} lead{'s' if len(sent_leads) != 1 else ''} "
          f"with no reply. Should I send them a follow-up email?")

    from modules.voice import listen
    confirm = listen().lower()
    if not any(w in confirm for w in ("yes", "yeah", "go ahead", "sure", "do it", "send")):
        speak("Okay, I'll skip for now.")
        return

    sent_count = 0
    for lead in sent_leads:
        # Reuse the same generator — GPT will produce a fresh, shorter follow-up
        lead["notes"] = (lead.get("notes", "") + " (This is a follow-up email. "
                         "Keep it shorter and more casual than the first email.)").strip()
        speak(f"Sending follow-up to {lead['name']}…")
        try:
            gmail_integration.send_to_lead(lead)
            sheets.mark_follow_up(lead["row"])
            sent_count += 1
        except Exception as e:
            print(f"Follow-up failed for {lead['name']}: {e}")

    speak(f"Sent {sent_count} follow-up email{'s' if sent_count != 1 else ''}.")


def handle_command(command):
    """Process and execute voice commands"""
    global _pending_music
    cmd = command.lower()

    _camera_words = ("camera", "video")
    if ("exit" in cmd or "quit" in cmd or "terminate" in cmd
            or ("stop" in cmd and not any(w in cmd for w in _camera_words))):
        speak("Alright, see you later!")
        from modules import vision
        vision.stop_camera()
        sys.exit(0)

    elif "reset" in cmd or "forget everything" in cmd or "start over" in cmd:
        reset_conversation()
        speak("Sure, fresh start. What's on your mind? I'm Alia, here to help!")

    elif "how much do you remember" in cmd or "memory stats" in cmd or "what have you saved" in cmd:
        from modules.memory import stats
        s = stats()
        speak(f"I've stored {s['chat_messages']} chat messages and {s['vision_interactions']} visual memories so far.")

    elif "close browser" in cmd or "close this browser" in cmd or "close youtube" in cmd or "close google" in cmd:
        close_browser()

    elif any(p in cmd for p in ("open camera", "turn on camera", "start camera", "enable camera",
                                 "open video", "turn on video", "start video")):
        from modules import state, vision
        if state.gui:
            state.gui.root.after(0, state.gui._start_video)
            from modules.role import get_role
            if get_role() == "customer_support":
                speak("Camera is on. Show me the product and I'll take a look.")
                def _auto_describe():
                    desc = vision.describe_for_support()
                    if desc:
                        speak(f"I can see — {desc} What seems to be the issue with it?")
                    else:
                        speak("I'm ready — show me the product clearly and ask away!")
                import threading
                threading.Thread(target=_auto_describe, daemon=True).start()
            else:
                speak("Camera is on. Show me something and ask!")
        else:
            speak("No GUI available to start the camera.")

    elif any(p in cmd for p in ("close camera", "turn off camera", "stop camera", "disable camera",
                                  "close video", "turn off video", "stop video")):
        from modules import state, vision
        if state.gui:
            state.gui.root.after(0, state.gui._stop_video)
            speak("Camera off.")
        else:
            vision.stop_camera()
            speak("Camera stopped.")

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

    elif "play" in cmd or ("open" in cmd and any(w in cmd for w in ["music", "song", "track"]) and "youtube" in cmd):
        global _pending_music
        # Strip filler words — keep only the actual song/artist name
        query = re.sub(
            r"\b(play|open|music|song|songs|track|for me|on youtube|in youtube|"
            r"youtube|please|a|the|some|and|me|i|i want|to|you|want|can|for|"
            r"it|that|this|something|any|just|now|up|put|start|gonna|go|in)\b",
            " ", cmd, flags=re.IGNORECASE
        )
        query = re.sub(r"\s+", " ", query).strip()
        if not query or len(query) < 2:
            _pending_music = True
            speak("Sure! What song or artist would you like me to play?")
        else:
            _pending_music = False
            play_youtube_music(query)

    elif "google" in cmd and ("search" in cmd or "find" in cmd):
        if "search for" in cmd:
            search_query = cmd.split("search for", 1)[1].strip()
        elif "find" in cmd:
            search_query = cmd.split("find", 1)[1].strip()
        else:
            search_query = cmd.replace("google", "").strip()
        search_query = search_query.replace("on google", "").replace("google", "").strip()
        if search_query:
            search_google(search_query)
        else:
            open_google()

    elif "youtube" in cmd and ("search" in cmd or "find" in cmd):
        if "search for" in cmd:
            search_query = cmd.split("search for", 1)[1].strip()
        elif "find" in cmd:
            search_query = cmd.split("find", 1)[1].strip()
        else:
            search_query = cmd.replace("youtube", "").strip()
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

    # ── Lead / Gmail / Sheets commands ───────────────────────────────────────
    elif any(p in cmd for p in ("send emails to leads", "send emails to all leads",
                                 "email all leads", "email the leads")):
        _handle_send_all_leads()

    elif any(p in cmd for p in ("send email to lead", "email lead", "send email to")):
        # "send email to Rahul" or "email lead Priya"
        name_hint = (
            cmd.replace("send email to lead", "")
               .replace("send email to", "")
               .replace("email lead", "")
               .strip()
        )
        _handle_send_single_lead(name_hint)

    elif any(p in cmd for p in ("check replies", "check for replies",
                                 "who replied", "any replies", "check lead replies")):
        _handle_check_replies()

    elif any(p in cmd for p in ("lead summary", "how many leads", "lead status",
                                 "show leads", "leads report")):
        _handle_lead_summary()

    elif any(p in cmd for p in ("send follow-up", "send followup", "follow up leads",
                                 "follow up emails", "followup emails")):
        _handle_send_followup()

    else:
        # If Alia asked "what song?" on the previous turn, treat this as the song name
        if _pending_music:
            _pending_music = False
            play_youtube_music(command)
            return

        from modules import vision
        from modules import state

        # When camera is on, always send the live frame with the question
        if vision._running:
            import cv2, base64
            frame = vision.get_frame()
            if frame is not None:
                ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
                    if state.gui:
                        state.gui.set_state("thinking")
                    reply = ask_openai_with_vision(command, b64)
                    # Split reply into sentences so Alia starts speaking immediately
                    from modules.ai import _split_sentences
                    sentences, leftover = _split_sentences(reply + " ")
                    for s in sentences:
                        speak(s)
                    if leftover.strip():
                        speak(leftover.strip())
                    return
            # Camera on but no frame yet — fall through to text
        # Streaming: speak each sentence as it arrives instead of waiting for full reply
        if state.gui:
            state.gui.set_state("thinking")
        for sentence in ask_openai_stream(command):
            speak(sentence)
