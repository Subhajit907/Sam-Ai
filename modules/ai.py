"""AI Module - Handles OpenAI API interactions"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable is not set!")
    print("Please add your API key to the .env file")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

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

MAX_HISTORY = 20  # keep last 20 messages to avoid token bloat

# Conversation history — seeded from persistent DB on first use
_conversation_history = None


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


def ask_openai(prompt):
    """Send a prompt to OpenAI and get a response, maintaining conversation history."""
    from modules.memory import save_chat
    history = _get_history()

    history.append({"role": "user", "content": prompt})
    save_chat("user", prompt)

    # Trim history if too long (keep system prompt + last MAX_HISTORY messages)
    if len(history) > MAX_HISTORY + 1:
        history[:] = [history[0]] + history[-(MAX_HISTORY):]

    try:
        response = client.chat.completions.create(
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
        print(f"Error communicating with OpenAI: {e}")
        return "Sorry, something went wrong on my end."


def ask_openai_with_vision(prompt: str, b64_image: str) -> str:
    """
    Send a prompt + camera frame to GPT-4o and get a response.
    Uses the vision-aware system prompt and maintains the same conversation history.
    """
    from modules.memory import save_chat
    history = _get_history()

    # Swap system prompt to vision-aware version for this call
    vision_history = [{"role": "system", "content": SYSTEM_PROMPT_VISION}] + history[1:]

    user_msg = {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_image}",
                    "detail": "low",
                },
            },
        ],
    }
    vision_history.append(user_msg)
    save_chat("user", prompt)

    # Also append text-only version to the real history so context is preserved
    history.append({"role": "user", "content": prompt})
    if len(history) > MAX_HISTORY + 1:
        history[:] = [history[0]] + history[-(MAX_HISTORY):]

    try:
        response = client.chat.completions.create(
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
        print(f"Vision API error: {e}")
        return ask_openai(prompt)   # graceful fallback to text-only


def reset_conversation():
    """Clear conversation history (start fresh)."""
    global _conversation_history
    _conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]


def generate_game_code(project_name, game_type):
    """Generate game code using OpenAI"""
    try:
        prompt = f"""Create a complete Python {game_type} game using pygame. 
        Project name: {project_name}
        
        Generate clean, well-commented code with:
        1. Main game class
        2. Game loop
        3. Collision detection
        4. Score system
        5. Game over screen
        
        Make it fun and playable. Return only the Python code, no explanations."""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert Python game developer. Generate complete, working game code."},
                {"role": "user", "content": prompt}
            ]
        )
        
        game_code = response.choices[0].message.content or ""

        # Clean up code if it has markdown markers
        if "```python" in game_code:
            game_code = game_code.split("```python")[1].split("```")[0]
        elif "```" in game_code:
            game_code = game_code.split("```")[1].split("```")[0]
        
        return game_code
    except Exception as e:
        print(f"Error generating game code: {e}")
        return None
