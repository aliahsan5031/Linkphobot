"""High-level entry points used by the UI: generate, re-render, and batch."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass

from PIL import Image

from .caption import build_caption
from .config import MAX_BATCH, get_brand
from .content import NO_API_KEY_MESSAGE, ContentError, clean_topic, generate_content, validate
from .export import build_zip, save_png
from .render import render_infographic


@dataclass
class Result:
    content: dict
    image: Image.Image
    caption: str
    png_path: str
    json_text: str
    meta: str
    title: str


def _public(content: dict) -> dict:
    return {k: v for k, v in content.items() if not k.startswith("_")}


def _finish(
    content: dict,
    topic: str,
    theme: str,
    style: str,
    size: str,
    brand: str,
    started: float,
) -> Result:
    if theme and theme != "auto":
        content["color_theme"] = theme
    image = render_infographic(content, size=size, brand=get_brand(brand))
    caption = build_caption(content, style)
    title = content.get("title") or topic
    elapsed = round(time.time() - started, 1)
    cached = " (from cache, no tokens used)" if content.get("_cached") else ""
    meta = (
        f"Topic:    {topic}\n"
        f"Title:    {title}\n"
        f"Theme:    {content.get('color_theme', '')}\n"
        f"Style:    {style}\n"
        f"Size:     {image.width}x{image.height}\n"
        f"Sections: {len(content.get('sections', []))}\n"
        f"Tokens:   {content.get('_tokens', 0)}{cached}\n"
        f"Time:     {elapsed}s\n"
        f"Model:    {content.get('_model', '')}"
    )
    return Result(
        content=content,
        image=image,
        caption=caption,
        png_path=save_png(image, title),
        json_text=json.dumps(_public(content), indent=2, ensure_ascii=False),
        meta=meta,
        title=title,
    )


def run_one(
    topic: str,
    theme: str = "auto",
    model: str = "default",
    style: str = "educational",
    size: str = "portrait",
    brand: str = "",
    api_key: str = "",
    client=None,
    use_cache: bool = True,
) -> Result:
    """Generate content with Groq, then render the image and caption."""
    started = time.time()
    topic = clean_topic(topic)
    content = generate_content(topic, model, api_key, style, client=client, use_cache=use_cache)
    return _finish(content, topic, theme, style, size, brand, started)


def rerender(
    json_text: str,
    theme: str = "auto",
    style: str = "educational",
    size: str = "portrait",
    brand: str = "",
) -> Result:
    """Render edited JSON again. No API call, so it is instant and free."""
    started = time.time()
    try:
        data = json.loads(json_text or "")
    except json.JSONDecodeError as exc:
        raise ContentError(
            f"The JSON has a syntax error on line {exc.lineno}: {exc.msg}. Fix it and try again."
        ) from exc
    if not isinstance(data, dict):
        raise ContentError("The JSON must be an object, starting with { and ending with }.")
    topic = str(data.get("title") or "infographic")
    return _finish(validate(data, topic), topic, theme, style, size, brand, started)


def parse_topics(text: str) -> list[str]:
    """One topic per line; blanks and case-insensitive duplicates are dropped."""
    seen: set[str] = set()
    topics = []
    for line in (text or "").splitlines():
        line = " ".join(line.split())
        if line and line.casefold() not in seen:
            seen.add(line.casefold())
            topics.append(line)
    return topics


def run_batch(
    topics_text: str,
    theme: str = "auto",
    model: str = "default",
    style: str = "educational",
    size: str = "portrait",
    brand: str = "",
    api_key: str = "",
    client=None,
    progress: Callable[[float, str], None] | None = None,
) -> tuple[str | None, str]:
    """Generate one infographic per line and return ``(zip_path, summary)``."""
    topics = parse_topics(topics_text)
    if not topics:
        raise ContentError("Enter at least one topic, one per line.")
    if client is None and not api_key:
        raise ContentError(NO_API_KEY_MESSAGE)
    skipped = max(0, len(topics) - MAX_BATCH)
    topics = topics[:MAX_BATCH]

    entries: list[tuple[str, Image.Image, str]] = []
    errors: list[str] = []
    for i, topic in enumerate(topics):
        if progress:
            progress(i / len(topics), f"Generating {i + 1}/{len(topics)}: {topic[:40]}")
        try:
            result = run_one(topic, theme, model, style, size, brand, api_key, client=client)
            entries.append((result.title, result.image, result.caption))
        except ContentError as exc:
            errors.append(f"{topic}: {exc}")

    zip_path = build_zip(entries, errors) if entries else None
    summary = f"{len(entries)} of {len(topics)} generated."
    if skipped:
        summary += f" {skipped} extra topic(s) skipped (limit is {MAX_BATCH} per batch)."
    if errors:
        summary += "\nFailed:\n" + "\n".join(f"  - {e}" for e in errors)
    return zip_path, summary
