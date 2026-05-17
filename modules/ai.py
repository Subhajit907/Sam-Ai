"""AI Module — routes chat/vision to Ollama (free) or OpenAI (paid) based on config."""

import os
import threading
from dotenv import load_dotenv

load_dotenv()

_llava_pulling = False

from modules.role import get_system_prompt, get_vision_prompt

# Legacy constants kept for any external references; actual prompts come from role module
SYSTEM_PROMPT        = get_system_prompt()
SYSTEM_PROMPT_VISION = get_vision_prompt()

MAX_HISTORY = 20

_conversation_history = None

# Document context — injected between system prompt and chat history in every API call
_doc_messages: list[dict] = []


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
        _conversation_history = [{"role": "system", "content": get_system_prompt()}] + past
        if past:
            print(f"[Memory] Restored {len(past)} messages from previous sessions.")
    return _conversation_history


def _get_full_history(query: str = "") -> list[dict]:
    """History with role prompt, product DB context (semantic search), doc context, and translator instruction."""
    history = _get_history()

    # Always use the live role prompt so switching roles takes effect immediately
    base_system = get_system_prompt()

    from modules.translator import is_active as _trans_active, get_from_lang, get_to_lang
    if _trans_active():
        base_system = (
            base_system
            + f"\n\nTRANSLATOR MODE ACTIVE: The user is speaking in {get_from_lang()}. "
            f"You MUST respond in {get_to_lang()} only. Never use any other language in your response."
        )

    system_msg: dict = {"role": "system", "content": base_system}

    # Inject only the most relevant product chunks (semantic search) when in customer support role
    from modules.role import get_role
    product_messages: list[dict] = []
    if get_role() == "customer_support":
        try:
            from modules.product_db import search_product_chunks
            ctx = search_product_chunks(query, top_k=5)
            if ctx:
                product_messages = [
                    {"role": "user",      "content": f"Here is the relevant product knowledge for this customer query:\n\n{ctx}"},
                    {"role": "assistant", "content": "Understood. I have the relevant product information ready and I'm here to help the customer."},
                ]
        except Exception as e:
            print(f"[ProductDB] Warning: could not load product context: {e}")

    extra = product_messages + _doc_messages
    if not extra:
        return [system_msg] + history[1:]

    return [system_msg] + extra + history[1:]


# ── Document context ──────────────────────────────────────────────────────────

def add_document_context(filename: str, content: str):
    """Append a text document to the shared context (supports multiple files)."""
    global _doc_messages
    _doc_messages += [
        {"role": "user",      "content": f"I've uploaded a document called '{filename}'. Here is its full content:\n\n{content}"},
        {"role": "assistant", "content": f"Got it! I've read '{filename}'. Ask me anything about it."},
    ]
    print(f"[Doc] Added: {filename} ({len(content)} chars) — {len(_doc_messages)//2} doc(s) total")


def add_document_image_context(filename: str, description: str):
    """Append an image description to context; in customer support mode also injects matched product knowledge."""
    global _doc_messages

    from modules.role import get_role
    product_context = ""
    if get_role() == "customer_support":
        try:
            from modules.product_db import search_product_chunks
            product_context = search_product_chunks(description, top_k=5)
        except Exception as e:
            print(f"[Doc] Product match warning: {e}")

    if product_context:
        user_content = (
            f"I've uploaded an image called '{filename}'. Here is a detailed description of what I can see:\n\n"
            f"{description}\n\n"
            f"Based on this image, here is the relevant product knowledge from our support database:\n\n"
            f"{product_context}"
        )
        assistant_content = (
            f"I can see the image '{filename}'. I've identified the product and matched it to our support database — "
            f"I have full knowledge of its features, known issues, and troubleshooting steps. "
            f"Please tell me what problem you're experiencing and I'll guide you through fixing it."
        )
        print(f"[Doc] Added image + product context: {filename} — {len(_doc_messages)//2 + 1} doc(s) total")
    else:
        user_content = f"I've uploaded an image called '{filename}'. Here is a detailed description of it:\n\n{description}"
        assistant_content = f"Got it! I can see the image '{filename}'. Ask me anything about it."
        print(f"[Doc] Added image: {filename} — {len(_doc_messages)//2 + 1} doc(s) total")

    _doc_messages += [
        {"role": "user",      "content": user_content},
        {"role": "assistant", "content": assistant_content},
    ]


def clear_document_context():
    global _doc_messages
    _doc_messages = []
    print("[Doc] All documents cleared.")


def has_document() -> bool:
    return bool(_doc_messages)


def document_count() -> int:
    return len(_doc_messages) // 2


# Legacy single-file setters — kept for backward compatibility
def set_document_context(filename: str, content: str):
    clear_document_context()
    add_document_context(filename, content)


def set_document_image_context(filename: str, description: str):
    clear_document_context()
    add_document_image_context(filename, description)


# ── Image description (used for uploaded image documents) ─────────────────────

def _image_describe_prompt() -> str:
    from modules.role import get_role
    if get_role() == "customer_support":
        return (
            "Describe this image in detail, focusing on the following:\n"
            "1. The product shown — identify the brand name, product type (e.g. vacuum cleaner, air fryer, blender), "
            "and any visible model name or model number on the label or body.\n"
            "2. The overall condition — does it look new, used, or damaged?\n"
            "3. Any visible damage, defects, or faults — cracks, burns, broken parts, loose components, error lights on the display.\n"
            "4. The state of key components — e.g. glass bowl, brush roll, cord, buttons, filter, crisper plate, attachments.\n"
            "5. Any text, warning labels, error codes, or numbers visible on the product.\n"
            "Be specific and thorough — this description will be used to diagnose and fix a customer's product issue."
        )
    return "Describe everything in this image in detail — all text, objects, layout, colours, numbers. Be thorough."


def describe_image_free(b64: str) -> str:
    try:
        import ollama
        response = ollama.chat(
            model="llava",
            messages=[{
                "role": "user",
                "content": _image_describe_prompt(),
                "images": [b64],
            }],
        )
        return response.message.content or ""
    except Exception as e:
        err = str(e)
        if "404" in err or "not found" in err.lower():
            _pull_llava_background()
            return "[Vision model not ready — pulling llava in background. Try again in a few minutes.]"
        return f"[Image analysis error: {e}]"


def describe_image_paid(b64: str, mime: str = "image/jpeg") -> str:
    try:
        response = _openai_client().chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _image_describe_prompt()},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}},
                ],
            }],
            max_tokens=1000,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"[Image analysis error: {e}]"


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
        response = ollama.chat(model="llama3.2", messages=_get_full_history(prompt))
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
                {"role": "system", "content": get_vision_prompt()},
                {"role": "user", "content": prompt, "images": [b64_image]},
            ],
        )
        reply = response.message.content or ""
        history.append({"role": "assistant", "content": reply})
        save_chat("assistant", reply)
        return reply
    except Exception as e:
        err = str(e)
        print(f"[Ollama vision] Error: {err}")
        if "404" in err or "not found" in err.lower():
            _pull_llava_background()
            return "My vision model isn't downloaded yet — I'm pulling it in the background right now. Give me a couple of minutes and try again!"
        return _ask_ollama(prompt)


def _pull_llava_background():
    global _llava_pulling
    if _llava_pulling:
        return
    _llava_pulling = True

    def _pull():
        global _llava_pulling
        print("[Ollama] Pulling llava in background...")
        try:
            import subprocess
            subprocess.run(["ollama", "pull", "llava"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[Ollama] llava pull complete.")
        except Exception as e:
            print(f"[Ollama] llava pull failed: {e}")
        finally:
            _llava_pulling = False

    threading.Thread(target=_pull, daemon=True).start()


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
            messages=_get_full_history(prompt),  # type: ignore[arg-type]
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
    # Build vision history with semantic product context injected (same as text calls)
    from modules.role import get_role
    product_inject: list[dict] = []
    if get_role() == "customer_support":
        try:
            from modules.product_db import search_product_chunks
            ctx = search_product_chunks(prompt, top_k=5)
            if ctx:
                product_inject = [
                    {"role": "user",      "content": f"Here is the relevant product knowledge for this customer query:\n\n{ctx}"},
                    {"role": "assistant", "content": "Understood. I have the relevant product information ready and I'm here to help the customer."},
                ]
        except Exception as e:
            print(f"[ProductDB] Warning: could not load product context: {e}")
    vision_history = [{"role": "system", "content": get_vision_prompt()}] + product_inject + _doc_messages + history[1:]
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
    from modules.config import get_mode
    if get_mode() == "free":
        return _ask_ollama(prompt)
    return _ask_openai_paid(prompt)


def ask_openai_with_vision(prompt: str, b64_image: str) -> str:
    from modules.config import get_mode
    if get_mode() == "free":
        return _ask_ollama_vision(prompt, b64_image)
    return _ask_openai_vision_paid(prompt, b64_image)


def reset_conversation():
    global _conversation_history
    _conversation_history = [{"role": "system", "content": get_system_prompt()}]


def switch_role(role_name: str) -> None:
    """Switch to a new role and reset conversation history to match the new persona."""
    from modules.role import set_role
    set_role(role_name)
    reset_conversation()
    print(f"[Role] Switched to: {role_name}")


def generate_game_code(project_name: str, game_type: str) -> str | None:
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
