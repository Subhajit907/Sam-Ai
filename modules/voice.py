"""Voice and Audio Module - cross-platform speech synthesis and recognition"""

import sys
import subprocess
import tempfile
import os
import threading
import time
import wave
import array
import math as _wmath
import speech_recognition as sr
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_tts_client = None  # lazy-init only when needed (paid mode)


def _get_tts_client():
    global _tts_client
    if _tts_client is None:
        _tts_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    return _tts_client

from modules import state

# Recognizer — calibrated once at startup, not on every call
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 2.0       # wait 2s of silence before ending phrase
recognizer.phrase_threshold = 0.3
recognizer.non_speaking_duration = 0.8

_calibrated = False

# Persistent microphone — opened once to avoid PortAudio segfault on macOS
# (repeated open/close of the PyAudio stream crashes Core Audio on macOS)
_mic: sr.Microphone | None = None
_mic_source = None   # the __enter__'d AudioSource


def _open_mic() -> sr.Microphone | None:
    """Open the microphone once and keep it alive for the process lifetime."""
    global _mic, _mic_source
    if _mic_source is not None:
        return _mic
    try:
        _mic = sr.Microphone()
        _mic_source = _mic.__enter__()
        return _mic
    except Exception as e:
        print(f"Microphone init error: {e}")
        _mic = None
        _mic_source = None
        return None


def _analyze_audio(mp3_path: str) -> list:
    """
    Convert MP3 → WAV then return a normalized amplitude array,
    one float (0.0–1.0) per 30 ms frame — matching the GUI's animation rate.
    """
    wav_path = mp3_path + "_lipsync.wav"
    try:
        if sys.platform == "darwin":
            subprocess.run(
                ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", mp3_path, wav_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
            )
        else:
            subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_path, "-ar", "22050", "-ac", "1", wav_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
            )

        if not os.path.exists(wav_path):
            return []

        with wave.open(wav_path, "rb") as wf:
            n_ch      = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            rate      = wf.getframerate()
            raw       = wf.readframes(wf.getnframes())

        samples = array.array("h" if sampwidth == 2 else "b", raw)
        if n_ch > 1:                        # mix to mono
            samples = samples[::n_ch]

        chunk = max(1, int(rate * 0.030))   # samples per 30 ms frame
        amps  = []
        for i in range(0, len(samples), chunk):
            sl  = samples[i : i + chunk]
            rms = _wmath.sqrt(sum(s * s for s in sl) / len(sl)) if sl else 0.0
            amps.append(rms)

        if amps:
            peak = max(amps) or 1.0
            amps = [a / peak for a in amps]

        return amps

    except Exception:
        return []
    finally:
        try:
            os.unlink(wav_path)
        except Exception:
            pass

def _calibrate():
    """Open the persistent mic and calibrate for ambient noise once at startup."""
    global _calibrated
    if _calibrated:
        return
    src = _open_mic()
    if src is None:
        return
    try:
        recognizer.adjust_for_ambient_noise(_mic_source, duration=1.0)
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
        from modules.config import get_mode
        tmp_path = tempfile.mktemp(suffix=".mp3")

        if get_mode() == "free":
            import asyncio
            import edge_tts
            from modules.translator import is_active as _trans_active, get_to_lang, get_tts_voice

            voice = get_tts_voice(get_to_lang()) if _trans_active() else "en-US-AriaNeural"

            async def _synthesize():
                comm = edge_tts.Communicate(text, voice=voice, rate="+5%")
                await comm.save(tmp_path)

            asyncio.run(_synthesize())
        else:
            response = _get_tts_client().audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text,
                speed=1.05,
            )
            with open(tmp_path, "wb") as f:
                f.write(response.content)

        # Analyze amplitude for lip sync BEFORE playback starts
        if state.gui:
            amps = _analyze_audio(tmp_path)
            state.gui.load_lip_sync(amps)

        # Start playback as a non-blocking process
        if sys.platform == "darwin":
            process = subprocess.Popen(["afplay", tmp_path])
        else:
            process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", tmp_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        # Tell GUI exactly when playback started so timing is accurate
        if state.gui:
            state.gui.start_lip_sync(time.time())

        # Watch mic in parallel — if user speaks, kill playback
        captured: list = [None]

        def watch_for_interruption():
            if _mic_source is None:
                return
            watcher = sr.Recognizer()
            watcher.energy_threshold = recognizer.energy_threshold * 1.5
            watcher.dynamic_energy_threshold = False
            watcher.pause_threshold = 2.0
            try:
                while process.poll() is None:   # while audio still playing
                    try:
                        audio = watcher.listen(_mic_source, timeout=0.4, phrase_time_limit=30)
                        # User spoke — cut Alia off and keep recording until silence
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


def _listen_continuation():
    """Listen for a brief moment to catch words spoken after Alia was cut off."""
    if _mic_source is None:
        return ""
    cont_recognizer = sr.Recognizer()
    cont_recognizer.energy_threshold = recognizer.energy_threshold
    cont_recognizer.dynamic_energy_threshold = False
    cont_recognizer.pause_threshold = 2.0
    cont_recognizer.non_speaking_duration = 0.8
    try:
        audio = cont_recognizer.listen(_mic_source, timeout=1.5, phrase_time_limit=30)
        return cont_recognizer.recognize_google(audio)  # type: ignore[attr-defined]
    except (sr.WaitTimeoutError, sr.UnknownValueError, Exception):
        return ""


def listen():
    """Listen for voice input. Uses interrupted audio first if available."""
    global _interrupted_audio

    # If user talked over Alia, transcribe that captured audio immediately
    if _interrupted_audio:
        audio = _interrupted_audio
        _interrupted_audio = None
        try:
            text = recognizer.recognize_google(audio)  # type: ignore[attr-defined]
        except (sr.UnknownValueError, Exception):
            text = ""

        # After Alia is cut off, user may still be speaking — grab the continuation
        continuation = _listen_continuation()
        if continuation:
            text = (text + " " + continuation).strip() if text else continuation

        if text:
            print(f"You: {text}")
            if state.gui:
                state.gui.set_state("thinking", f"You: {text}")
            return text
        # fall through to normal listen if nothing was captured

    if state.gui:
        state.gui.set_state("listening", "Listening...")

    _calibrate()  # no-op after first call

    if _mic_source is None:
        print("Microphone not available.")
        if state.gui:
            state.gui.set_state("idle")
        return ""

    try:
        print("Listening...")
        try:
            # timeout=8: wait up to 8s for speech to start
            audio = recognizer.listen(_mic_source, timeout=8, phrase_time_limit=25)
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
