"""Saving images and building downloadable files."""

from __future__ import annotations

import io
import re
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from PIL import Image

MAX_AGE_SECONDS = 3600


def output_dir() -> Path:
    path = Path(tempfile.gettempdir()) / "linkphobot"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_old_files(max_age: float = MAX_AGE_SECONDS, now: float | None = None) -> int:
    """Delete generated files older than ``max_age`` seconds. Returns how many."""
    now = time.time() if now is None else now
    removed = 0
    for path in output_dir().iterdir():
        if path.is_file() and now - path.stat().st_mtime > max_age:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_len].strip("-")
    return slug or "infographic"


def save_png(img: Image.Image, name: str) -> str:
    """Write ``img`` to a uniquely named file and return its path."""
    cleanup_old_files()
    path = output_dir() / f"{slugify(name)}-{uuid.uuid4().hex[:8]}.png"
    img.save(path, "PNG", optimize=True)
    return str(path)


def build_zip(entries: list[tuple[str, Image.Image, str]], errors: list[str] | None = None) -> str:
    """Zip ``(name, image, caption)`` entries as numbered PNG + TXT pairs."""
    cleanup_old_files()
    path = output_dir() / f"linkphobot-batch-{uuid.uuid4().hex[:8]}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for number, (name, img, caption) in enumerate(entries, 1):
            stem = f"{number:02d}-{slugify(name)}"
            buffer = io.BytesIO()
            img.save(buffer, "PNG", optimize=True)
            archive.writestr(f"{stem}.png", buffer.getvalue())
            archive.writestr(f"{stem}.txt", caption)
        if errors:
            archive.writestr("errors.txt", "\n".join(errors))
    return str(path)
