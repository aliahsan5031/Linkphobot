"""
font_scaling.py
===============
Linkphobot - Phase 4: Typography Scaling Engine
Dynamic Font Scaling System

Handles:
- Scale font size to fit text into a pixel box
- Scale titles based on character length
- Scale body text based on content density
- Scale font to exact single-line fit
- Typography scale tables for consistent sizing
"""

import sys
import os
from PIL import ImageFont
from typing import Tuple, Optional, Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from text_measurement import (
    text_width, measure_line_height, fits_in_box,
    fits_single_line, count_lines_needed
)


# ════════════════════════════════════════════════════════════════════════════
# FONT LOADER BRIDGE
# ════════════════════════════════════════════════════════════════════════════

def _load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """
    Load font via phase3 font_loader if available, else PIL default.
    Falls back gracefully so Phase 4 works standalone.
    """
    try:
        p3 = os.path.join(os.path.dirname(__file__), "..", "phase3")
        if p3 not in sys.path:
            sys.path.insert(0, os.path.abspath(p3))
        from font_loader import get_font
        return get_font(weight, size)
    except Exception:
        try:
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()


# ════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY SCALE TABLES
# ════════════════════════════════════════════════════════════════════════════

# Base sizes for 1080px canvas  (element_type -> base_size_px)
BASE_SCALE = {
    "title":         64,
    "subtitle":      28,
    "section_head":  30,
    "bullet":        22,
    "stat_value":    44,
    "stat_label":    18,
    "key_point":     22,
    "cta":           24,
    "hashtag":       18,
    "caption":       16,
    "label":         15,
    "badge":         15,
}

# Min / Max clamp for each element type
SIZE_CLAMPS = {
    "title":         (32, 72),
    "subtitle":      (18, 34),
    "section_head":  (18, 34),
    "bullet":        (14, 26),
    "stat_value":    (28, 52),
    "stat_label":    (13, 22),
    "key_point":     (14, 26),
    "cta":           (16, 28),
    "hashtag":       (13, 22),
    "caption":       (12, 20),
    "label":         (11, 18),
    "badge":         (11, 18),
}

# Density reduction table: applied when n_sections * n_bullets is high
# (density_threshold -> scale_factor)
DENSITY_SCALE = [
    (0,   1.00),
    (16,  0.96),
    (20,  0.92),
    (24,  0.88),
    (28,  0.84),
    (32,  0.80),
]


def get_density_scale(n_sections: int, n_bullets: int) -> float:
    """
    Return a global scale factor based on content density.
    Higher density = smaller fonts to prevent overflow.
    """
    density = n_sections * n_bullets
    factor  = 1.0
    for threshold, scale in DENSITY_SCALE:
        if density >= threshold:
            factor = scale
    return factor


def get_base_size(element_type: str,
                   n_sections: int = 4,
                   n_bullets: int = 4) -> int:
    """
    Return the appropriate font size for an element type,
    scaled for content density.

    Args:
        element_type: key from BASE_SCALE
        n_sections:   number of sections in the infographic
        n_bullets:    average bullets per section

    Returns:
        font size in pixels (clamped)
    """
    base    = BASE_SCALE.get(element_type, 20)
    density = get_density_scale(n_sections, n_bullets)
    scaled  = int(base * density)
    lo, hi  = SIZE_CLAMPS.get(element_type, (12, 72))
    return max(lo, min(hi, scaled))


# ════════════════════════════════════════════════════════════════════════════
# SCALE TO FIT  –  shrink font to fit text into a box
# ════════════════════════════════════════════════════════════════════════════

def scale_font_to_fit_box(text: str,
                            weight: str,
                            box_width: int,
                            box_height: int,
                            start_size: int,
                            min_size: int = 10,
                            line_spacing: int = 6) -> Tuple[ImageFont.FreeTypeFont, int]:
    """
    Binary-search the largest font size that fits text into a pixel box.

    Args:
        text         : text to fit
        weight       : font weight string
        box_width    : available width  in pixels
        box_height   : available height in pixels
        start_size   : starting (maximum) font size
        min_size     : minimum allowed font size
        line_spacing : extra pixels between lines

    Returns:
        (font, final_size) tuple
    """
    from multiline_wrapping import wrapped_block_height

    lo, hi = min_size, start_size
    best_font = _load_font(weight, min_size)
    best_size = min_size

    while lo <= hi:
        mid  = (lo + hi) // 2
        font = _load_font(weight, mid)
        h    = wrapped_block_height(text, font, box_width, line_spacing)
        if h <= box_height:
            best_font = font
            best_size = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return best_font, best_size


def scale_font_to_fit_width(text: str,
                              weight: str,
                              box_width: int,
                              start_size: int,
                              min_size: int = 10) -> Tuple[ImageFont.FreeTypeFont, int]:
    """
    Find the largest font size where text fits on ONE line within box_width.

    Args:
        text       : single-line text string
        weight     : font weight
        box_width  : pixel width to fit within
        start_size : maximum starting font size
        min_size   : minimum allowed size

    Returns:
        (font, final_size) tuple
    """
    for size in range(start_size, min_size - 1, -1):
        font = _load_font(weight, size)
        if text_width(text, font) <= box_width:
            return font, size
    font = _load_font(weight, min_size)
    return font, min_size


def scale_font_for_lines(text: str,
                          weight: str,
                          box_width: int,
                          max_lines: int,
                          start_size: int,
                          min_size: int = 10) -> Tuple[ImageFont.FreeTypeFont, int]:
    """
    Find the largest font size where text wraps into at most max_lines.

    Returns:
        (font, final_size) tuple
    """
    for size in range(start_size, min_size - 1, -1):
        font   = _load_font(weight, size)
        n_lines = count_lines_needed(text, font, box_width)
        if n_lines <= max_lines:
            return font, size
    font = _load_font(weight, min_size)
    return font, min_size


# ════════════════════════════════════════════════════════════════════════════
# TITLE SCALING
# ════════════════════════════════════════════════════════════════════════════

def scale_title(title: str,
                 weight: str = "extrabold",
                 box_width: int = 972,
                 max_lines: int = 3,
                 base_size: int = 64,
                 min_size: int = 32) -> Tuple[ImageFont.FreeTypeFont, int]:
    """
    Scale title font to fit within box_width in at most max_lines.

    Also applies a length-based heuristic for fast first-pass sizing:
    - <= 20 chars: use base_size
    - <= 32 chars: 88% of base
    - <= 44 chars: 78% of base
    - > 44 chars:  68% of base

    Returns:
        (font, size)
    """
    n = len(title)
    if   n <= 20: start = base_size
    elif n <= 32: start = max(min_size, int(base_size * 0.88))
    elif n <= 44: start = max(min_size, int(base_size * 0.78))
    else:         start = max(min_size, int(base_size * 0.68))

    return scale_font_for_lines(title, weight, box_width,
                                  max_lines, start, min_size)


def scale_subtitle(subtitle: str,
                    weight: str = "regular",
                    box_width: int = 892,
                    max_lines: int = 2,
                    base_size: int = 28,
                    min_size: int = 16) -> Tuple[ImageFont.FreeTypeFont, int]:
    """Scale subtitle font similarly."""
    n = len(subtitle)
    if   n <= 40: start = base_size
    elif n <= 60: start = max(min_size, int(base_size * 0.90))
    else:         start = max(min_size, int(base_size * 0.82))

    return scale_font_for_lines(subtitle, weight, box_width,
                                  max_lines, start, min_size)


# ════════════════════════════════════════════════════════════════════════════
# SECTION HEADING SCALING
# ════════════════════════════════════════════════════════════════════════════

def scale_section_heading(heading: str,
                           weight: str = "bold",
                           box_width: int = 900,
                           max_lines: int = 2,
                           base_size: int = 30,
                           min_size: int = 18) -> Tuple[ImageFont.FreeTypeFont, int]:
    """Scale section heading font to fit in one or two lines."""
    n = len(heading)
    if   n <= 20: start = base_size
    elif n <= 32: start = max(min_size, int(base_size * 0.90))
    else:         start = max(min_size, int(base_size * 0.82))

    return scale_font_for_lines(heading, weight, box_width,
                                  max_lines, start, min_size)


# ════════════════════════════════════════════════════════════════════════════
# BULLET SCALING
# ════════════════════════════════════════════════════════════════════════════

def scale_bullet_font(bullets: list,
                       weight: str = "regular",
                       box_width: int = 880,
                       max_lines_per_bullet: int = 3,
                       base_size: int = 22,
                       min_size: int = 14,
                       n_sections: int = 4) -> Tuple[ImageFont.FreeTypeFont, int]:
    """
    Find the largest font where ALL bullets in a list wrap to at most
    max_lines_per_bullet.

    Also applies density reduction for many sections.

    Returns:
        (font, size)
    """
    # Apply density reduction
    density_scale = get_density_scale(n_sections, len(bullets))
    start = max(min_size, int(base_size * density_scale))

    for size in range(start, min_size - 1, -1):
        font = _load_font(weight, size)
        ok   = all(count_lines_needed(b, font, box_width) <= max_lines_per_bullet
                   for b in bullets if b)
        if ok:
            return font, size

    return _load_font(weight, min_size), min_size


# ════════════════════════════════════════════════════════════════════════════
# STAT VALUE SCALING
# ════════════════════════════════════════════════════════════════════════════

def scale_stat_value(value: str,
                      weight: str = "extrabold",
                      box_width: int = 200,
                      base_size: int = 44,
                      min_size: int = 22) -> Tuple[ImageFont.FreeTypeFont, int]:
    """Scale stat value to fit single-line within box_width."""
    return scale_font_to_fit_width(value, weight, box_width,
                                    base_size, min_size)


# ════════════════════════════════════════════════════════════════════════════
# GLOBAL TYPOGRAPHY RESOLVER
# ════════════════════════════════════════════════════════════════════════════

def resolve_typography(content: dict,
                        canvas_width: int = 1080,
                        margin: int = 54) -> dict:
    """
    Resolve all font sizes for an entire infographic in one call.

    Args:
        content      : Phase 1 content dict
        canvas_width : canvas pixel width
        margin       : left/right margin

    Returns:
        dict of {element_type: {"size": int, "weight": str}}

    Example return:
        {
            "title":        {"size": 58, "weight": "extrabold"},
            "subtitle":     {"size": 26, "weight": "regular"},
            "section_head": {"size": 28, "weight": "bold"},
            "bullet":       {"size": 20, "weight": "regular"},
            ...
        }
    """
    content_w   = canvas_width - margin * 2
    inner_w     = content_w - 56 * 2   # header horizontal padding
    sections    = content.get("sections", [])
    n_sec       = max(1, len(sections))
    n_bull      = max(1, max((len(s.get("content",[])) for s in sections), default=1))
    all_bullets = [b for s in sections for b in s.get("content",[])]

    title    = content.get("title", "")
    subtitle = content.get("subtitle", "")

    _, title_sz = scale_title(title,    box_width=inner_w)
    _, sub_sz   = scale_subtitle(subtitle, box_width=inner_w)

    sec_head_sz = BASE_SCALE["section_head"]
    for s in sections:
        _, sz = scale_section_heading(s.get("heading",""), box_width=content_w-120)
        sec_head_sz = min(sec_head_sz, sz)

    bull_w = content_w - 120
    _, bull_sz = scale_bullet_font(
        all_bullets, box_width=bull_w,
        n_sections=n_sec,
        base_size=BASE_SCALE["bullet"]
    ) if all_bullets else (None, BASE_SCALE["bullet"])

    density = get_density_scale(n_sec, n_bull)

    def ds(key):
        lo, hi = SIZE_CLAMPS.get(key, (12, 72))
        return max(lo, min(hi, int(BASE_SCALE.get(key, 18) * density)))

    return {
        "title":        {"size": title_sz,   "weight": "extrabold"},
        "subtitle":     {"size": sub_sz,     "weight": "regular"},
        "section_head": {"size": sec_head_sz,"weight": "bold"},
        "bullet":       {"size": bull_sz,    "weight": "regular"},
        "stat_value":   {"size": ds("stat_value"), "weight": "extrabold"},
        "stat_label":   {"size": ds("stat_label"), "weight": "medium"},
        "key_point":    {"size": ds("key_point"),  "weight": "semibold"},
        "cta":          {"size": ds("cta"),         "weight": "semibold"},
        "hashtag":      {"size": ds("hashtag"),     "weight": "regular"},
        "caption":      {"size": ds("caption"),     "weight": "regular"},
        "label":        {"size": ds("label"),       "weight": "semibold"},
    }
