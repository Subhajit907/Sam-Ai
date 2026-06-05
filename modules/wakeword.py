"""Wake word detection — listens for 'Hey Alia' in the background."""

import threading
import speech_recognition as sr

_thread: threading.Thread | None = None
_stop_event   = threading.Event()
_pause_event  = threading.Event()   # set = paused (not listening)
_callback = None                    # called (no args) when wake word is heard


def _loop():
    from modules.voice import _mic_source, _mic_lock
    from modules import state

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = 300
    recognizer.pause_threshold  = 0.5

    while not _stop_event.is_set():
        # Paused while Alia is in active conversation
        if _pause_event.is_set():
            _stop_event.wait(timeout=0.3)
            continue

        # Only grab the mic when Alia isn't already using it
        if state.gui and state.gui.state not in ("idle", "wake_word"):
            _stop_event.wait(timeout=0.3)
            continue

        if _mic_source is None:
            _stop_event.wait(timeout=1.0)
            continue

        try:
            with _mic_lock:
                audio = recognizer.listen(_mic_source, timeout=1.5, phrase_time_limit=3)

            text = recognizer.recognize_google(audio).lower()
            if "alia" in text:
                pause()          # stop competing for the mic immediately
                if _callback:
                    _callback()

        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except Exception:
            continue


def start(callback):
    global _thread, _callback
    _callback = callback
    _stop_event.clear()
    _pause_event.clear()
    _thread = threading.Thread(target=_loop, daemon=True, name="wakeword-listener")
    _thread.start()


def pause():
    _pause_event.set()


def resume():
    _pause_event.clear()


def stop():
    _stop_event.set()


def is_running() -> bool:
    return _thread is not None and _thread.is_alive()
