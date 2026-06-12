from groq import Groq
import time
from config import GROQ_API_KEY

_client = None
_last_call_time = 0
_MIN_INTERVAL = 1.5  # seconds between calls to avoid rate limits


def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def llm_call(system_prompt: str, user_prompt: str, model: str = "llama-3.1-8b-instant", max_tokens: int = 800, temperature: float = 0.3) -> str:
    global _last_call_time
    client = get_client()

    # Rate limiting
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    for attempt in range(3):
        try:
            _last_call_time = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower():
                wait = 2 ** attempt
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise

    return ""
