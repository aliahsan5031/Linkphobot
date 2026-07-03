"""
groq_client.py
==============
Linkphobot - Phase 1: Content Generator
Groq API Client Wrapper

Handles:
- API key loading from environment / Colab secrets / .env
- Client initialization
- Completion requests with retry logic
- Token usage tracking
"""

import os
import time
from typing import Optional

# ── Try loading from .env file (local dev) ──────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required in Colab

# ── Try Colab userdata (Google Colab secrets) ───────────────────────────────
def _load_colab_secret(key: str) -> Optional[str]:
    """Load secret from Google Colab userdata if available."""
    try:
        from google.colab import userdata
        return userdata.get(key)
    except Exception:
        return None


def get_api_key(key_name: str = "GROQ_API_KEY") -> str:
    """
    Resolve API key using this priority chain:
      1. Environment variable (os.environ)
      2. Google Colab userdata secrets
      3. .env file (already loaded above)

    Raises:
        EnvironmentError: if key is not found anywhere
    """
    value = (
        os.environ.get(key_name)
        or _load_colab_secret(key_name)
    )
    if not value:
        raise EnvironmentError(
            f"\n[Linkphobot] ❌  API key '{key_name}' not found.\n"
            "Please set it via one of these methods:\n"
            "  • Colab:  Secrets tab → add GROQ_API_KEY\n"
            "  • Local:  export GROQ_API_KEY=your_key  (or add to .env)\n"
            "  • HF:     Settings → Repository Secrets → GROQ_API_KEY\n"
        )
    return value


# ── Groq client factory ──────────────────────────────────────────────────────
def create_groq_client():
    """
    Create and return an authenticated Groq client.

    Returns:
        groq.Groq instance ready to use
    """
    try:
        from groq import Groq
    except ImportError as e:
        raise ImportError(
            "[Linkphobot] ❌  'groq' package not installed.\n"
            "Run:  pip install groq"
        ) from e

    api_key = get_api_key("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    return client


# ── Core completion function ─────────────────────────────────────────────────
def groq_complete(
    prompt: str,
    system_prompt: str,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    retries: int = 3,
    retry_delay: float = 2.0,
    client=None,
) -> dict:
    """
    Send a completion request to Groq and return structured response.

    Args:
        prompt          : User message / main prompt
        system_prompt   : System context instructions
        model           : Groq model identifier
        temperature     : Creativity level (0.0 – 1.0)
        max_tokens      : Maximum tokens in response
        retries         : Number of retry attempts on failure
        retry_delay     : Seconds to wait between retries
        client          : Optional pre-built Groq client (reuse across calls)

    Returns:
        dict with keys:
            content  (str)   – raw text response
            model    (str)   – model used
            usage    (dict)  – token usage stats
            elapsed  (float) – request time in seconds
    """
    if client is None:
        client = create_groq_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": prompt},
    ]

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            t_start = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed = round(time.time() - t_start, 2)

            content = response.choices[0].message.content
            usage   = {
                "prompt_tokens":     response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens":      response.usage.total_tokens,
            }

            return {
                "content": content,
                "model":   response.model,
                "usage":   usage,
                "elapsed": elapsed,
            }

        except Exception as e:
            last_error = e
            if attempt < retries:
                print(f"[Linkphobot] ⚠️  Attempt {attempt} failed: {e}. Retrying in {retry_delay}s…")
                time.sleep(retry_delay)
            else:
                raise RuntimeError(
                    f"[Linkphobot] ❌  Groq request failed after {retries} attempts.\n"
                    f"Last error: {last_error}"
                ) from last_error


# ── Available models reference ───────────────────────────────────────────────
GROQ_MODELS = {
    "fast":    "llama-3.1-8b-instant",        # fastest, good for drafts
    "default": "llama-3.3-70b-versatile",     # balanced quality/speed ← recommended
    "quality": "llama-3.3-70b-versatile",     # best quality
    "mixtral": "mixtral-8x7b-32768",          # large context window
}
