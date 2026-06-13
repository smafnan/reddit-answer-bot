#!/usr/bin/env python3
"""
Quick verification script to test Groq API setup
Run this to confirm everything is working before starting the full pipeline
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 60)
print("🚀 Groq API Verification Script")
print("=" * 60)

# Check for API key
groq_api_key = os.environ.get("GROQ_API_KEY")

if not groq_api_key:
    print("\n❌ ERROR: GROQ_API_KEY not found in .env file!")
    print("\n   Steps to fix:")
    print("   1. Open: backend/.env")
    print("   2. Add: GROQ_API_KEY=your_actual_key_here")
    print("   3. Get key from: https://console.groq.com/keys")
    print("   4. Save and restart")
    sys.exit(1)

print(f"\n✅ GROQ_API_KEY found: {groq_api_key[:10]}...{groq_api_key[-5:]}")

# Try to import and initialize Groq
try:
    from groq import Groq
    print("✅ Groq library imported successfully")
except ImportError:
    print("❌ ERROR: Groq library not installed!")
    print("   Run: pip install groq")
    sys.exit(1)

# Try to create client
try:
    client = Groq(api_key=groq_api_key)
    print("✅ Groq client initialized successfully")
except Exception as e:
    print(f"❌ ERROR initializing Groq client: {e}")
    sys.exit(1)

# Try to make a test call
print("\n🧪 Testing Groq API with a sample query...")
try:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": "Say 'Groq is working!' in exactly those words."
            }
        ],
        temperature=0.7,
        max_tokens=50
    )

    response_text = response.choices[0].message.content
    print(f"✅ API Response: {response_text}")

    if "Groq is working" in response_text:
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Everything is working!")
        print("=" * 60)
        print("\n✨ You can now:")
        print("   1. Run: python main.py")
        print("   2. Open: INTERACTIVE_UI.html")
        print("   3. Ask any question!")
        print("\n💡 Tip: Check the console logs for 'Initialized Groq client successfully.'")
        sys.exit(0)
    else:
        print("\n⚠️  Got response but it wasn't the expected test message")

except Exception as e:
    print(f"\n❌ ERROR calling Groq API: {e}")
    print("\nPossible causes:")
    print("   - Invalid API key")
    print("   - Groq API is down")
    print("   - Network connection issue")
    print("\nTry:")
    print("   1. Check your API key at https://console.groq.com/keys")
    print("   2. Make sure you have internet connection")
    print("   3. Wait a moment and try again")
    sys.exit(1)

print("\n✅ All checks passed! You're ready to go! 🚀")
