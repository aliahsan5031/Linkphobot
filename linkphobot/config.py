"""Shared configuration: themes, sizes, models, and settings resolution."""

from __future__ import annotations

import os

try:  # optional: lets a local .env file provide GROQ_API_KEY
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv is optional
    pass

VERSION = "1.1.0"
DEFAULT_BRAND = "Linkphobot  |  AI-Powered LinkedIn Infographics"

MIN_TOPIC_LEN = 3
MAX_TOPIC_LEN = 200
MAX_BATCH = 10
MAX_BRAND_LEN = 60

# Groq retired llama-3.3-70b-versatile and llama-3.1-8b-instant on 2026-08-16
# (requests now return 404). These are Groq's recommended replacements.
MODELS = {
    "default": "openai/gpt-oss-120b",
    "fast": "openai/gpt-oss-20b",
    "quality": "openai/gpt-oss-120b",
}

# Tried in order if the chosen model is unavailable (retired, renamed, no access).
FALLBACK_MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b")

CAPTION_STYLES = ["educational", "data_driven", "thought_leadership", "story", "listicle"]

# name -> (width, height) in pixels. Portrait 4:5 and square are LinkedIn's
# image-post sizes.
SIZES = {
    "portrait": (1080, 1350),
    "square": (1080, 1080),
}

# theme -> (background, primary, accent, body text)
PALETTES = {
    "tech_purple": ("#0D0D1A", "#6C3FC5", "#00D4FF", "#B0B0C8"),
    "health_blue": ("#EBF8FF", "#0077B6", "#F4A261", "#0077B6"),
    "finance_navy": ("#F8F9FA", "#0A2342", "#F7C948", "#2C3E50"),
    "executive_navy": ("#FAFBFF", "#1A1F36", "#FF6B35", "#2D3561"),
    "eco_green": ("#F0FFF4", "#1B4332", "#95D5B2", "#2D6A4F"),
    "data_indigo": ("#FAF8FF", "#3C1053", "#FFB347", "#7B2D8B"),
    "engineering_navy": ("#F5F5F5", "#0A192F", "#64FFDA", "#172A45"),
    "cyber_dark": ("#0A0A0A", "#111111", "#00FF41", "#CCCCCC"),
    "clean_blue": ("#F8FAFC", "#2563EB", "#FBBF24", "#1E40AF"),
    "edu_teal": ("#FFF8F0", "#004E64", "#F4A261", "#00A5CF"),
    "creative_coral": ("#FFFBF0", "#FF4E50", "#F9D423", "#FF4E50"),
    "dev_dark": ("#11111B", "#89B4FA", "#A6E3A1", "#BAC2DE"),
    "people_warm": ("#FFFAF5", "#B5451B", "#FFD166", "#B5451B"),
    "professional": ("#FAFBFF", "#1E3A5F", "#FF6B35", "#2E6DA4"),
}
VALID_THEMES = set(PALETTES)
THEME_CHOICES = ["auto", *PALETTES]


def get_api_key(user_key: str = "") -> str:
    """Resolve the Groq key: the value typed in the UI, then the environment.

    On Hugging Face Spaces set GROQ_API_KEY as a repository secret. The key is
    never stored in the source tree. ``Linkphobot_API`` is read for backwards
    compatibility with the older pipeline.
    """
    if user_key and user_key.strip():
        return user_key.strip()
    for name in ("GROQ_API_KEY", "Linkphobot_API"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def get_brand(user_brand: str = "") -> str:
    """Footer brand line: UI value, then LINKPHOBOT_BRAND, then the default."""
    for candidate in (user_brand, os.environ.get("LINKPHOBOT_BRAND", "")):
        candidate = " ".join((candidate or "").split())
        if candidate:
            return candidate[:MAX_BRAND_LEN]
    return DEFAULT_BRAND
