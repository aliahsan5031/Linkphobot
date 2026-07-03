"""
text_measurement.py
===================
Linkphobot - Phase 4: Typography Scaling Engine
Precise Text Measurement Utilities

All measurement functions work with PIL ImageFont objects.
No rendering side effects - pure measurement only.
"""

from PIL import ImageFont
from typing import Tuple, List, Optional


# ════════════════════════════════════════════════════════════════════════════
# SINGLE-LINE MEASUREMENT
# ════════════════════════════════════════════════════════════════════════════

def measure_text(text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    """
    Measure pixel width and height of a single text string.

    Returns:
        (width, height) tuple in pixels
    """
    if not text:
        return (0, 0)
    try:
        bbox = font.getbbox(text)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    except Exception:
        try:
            w, h = font.getsize(text)
            return (w, h)
        except Exception:
            size = getattr(font, "size", 12)
            return (len(text) * size // 2, size)


def measure_line_height(font: ImageFont.FreeTypeFont) -> int:
    """
    Get reliable line height for a font using capital + descender reference.

    Returns:
        line height in pixels
    """
    try:
        bbox = font.getbbox("Agypqj|")
        return bbox[3] - bbox[1]
    except Exception:
        return getattr(font, "size", 12)


def measure_ascent_descent(font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    """
    Get font ascent and descent values.

    Returns:
        (ascent, descent) both as positive integers
    """
    try:
        ascent, descent = font.getmetrics()
        return ascent, abs(descent)
    except Exception:
        lh = measure_line_height(font)
        return int(lh * 0.8), int(lh * 0.2)


def text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    """Return pixel width of a text string."""
    return measure_text(text, font)[0]


def text_height(font: ImageFont.FreeTypeFont) -> int:
    """Return pixel height of a single line for this font."""
    return measure_line_height(font)


# ════════════════════════════════════════════════════════════════════════════
# MULTI-LINE MEASUREMENT
# ════════════════════════════════════════════════════════════════════════════

def measure_multiline(lines: List[str],
                      font: ImageFont.FreeTypeFont,
                      line_spacing: int = 6) -> Tuple[int, int]:
    """
    Measure total width and height of a list of lines.

    Args:
        lines        : list of already-wrapped line strings
        font         : PIL font
        line_spacing : extra pixels between lines

    Returns:
        (max_width, total_height)
    """
    if not lines:
        return (0, 0)
    lh       = measure_line_height(font)
    step     = lh + line_spacing
    max_w    = max(text_width(l, font) for l in lines)
    total_h  = len(lines) * step - line_spacing  # no trailing gap
    return (max_w, total_h)


def measure_wrapped_block(text: str,
                           font: ImageFont.FreeTypeFont,
                           max_width: int,
                           line_spacing: int = 6) -> Tuple[int, int, int]:
    """
    Measure a text block after wrapping to max_width.

    Returns:
        (max_w, total_h, line_count)
    """
    from multiline_wrapping import wrap_text
    lines  = wrap_text(text, font, max_width)
    w, h   = measure_multiline(lines, font, line_spacing)
    return (w, h, len(lines))


# ════════════════════════════════════════════════════════════════════════════
# FIT TESTS
# ════════════════════════════════════════════════════════════════════════════

def fits_single_line(text: str,
                     font: ImageFont.FreeTypeFont,
                     max_width: int) -> bool:
    """Return True if text fits on one line within max_width."""
    return text_width(text, font) <= max_width


def fits_in_box(text: str,
                font: ImageFont.FreeTypeFont,
                box_width: int,
                box_height: int,
                line_spacing: int = 6) -> bool:
    """Return True if wrapped text fits inside a pixel box."""
    _, h, _ = measure_wrapped_block(text, font, box_width, line_spacing)
    return h <= box_height


def count_lines_needed(text: str,
                        font: ImageFont.FreeTypeFont,
                        max_width: int) -> int:
    """Return how many wrapped lines a text string needs."""
    from multiline_wrapping import wrap_text
    return len(wrap_text(text, font, max_width))


# ════════════════════════════════════════════════════════════════════════════
# DENSITY METRICS
# ════════════════════════════════════════════════════════════════════════════

def char_density_ratio(text: str,
                        font: ImageFont.FreeTypeFont,
                        box_width: int) -> float:
    """
    Returns ratio of text width to box width (0.0 – n).
    Values > 1.0 mean text overflows the box.
    """
    w = text_width(text, font)
    return w / max(box_width, 1)


def average_char_width(font: ImageFont.FreeTypeFont) -> float:
    """
    Estimate average character width for this font.
    Uses a representative sample of common characters.
    """
    sample = "abcdefghijklmnopqrstuvwxyz ABCDE0123456789"
    w, _   = measure_text(sample, font)
    return w / len(sample)


def estimate_chars_per_line(font: ImageFont.FreeTypeFont,
                             box_width: int) -> int:
    """
    Estimate how many average characters fit on one line.
    """
    avg_w = average_char_width(font)
    return max(1, int(box_width / avg_w))
