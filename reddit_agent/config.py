import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if not os.path.exists(dotenv_path):
    print("WARNING: No .env file found. Copy .env.example to .env")
    print("Using simulated mode (no LLM calls).")
    load_dotenv(dotenv_path, override=False)
else:
    load_dotenv(dotenv_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
HAS_API_KEY = bool(GROQ_API_KEY) and "your_" not in GROQ_API_KEY
