import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if not os.path.exists(dotenv_path):
    print("ERROR: No .env file found!")
    print("Run: copy .env.example .env")
    exit(1)

load_dotenv(dotenv_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

if not GROQ_API_KEY or "your_" in GROQ_API_KEY:
    print("ERROR: Missing GROQ_API_KEY in .env")
    print("Get a free key at: https://console.groq.com/keys")
    exit(1)
