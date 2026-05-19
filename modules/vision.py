"""Vision Module - Webcam capture and object identification via GPT-4o"""

import cv2
import base64
import threading

_cap = None
_running = False
_latest_frame = None
_frame_lock = threading.Lock()
_reader_thread: threading.Thread | None = None


def start_camera():
    """Open webcam and start reading frames in a background thread."""
    global _cap, _running, _reader_thread
    _cap = cv2.VideoCapture(0)
    if not _cap.isOpened():
        raise RuntimeError("Could not open webcam. Make sure it is connected and not in use.")
    _running = True
    _reader_thread = threading.Thread(target=_read_frames, daemon=True)
    _reader_thread.start()


def _read_frames():
    global _latest_frame, _running
    while _running:
        try:
            if _cap is None or not _cap.isOpened():
                break
            ret, frame = _cap.read()
            if ret:
                with _frame_lock:
                    _latest_frame = frame
        except Exception:
            break


def stop_camera():
    """Stop webcam capture and release the device. Waits for reader thread to finish."""
    global _cap, _running, _latest_frame, _reader_thread
    _running = False
    if _reader_thread is not None:
        _reader_thread.join(timeout=2.0)
        _reader_thread = None
    if _cap:
        _cap.release()
        _cap = None
    with _frame_lock:
        _latest_frame = None


def get_frame():
    """Return the latest captured frame (BGR numpy array), or None."""
    with _frame_lock:
        return _latest_frame.copy() if _latest_frame is not None else None


def describe_for_support() -> str:
    """
    Called automatically when camera turns on in Customer Support mode.
    Returns a short description of the product visible in the frame so Alia
    can greet the customer with context about what she can see.
    """
    import time
    # Give the camera 1.5 s to buffer its first usable frame
    deadline = time.time() + 3.0
    frame = None
    while time.time() < deadline:
        frame = get_frame()
        if frame is not None:
            break
        time.sleep(0.2)

    if frame is None:
        return ""

    ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ret:
        return ""

    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    from modules.ai import ask_openai_with_vision
    prompt = (
        "A customer just pointed their camera at a product for support. "
        "In one short sentence, tell me: what product or item do you see? "
        "Include the brand name and product type if visible. "
        "If you can't identify the product clearly, say so briefly. "
        "Do NOT identify any person. Focus only on the object."
    )
    return ask_openai_with_vision(prompt, b64)


def identify_object(question="What object am I holding or showing? Describe it briefly and clearly."):
    """Capture the current camera frame and ask GPT-4o to identify the object."""
    frame = get_frame()
    if frame is None:
        return "I can't see anything right now — make sure the camera is on."

    ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ret:
        return "Failed to capture an image from the camera."

    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    # Build memory context from past vision interactions
    try:
        from modules.memory import get_vision_context, init_db
        init_db()
        past = get_vision_context(question, limit=5)
        memory_hint = ""
        if past:
            lines = "\n".join(f'- Q: "{p["question"]}" → A: "{p["answer"]}"' for p in past)
            memory_hint = (
                f"\n\nFor context, here are some things you've seen before for this user:\n{lines}"
                "\nUse this to give more consistent, personalised answers if relevant."
            )
    except Exception:
        memory_hint = ""

    system_msg = (
        "You are Alia, an AI assistant with live camera access. "
        "Your job is to describe objects, items, text, and scenes shown to you. "
        "Focus only on physical objects and what the user is holding or showing — "
        "do not comment on or identify any people or faces. "
        "Be concise (1-2 sentences) and speak directly to the user."
    )

    try:
        from modules.ai import client
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_msg},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question + memory_hint},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "low",
                            },
                        },
                    ],
                },
            ],
            max_tokens=200,
        )
        answer = response.choices[0].message.content or ""

        # Persist this interaction
        try:
            from modules.memory import save_vision
            save_vision(question, b64, answer)
        except Exception:
            pass

        return answer
    except Exception as e:
        print(f"Vision API error: {e}")
        return "Sorry, I had trouble analyzing the image."
