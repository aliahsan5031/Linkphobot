"""LinkedIn caption building: hashtag cleanup and per-style fallbacks."""

from __future__ import annotations

import re

LINKEDIN_CAPTION_LIMIT = 3000
_HASHTAG_ONLY_LINE = re.compile(r"^\s*(?:#\w+\s*)+$")


def normalize_hashtags(tags: object, limit: int = 8) -> list[str]:
    """Return unique, well-formed hashtags (``#Word``), at most ``limit``."""
    if isinstance(tags, str):
        tags = re.findall(r"#?\w+", tags)
    if not isinstance(tags, (list, tuple)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        word = re.sub(r"\W", "", str(raw))
        if not word:
            continue
        tag = "#" + word
        if tag.casefold() in seen:
            continue
        seen.add(tag.casefold())
        out.append(tag)
    return out[:limit]


def _strip_trailing_hashtags(text: str) -> str:
    """Drop trailing lines made only of hashtags; we append our own cleaned set."""
    lines = text.rstrip().splitlines()
    while lines and (not lines[-1].strip() or _HASHTAG_ONLY_LINE.match(lines[-1])):
        lines.pop()
    return "\n".join(lines).strip()


def _points(content: dict) -> list[str]:
    points = [p for p in content.get("key_points", []) if p]
    if points:
        return points[:4]
    # fall back to the first bullet of each section
    return [s["content"][0] for s in content.get("sections", []) if s.get("content")][:4]


def _fallback_body(content: dict, style: str) -> str:
    title = content.get("title", "").strip()
    cta = content.get("call_to_action", "").strip() or "Save this post and share it."
    points = _points(content)
    stats = content.get("statistics", [])
    bullets = "\n".join(f"• {p}" for p in points)

    if style == "listicle":
        numbered = "\n".join(f"{i}. {p}" for i, p in enumerate(points, 1))
        return f"{title}\n\n{numbered}\n\n{cta}".strip()
    if style == "data_driven" and stats:
        lead = stats[0]
        headline = f"{lead['value']} {lead['label']}".strip()
        return f"{headline}\n\n{title}\n\n{bullets}\n\n{cta}".strip()
    if style == "thought_leadership":
        return (
            f"Hot take on {title}:\n\n{bullets}\n\n"
            "Do you agree? Tell me what you see in your own work.\n\n" + cta
        ).strip()
    if style == "story":
        paragraphs = "\n\n".join(points)
        return (
            f"A lesson that changed how I think about {title}:\n\n{paragraphs}\n\n{cta}"
        ).strip()
    # educational (default)
    return f"{title}\n\nWhat every professional should know:\n\n{bullets}\n\n{cta}".strip()


def build_caption(content: dict, style: str = "educational", max_tags: int = 5) -> str:
    """Build the post text: model caption if present, else a style-specific one."""
    body = _strip_trailing_hashtags(str(content.get("linkedin_caption") or ""))
    if not body:
        body = _fallback_body(content, style)
    tags = " ".join(normalize_hashtags(content.get("hashtags"))[:max_tags])
    if not tags:
        return body[:LINKEDIN_CAPTION_LIMIT]
    room = LINKEDIN_CAPTION_LIMIT - len(tags) - 2
    return f"{body[:room].rstrip()}\n\n{tags}"
