"""
Alia AI — Mobile Backend
FastAPI server that wraps the existing desktop modules and exposes
REST endpoints for the React Native mobile app.

Run:  python mobile/backend/server.py
      (from the project root so 'modules/' is on the import path)
"""

import sys
import os
import io
import asyncio
import tempfile

# Make project root importable so 'modules/' is found
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from modules.config import get_mode, save_config, is_configured, get_openai_key, get_groq_key
from modules.ai import ask_openai, ask_openai_with_vision, reset_conversation
from modules.memory import init_db, load_recent_chat
from modules.role import get_role, set_role, list_roles

init_db()

app = FastAPI(title="Alia AI Mobile API")

# Allow all origins — restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

class SpeakRequest(BaseModel):
    text: str

class VisionRequest(BaseModel):
    question: str
    image_b64: str          # base64 JPEG from phone camera

class SettingsRequest(BaseModel):
    mode: str               # "openai" | "groq" | "free"
    openai_key: str = ""
    groq_key: str = ""

class RoleRequest(BaseModel):
    role: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": get_mode(),
        "configured": is_configured(),
        "role": get_role(),
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
    reply = ask_openai(body.message)
    return ChatResponse(reply=reply)


@app.post("/api/speak")
def speak(body: SpeakRequest):
    """
    Convert text to speech and return MP3 audio bytes.
    Mobile app plays the audio using expo-av.
    """
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    mode = get_mode()

    if mode == "free":
        # edge-tts — free, high quality
        import edge_tts

        async def _synthesize() -> bytes:
            comm = edge_tts.Communicate(text, voice="en-US-AriaNeural", rate="+5%")
            buf = io.BytesIO()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
            return buf.getvalue()

        audio_bytes = asyncio.run(_synthesize())
    else:
        # OpenAI TTS (works for both openai and groq modes)
        from openai import OpenAI
        client = OpenAI(api_key=get_openai_key())
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text,
            speed=1.05,
        )
        audio_bytes = response.content

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )


@app.post("/api/vision", response_model=ChatResponse)
def vision(body: VisionRequest):
    if not body.image_b64:
        raise HTTPException(status_code=400, detail="No image provided")
    reply = ask_openai_with_vision(body.question, body.image_b64)
    return ChatResponse(reply=reply)


@app.get("/api/history")
def history():
    messages = load_recent_chat(limit=30)
    return {"messages": messages}


@app.post("/api/reset")
def reset():
    reset_conversation()
    return {"status": "ok"}


@app.get("/api/settings")
def get_settings():
    return {
        "mode": get_mode(),
        "configured": is_configured(),
        "has_openai_key": bool(get_openai_key()),
        "has_groq_key": bool(get_groq_key()),
        "role": get_role(),
        "roles": list_roles(),
    }


@app.post("/api/settings")
def update_settings(body: SettingsRequest):
    save_config(body.mode, openai_key=body.openai_key, groq_key=body.groq_key)
    return {"status": "ok", "mode": get_mode()}


@app.post("/api/role")
def update_role(body: RoleRequest):
    from modules.ai import switch_role
    switch_role(body.role)
    return {"status": "ok", "role": get_role()}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("ALIA_PORT", 8000))
    print(f"Alia AI Mobile Backend — http://0.0.0.0:{port}")
    print("Connect your phone to the same Wi-Fi and set the server IP in the app.")
    uvicorn.run(app, host="0.0.0.0", port=port)
