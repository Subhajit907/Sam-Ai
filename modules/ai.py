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


def ask_openai(prompt):
    """Send a prompt to OpenAI and get a response"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Sam, a smart AI assistant that can control the computer."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error communicating with OpenAI: {e}")
        return "Sorry, I encountered an error. Please try again."


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
