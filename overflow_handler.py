"""
overflow_handler.py
===================
Linkphobot - Phase 4: Typography Scaling Engine
Overflow Detection & Prevention System

Handles:
- Detect text overflow before rendering
- Truncate text to fit boxes
- Split content into pages (carousel)
- Reflow sections when canvas height exceeded
- Shrink cards proportionally
- Emergency fallback strategies
"""

import sys
import os
from typing import List, Dict, Tuple, Optional
from PIL import ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from text_measurement import (
    fits_in_box, measure_line_height,
    count_lines_needed
)
from multiline_wrapping import (
    wrap_and_truncate, wrapped_block_height
)
from font_scaling import (
    scale_font_to_fit_box,
    scale_bullet_font,
    _load_font,
)


# ════════════════════════════════════════════════════════════════════════════
# CANVAS CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

CANVAS_H        = 1350
CANVAS_W        = 1080
MARGIN          = 54
SAFE_HEIGHT     = CANVAS_H - MARGIN * 2  # 1242px usable
MIN_CARD_HEIGHT = 80
BLOCK_GAP       = 16


# ════════════════════════════════════════════════════════════════════════════
# OVERFLOW DETECTION
# ════════════════════════════════════════════════════════════════════════════

def detect_text_overflow(text: str,
                          font: ImageFont.FreeTypeFont,
                          box_width: int,
                          box_height: int,
                          line_spacing: int = 6) -> bool:
    """
    Return True if text overflows the given box dimensions.
    """
    return not fits_in_box(text, font, box_width, box_height, line_spacing)


def detect_layout_overflow(block_heights: List[int],
                            gaps: List[int],
                            canvas_height: int = SAFE_HEIGHT) -> bool:
    """
    Return True if stacked blocks exceed canvas height.

    Args:
        block_heights : list of block heights in pixels
        gaps          : list of gap sizes between blocks (len = len(blocks)-1)
        canvas_height : available canvas height
    """
    total = sum(block_heights)
    total += sum(gaps[:len(block_heights)-1])
    return total > canvas_height


def overflow_amount(block_heights: List[int],
                     gaps: List[int],
                     canvas_height: int = SAFE_HEIGHT) -> int:
    """
    Return how many pixels the layout overflows by (0 if no overflow).
    """
    total = sum(block_heights) + sum(gaps[:len(block_heights)-1])
    return max(0, total - canvas_height)


# ════════════════════════════════════════════════════════════════════════════
# TEXT-LEVEL OVERFLOW FIX
# ════════════════════════════════════════════════════════════════════════════

def fit_text_to_box(text: str,
                     weight: str,
                     box_width: int,
                     box_height: int,
                     start_size: int,
                     min_size: int = 10,
                     line_spacing: int = 6) -> Tuple[ImageFont.FreeTypeFont, int, List[str]]:
    """
    Scale font and wrap text to guarantee it fits inside a pixel box.

    Returns:
        (font, final_size, wrapped_lines)
    """
    from font_scaling import scale_font_to_fit_box
    from multiline_wrapping import wrap_text

    font, size = scale_font_to_fit_box(
        text, weight, box_width, box_height,
        start_size, min_size, line_spacing
    )
    lines = wrap_text(text, font, box_width)
    return font, size, lines


def truncate_bullets_to_fit(bullets: List[str],
                              font: ImageFont.FreeTypeFont,
                              box_width: int,
                              available_height: int,
                              line_spacing: int = 6,
                              bullet_gap: int = 10) -> List[str]:
    """
    Remove bullets from the end until the list fits in available_height.
    Always keeps at least 1 bullet.

    Returns:
        trimmed bullets list
    """
    if not bullets:
        return bullets

    lh   = measure_line_height(font)
    step = lh + line_spacing

    def total_h(blist):
        h = 0
        for b in blist:
            n = count_lines_needed(b, font, box_width)
            h += n * step + bullet_gap
        return h - bullet_gap if blist else 0

    result = list(bullets)
    while len(result) > 1 and total_h(result) > available_height:
        result.pop()

    # If even 1 bullet overflows, truncate its text
    if result and total_h(result) > available_height:
        from multiline_wrapping import wrap_and_truncate
        max_lines = max(1, available_height // step)
        result[0] = " ".join(
            wrap_and_truncate(result[0], font, box_width, max_lines)
        )

    return result


# ════════════════════════════════════════════════════════════════════════════
# CARD-LEVEL OVERFLOW FIX
# ════════════════════════════════════════════════════════════════════════════

def compress_card_height(required_h: int,
                          available_h: int,
                          min_h: int = MIN_CARD_HEIGHT) -> int:
    """
    Scale down a card height to fit available space.

    Returns:
        clamped height (never below min_h)
    """
    return max(min_h, min(required_h, available_h))


def redistribute_heights(block_heights: List[int],
                          total_available: int,
                          minimums: Optional[List[int]] = None) -> List[int]:
    """
    Proportionally reduce block heights to fit total_available.
    Respects per-block minimum heights.

    Args:
        block_heights  : list of required heights
        total_available: pixel budget
        minimums       : list of minimum heights per block

    Returns:
        adjusted list of heights
    """
    if not block_heights:
        return block_heights

    mins   = minimums or [MIN_CARD_HEIGHT] * len(block_heights)
    total  = sum(block_heights)

    if total <= total_available:
        return block_heights

    # First pass: proportional reduction
    scale  = total_available / total
    result = [max(m, int(h * scale)) for h, m in zip(block_heights, mins)]

    # Second pass: if still over budget, shave from largest blocks
    excess = sum(result) - total_available
    if excess > 0:
        indices = sorted(range(len(result)), key=lambda i: -result[i])
        for idx in indices:
            if excess <= 0:
                break
            reducible = result[idx] - mins[idx]
            cut        = min(reducible, excess)
            result[idx] -= cut
            excess     -= cut

    return result


# ════════════════════════════════════════════════════════════════════════════
# PAGE SPLITTER  –  carousel overflow handler
# ════════════════════════════════════════════════════════════════════════════

def split_sections_into_pages(sections: List[dict],
                               sections_per_first_page: int = 2,
                               sections_per_page: int = 3) -> List[List[dict]]:
    """
    Split sections list into carousel pages.

    Args:
        sections               : full list of section dicts
        sections_per_first_page: how many sections on page 1 (header takes space)
        sections_per_page      : sections on subsequent pages

    Returns:
        list of section lists, one per page
    """
    if not sections:
        return [[]]

    pages = []
    pages.append(sections[:sections_per_first_page])
    rest = sections[sections_per_first_page:]

    while rest:
        pages.append(rest[:sections_per_page])
        rest = rest[sections_per_page:]

    return pages


def compute_pages_needed(sections: List[dict],
                          statistics: List[dict],
                          key_points: List[str],
                          header_h: int = 420,
                          section_h_avg: int = 160,
                          stats_h: int = 160,
                          kp_h: int = 140,
                          footer_h: int = 120,
                          canvas_h: int = SAFE_HEIGHT) -> int:
    """
    Estimate the minimum number of carousel pages needed.

    Returns:
        integer page count (minimum 1)
    """
    extras = (
        (stats_h if statistics else 0)
        + (kp_h   if key_points else 0)
        + footer_h + BLOCK_GAP * 4
    )

    remaining_first_page = canvas_h - header_h - extras - BLOCK_GAP * 2
    remaining_other_page = canvas_h - extras - BLOCK_GAP

    # How many sections fit per page
    sec_per_first = max(1, remaining_first_page // (section_h_avg + BLOCK_GAP))
    sec_per_other = max(1, remaining_other_page // (section_h_avg + BLOCK_GAP))

    n = len(sections)
    if n == 0:
        return 1

    if n <= sec_per_first:
        return 1

    remaining = n - sec_per_first
    extra_pages = -(-remaining // sec_per_other)  # ceiling division
    return 1 + extra_pages


# ════════════════════════════════════════════════════════════════════════════
# EMERGENCY FALLBACK STRATEGIES
# ════════════════════════════════════════════════════════════════════════════

def apply_emergency_overflow_fix(content: dict) -> dict:
    """
    Apply aggressive content trimming as last resort to prevent overflow.

    Strategies applied in order:
      1. Trim bullets to max 3 per section
      2. Trim sections to max 4
      3. Trim key_points to max 2
      4. Trim statistics to max 2
      5. Truncate title to 50 chars

    Args:
        content: Phase 1 content dict (modified in-place copy)

    Returns:
        trimmed content dict
    """
    import copy
    c = copy.deepcopy(content)

    # 1. Trim bullets
    for sec in c.get("sections", []):
        if len(sec.get("content", [])) > 3:
            sec["content"] = sec["content"][:3]

    # 2. Trim sections
    if len(c.get("sections", [])) > 4:
        c["sections"] = c["sections"][:4]

    # 3. Trim key_points
    if len(c.get("key_points", [])) > 2:
        c["key_points"] = c["key_points"][:2]

    # 4. Trim stats
    if len(c.get("statistics", [])) > 2:
        c["statistics"] = c["statistics"][:2]

    # 5. Truncate title
    title = c.get("title", "")
    if len(title) > 50:
        c["title"] = title[:47] + "…"

    return c


# ════════════════════════════════════════════════════════════════════════════
# OVERFLOW REPORT
# ════════════════════════════════════════════════════════════════════════════

def generate_overflow_report(content: dict,
                              canvas_h: int = SAFE_HEIGHT) -> dict:
    """
    Analyse content and return overflow risk assessment.

    Returns:
        dict with keys:
          overflow_risk   : "low" | "medium" | "high"
          pages_needed    : estimated page count
          sections_count  : number of sections
          has_stats       : bool
          has_kp          : bool
          recommendations : list of suggestion strings
    """
    sections   = content.get("sections", [])
    statistics = content.get("statistics", [])
    kp         = content.get("key_points", [])

    n_sec  = len(sections)
    n_bull = max((len(s.get("content",[])) for s in sections), default=0)

    pages = compute_pages_needed(
        sections, statistics, kp
    )

    recommendations = []
    if n_sec > 5:
        recommendations.append(f"Reduce sections from {n_sec} to 4-5 for single page")
    if n_bull > 4:
        recommendations.append(f"Reduce bullets to 3-4 per section")
    if len(statistics) > 3:
        recommendations.append("Use max 3 statistics")
    if pages > 1:
        recommendations.append(f"Content will generate a {pages}-page carousel")

    density = n_sec * n_bull
    if density <= 16:
        risk = "low"
    elif density <= 24:
        risk = "medium"
    else:
        risk = "high"

    return {
        "overflow_risk":    risk,
        "pages_needed":     pages,
        "sections_count":   n_sec,
        "avg_bullets":      n_bull,
        "has_stats":        bool(statistics),
        "has_key_points":   bool(kp),
        "recommendations":  recommendations,
    }
