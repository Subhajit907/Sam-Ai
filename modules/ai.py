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

# Conversation history for natural back-and-forth
_conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
MAX_HISTORY = 20  # keep last 20 messages to avoid token bloat


def ask_openai(prompt):
    """Send a prompt to OpenAI and get a response, maintaining conversation history."""
    global _conversation_history

    _conversation_history.append({"role": "user", "content": prompt})

    # Trim history if too long (keep system prompt + last MAX_HISTORY messages)
    if len(_conversation_history) > MAX_HISTORY + 1:
        _conversation_history = [_conversation_history[0]] + _conversation_history[-(MAX_HISTORY):]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",   # faster and cheaper than gpt-3.5-turbo, better quality
            messages=_conversation_history,
            temperature=0.85,       # more natural, varied responses
            max_tokens=300,         # keep spoken replies concise
        )
        reply = response.choices[0].message.content
        _conversation_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(f"Error communicating with OpenAI: {e}")
        return "Sorry, something went wrong on my end."


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
        
        game_code = response.choices[0].message.content
        
        # Clean up code if it has markdown markers
        if "```python" in game_code:
            game_code = game_code.split("```python")[1].split("```")[0]
        elif "```" in game_code:
            game_code = game_code.split("```")[1].split("```")[0]
        
        return game_code
    except Exception as e:
        print(f"Error generating game code: {e}")
        return None
