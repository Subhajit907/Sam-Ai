"""AI Module — routes chat/vision to Ollama (free) or OpenAI (paid) based on config."""

import os
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are Alia, a friendly and natural AI assistant. Talk like a real person — conversational, warm, and concise.

Rules:
- Keep responses short and natural unless the user asks for detail
- Don't use bullet points or headers in spoken replies — just talk
- Show personality: be friendly, occasionally light-hearted
- Remember what was said earlier in the conversation
- If you don't know something, say so naturally
- Never sound robotic or formal"""

SYSTEM_PROMPT_VISION = """You are Alia, a friendly AI assistant. You have a live camera feed from the user's webcam attached to every message.

Your job:
- Look at the image and answer the user's question based on what you actually see
- Describe objects, items, text, colours, or scenes visible in the frame — be specific
- If the user holds something up or shows you something, describe it clearly and helpfully
- Do NOT say you cannot see — you CAN see the camera feed
- Do NOT identify or name any person by face — only describe objects and items
- Keep answers short and conversational, spoken like a real person
- Never use bullet points or headers — just talk naturally"""

MAX_HISTORY = 20

_conversation_history = None

# ── Lazy-init clients ─────────────────────────────────────────────────────────

def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def _get_history():
    global _conversation_history
    if _conversation_history is None:
        from modules.memory import init_db, load_recent_chat
        init_db()
        past = load_recent_chat(MAX_HISTORY)
        _conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}] + past
        if past:
            print(f"[Memory] Restored {len(past)} messages from previous sessions.")
    return _conversation_history


# ── Free backend (Ollama) ─────────────────────────────────────────────────────

def _ask_ollama(prompt: str) -> str:
    from modules.memory import save_chat
    history = _get_history()
    history.append({"role": "user", "content": prompt})
    save_chat("user", prompt)
    if len(history) > MAX_HISTORY + 1:
        history[:] = [history[0]] + history[-MAX_HISTORY:]
    try:
        import ollama
        response = ollama.chat(model="llama3.2", messages=history)
        reply = response.message.content or ""
        history.append({"role": "assistant", "content": reply})
        save_chat("assistant", reply)
        return reply
    except Exception as e:
        print(f"[Ollama] Error: {e}")
        return "Ollama isn't responding. Make sure it's running — try: ollama serve"


def _ask_ollama_vision(prompt: str, b64_image: str) -> str:
    from modules.memory import save_chat
    history = _get_history()
    history.append({"role": "user", "content": prompt})
    save_chat("user", prompt)
    if len(history) > MAX_HISTORY + 1:
        history[:] = [history[0]] + history[-MAX_HISTORY:]
    try:
        import ollama
        response = ollama.chat(
            model="llava",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_VISION},
                {"role": "user", "content": prompt, "images": [b64_image]},
            ],
        )
        reply = response.message.content or ""
        history.append({"role": "assistant", "content": reply})
        save_chat("assistant", reply)
        return reply
    except Exception as e:
        print(f"[Ollama vision] Error: {e}")
        return _ask_ollama(prompt)


# ── Paid backend (OpenAI) ─────────────────────────────────────────────────────

def _ask_openai_paid(prompt: str) -> str:
    from modules.memory import save_chat
    history = _get_history()
    history.append({"role": "user", "content": prompt})
    save_chat("user", prompt)
    if len(history) > MAX_HISTORY + 1:
        history[:] = [history[0]] + history[-MAX_HISTORY:]
    try:
        response = _openai_client().chat.completions.create(
            model="gpt-4o",
            messages=history,  # type: ignore[arg-type]
            temperature=0.85,
            max_tokens=300,
        )
        reply = response.choices[0].message.content or ""
        history.append({"role": "assistant", "content": reply})
        save_chat("assistant", reply)
        return reply
    except Exception as e:
        print(f"[OpenAI] Error: {e}")
        return "Sorry, something went wrong on my end."


def _ask_openai_vision_paid(prompt: str, b64_image: str) -> str:
    from modules.memory import save_chat
    history = _get_history()
    vision_history = [{"role": "system", "content": SYSTEM_PROMPT_VISION}] + history[1:]
    user_msg = {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}", "detail": "low"}},
        ],
    }
    vision_history.append(user_msg)
    save_chat("user", prompt)
    history.append({"role": "user", "content": prompt})
    if len(history) > MAX_HISTORY + 1:
        history[:] = [history[0]] + history[-MAX_HISTORY:]
    try:
        response = _openai_client().chat.completions.create(
            model="gpt-4o",
            messages=vision_history,  # type: ignore[arg-type]
            temperature=0.85,
            max_tokens=300,
        )
        reply = response.choices[0].message.content or ""
        history.append({"role": "assistant", "content": reply})
        save_chat("assistant", reply)
        return reply
    except Exception as e:
        print(f"[OpenAI vision] Error: {e}")
        return _ask_openai_paid(prompt)


# ── Public API ────────────────────────────────────────────────────────────────

def ask_openai(prompt: str) -> str:
    """Main chat call — routes to Ollama or OpenAI based on config."""
    from modules.config import get_mode
    if get_mode() == "free":
        return _ask_ollama(prompt)
    return _ask_openai_paid(prompt)


def ask_openai_with_vision(prompt: str, b64_image: str) -> str:
    """Vision call — routes to LLaVA or GPT-4o Vision based on config."""
    from modules.config import get_mode
    if get_mode() == "free":
        return _ask_ollama_vision(prompt, b64_image)
    return _ask_openai_vision_paid(prompt, b64_image)


def reset_conversation():
    global _conversation_history
    _conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]


def generate_game_code(project_name: str, game_type: str) -> str | None:
    """Generate pygame game code — uses Ollama or OpenAI based on config."""
    from modules.config import get_mode
    prompt = (
        f"Create a complete Python {game_type} game using pygame.\n"
        f"Project name: {project_name}\n\n"
        "Generate clean, well-commented code with:\n"
        "1. Main game class\n2. Game loop\n3. Collision detection\n"
        "4. Score system\n5. Game over screen\n\n"
        "Make it fun and playable. Return only the Python code, no explanations."
    )
    try:
        if get_mode() == "free":
            import ollama
            response = ollama.chat(
                model="llama3.2",
                messages=[
                    {"role": "system", "content": "You are an expert Python game developer. Generate complete, working game code."},
                    {"role": "user", "content": prompt},
                ],
            )
            game_code = response.message.content or ""
        else:
            response = _openai_client().chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert Python game developer. Generate complete, working game code."},
                    {"role": "user", "content": prompt},
                ],
            )
            game_code = response.choices[0].message.content or ""

        if "```python" in game_code:
            game_code = game_code.split("```python")[1].split("```")[0]
        elif "```" in game_code:
            game_code = game_code.split("```")[1].split("```")[0]
        return game_code
    except Exception as e:
        print(f"Error generating game code: {e}")
        return None
