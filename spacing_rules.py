"""
spacing_rules.py
================
Linkphobot - Phase 2: JSON Structure Generator
Spacing Rules & Layout Measurement System

Defines all spacing constants, dynamic section height calculators,
and the vertical flow engine that stacks blocks top-to-bottom.
"""

from dataclasses import dataclass


# ════════════════════════════════════════════════════════════════════════════
# GLOBAL SPACING CONSTANTS  (all in pixels, 1080x1350 canvas)
# ════════════════════════════════════════════════════════════════════════════

# Canvas margins
MARGIN_LEFT   = 54
MARGIN_RIGHT  = 54
MARGIN_TOP    = 54
MARGIN_BOTTOM = 54
CONTENT_WIDTH = 1080 - MARGIN_LEFT - MARGIN_RIGHT   # 972px

# Block-level vertical gaps (space between blocks)
GAP_AFTER_HEADER      = 20
GAP_BETWEEN_SECTIONS  = 14
GAP_BEFORE_STATS      = 20
GAP_BEFORE_KEYPOINTS  = 16
GAP_BEFORE_FOOTER     = 20

# ── Header block ─────────────────────────────────────────────────────────
HEADER_PADDING_TOP    = 36
HEADER_PADDING_BOTTOM = 28
HEADER_PADDING_H      = 40   # horizontal padding inside header card
HEADER_ACCENT_BAR_H   = 5    # top accent bar height
HEADER_TITLE_FONT     = 64
HEADER_SUBTITLE_FONT  = 28
HEADER_TITLE_LINE_H   = 1.15
HEADER_SUBTITLE_LINE_H= 1.3
HEADER_GAP_TITLE_SUB  = 14   # gap between title and subtitle

# ── Section block ─────────────────────────────────────────────────────────
SECTION_PADDING_TOP    = 22
SECTION_PADDING_BOTTOM = 22
SECTION_PADDING_H      = 28
SECTION_CORNER_RADIUS  = 16
SECTION_ACCENT_BAR_W   = 5   # left accent bar width
SECTION_HEADING_FONT   = 30
SECTION_HEADING_LINE_H = 1.2
SECTION_GAP_HEAD_BULL  = 14  # gap between heading row and first bullet
SECTION_BULLET_FONT    = 22
SECTION_BULLET_LINE_H  = 1.35
SECTION_BULLET_GAP     = 10  # gap between bullets
SECTION_DOT_SIZE       = 8
SECTION_DOT_OFFSET_X   = 0   # dot x relative to section left padding
SECTION_ICON_SIZE      = 36
SECTION_ICON_GAP       = 12  # gap between icon and heading text

# ── Stats block ───────────────────────────────────────────────────────────
STATS_PADDING_TOP     = 24
STATS_PADDING_BOTTOM  = 24
STATS_PADDING_H       = 28
STATS_CORNER_RADIUS   = 16
STATS_HEADING_FONT    = 26
STATS_HEADING_GAP     = 16
STATS_ITEM_CORNER     = 12
STATS_ITEM_PADDING_V  = 16
STATS_ITEM_PADDING_H  = 20
STATS_VALUE_FONT      = 44
STATS_LABEL_FONT      = 18
STATS_ITEM_GAP        = 12   # horizontal gap between stat cards
STATS_MIN_ITEM_HEIGHT = 100

# ── Key points block ──────────────────────────────────────────────────────
KP_PADDING_TOP    = 22
KP_PADDING_BOTTOM = 22
KP_PADDING_H      = 28
KP_CORNER_RADIUS  = 16
KP_HEADING_FONT   = 26
KP_HEADING_GAP    = 14
KP_ITEM_FONT      = 22
KP_ITEM_LINE_H    = 1.3
KP_ITEM_GAP       = 10
KP_BULLET_SIZE    = 10
KP_BULLET_GAP     = 14

# ── Footer block ──────────────────────────────────────────────────────────
FOOTER_PADDING_TOP    = 20
FOOTER_PADDING_BOTTOM = 20
FOOTER_PADDING_H      = 28
FOOTER_CORNER_RADIUS  = 16
FOOTER_CTA_FONT       = 24
FOOTER_HASHTAG_FONT   = 20
FOOTER_DIVIDER_H      = 2
FOOTER_DIVIDER_GAP    = 14

# ── Typography fonts ──────────────────────────────────────────────────────
FONT_DISPLAY = "Inter"      # titles, headings
FONT_BODY    = "Inter"      # body, bullets, captions
FONT_MONO    = "JetBrains Mono"  # stats, numbers


# ════════════════════════════════════════════════════════════════════════════
# HEIGHT ESTIMATORS
# Each function returns estimated pixel height for that block type,
# given variable content (number of bullets, text length, etc.)
# ════════════════════════════════════════════════════════════════════════════

def _text_height(text: str, font_size: int, line_height: float,
                 available_width: int, chars_per_line_ref: int = 45) -> int:
    """
    Estimate rendered height of a text string.
    Uses character-count heuristic adjusted for font size.
    """
    if not text:
        return 0
    # Adjust chars per line based on font size (smaller font = more chars per line)
    scale = 32 / max(font_size, 1)
    cpl   = max(10, int(chars_per_line_ref * scale * (available_width / 900)))
    lines = max(1, -(-len(text) // cpl))  # ceiling division
    return int(lines * font_size * line_height)


def estimate_header_height(title: str, subtitle: str) -> int:
    """Estimate header block height in pixels."""
    inner_w = CONTENT_WIDTH - HEADER_PADDING_H * 2

    title_h    = _text_height(title,    HEADER_TITLE_FONT,    HEADER_TITLE_LINE_H,    inner_w, 20)
    subtitle_h = _text_height(subtitle, HEADER_SUBTITLE_FONT, HEADER_SUBTITLE_LINE_H, inner_w, 38)

    total = (
        HEADER_ACCENT_BAR_H
        + HEADER_PADDING_TOP
        + title_h
        + HEADER_GAP_TITLE_SUB
        + subtitle_h
        + HEADER_PADDING_BOTTOM
    )
    return max(total, 180)


def estimate_section_height(heading: str, bullets: list) -> int:
    """Estimate a single section card height in pixels."""
    inner_w = CONTENT_WIDTH - SECTION_PADDING_H * 2 - SECTION_ACCENT_BAR_W - 10

    heading_h = _text_height(heading, SECTION_HEADING_FONT, SECTION_HEADING_LINE_H, inner_w, 30)

    bullet_h = 0
    for bullet in bullets:
        bh = _text_height(bullet, SECTION_BULLET_FONT, SECTION_BULLET_LINE_H,
                          inner_w - SECTION_DOT_SIZE - 16, 42)
        bullet_h += bh + SECTION_BULLET_GAP
    if bullets:
        bullet_h -= SECTION_BULLET_GAP  # remove last gap

    total = (
        SECTION_PADDING_TOP
        + max(heading_h, SECTION_ICON_SIZE)
        + SECTION_GAP_HEAD_BULL
        + bullet_h
        + SECTION_PADDING_BOTTOM
    )
    return max(total, 100)


def estimate_stats_height(stat_count: int) -> int:
    """Estimate stats block height in pixels."""
    heading_h   = STATS_HEADING_FONT + STATS_HEADING_GAP
    item_height = STATS_MIN_ITEM_HEIGHT
    total = (
        STATS_PADDING_TOP
        + heading_h
        + item_height
        + STATS_PADDING_BOTTOM
    )
    return max(total, 160)


def estimate_keypoints_height(points: list) -> int:
    """Estimate key points block height in pixels."""
    inner_w  = CONTENT_WIDTH - KP_PADDING_H * 2 - KP_BULLET_SIZE - KP_BULLET_GAP
    heading_h = KP_HEADING_FONT + KP_HEADING_GAP

    items_h = 0
    for pt in points:
        ph = _text_height(pt, KP_ITEM_FONT, KP_ITEM_LINE_H, inner_w, 42)
        items_h += ph + KP_ITEM_GAP
    if points:
        items_h -= KP_ITEM_GAP

    total = (
        KP_PADDING_TOP
        + heading_h
        + items_h
        + KP_PADDING_BOTTOM
    )
    return max(total, 100)


def estimate_footer_height(cta: str, hashtags: list) -> int:
    """Estimate footer block height in pixels."""
    inner_w  = CONTENT_WIDTH - FOOTER_PADDING_H * 2
    cta_h    = _text_height(cta, FOOTER_CTA_FONT, 1.3, inner_w, 40)
    tags_str = "  ".join(hashtags[:6])
    tags_h   = _text_height(tags_str, FOOTER_HASHTAG_FONT, 1.4, inner_w, 50)

    total = (
        FOOTER_PADDING_TOP
        + cta_h
        + FOOTER_DIVIDER_GAP
        + FOOTER_DIVIDER_H
        + FOOTER_DIVIDER_GAP
        + tags_h
        + FOOTER_PADDING_BOTTOM
    )
    return max(total, 100)


# ════════════════════════════════════════════════════════════════════════════
# VERTICAL FLOW ENGINE
# Stacks blocks and returns a dict of {block_name: y_start}
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class BlockHeights:
    header:     int = 0
    sections:   list = None   # list of int, one per section
    stats:      int = 0
    key_points: int = 0
    footer:     int = 0

    def __post_init__(self):
        if self.sections is None:
            self.sections = []


def compute_vertical_flow(heights: BlockHeights,
                           has_stats: bool,
                           has_key_points: bool,
                           canvas_height: int = 1350,
                           margin_top: int = MARGIN_TOP,
                           margin_bottom: int = MARGIN_BOTTOM) -> dict:
    """
    Stack all blocks top-to-bottom with defined gaps.

    Returns:
        dict with keys: header_y, section_y (list), stats_y,
                        key_points_y, footer_y, total_height, overflow
    """
    cursor = margin_top
    result = {}

    # Header
    result["header_y"] = cursor
    cursor += heights.header + GAP_AFTER_HEADER

    # Sections
    result["section_y"] = []
    for i, sh in enumerate(heights.sections):
        result["section_y"].append(cursor)
        cursor += sh
        if i < len(heights.sections) - 1:
            cursor += GAP_BETWEEN_SECTIONS

    # Stats
    if has_stats and heights.stats > 0:
        cursor += GAP_BEFORE_STATS
        result["stats_y"] = cursor
        cursor += heights.stats
    else:
        result["stats_y"] = None

    # Key points
    if has_key_points and heights.key_points > 0:
        cursor += GAP_BEFORE_KEYPOINTS
        result["key_points_y"] = cursor
        cursor += heights.key_points
    else:
        result["key_points_y"] = None

    # Footer
    cursor += GAP_BEFORE_FOOTER
    result["footer_y"] = cursor
    cursor += heights.footer + margin_bottom

    result["total_height"] = cursor
    result["overflow"]     = cursor > canvas_height

    return result


# ════════════════════════════════════════════════════════════════════════════
# SECTION COMPRESSION  –  fit all sections into available space
# ════════════════════════════════════════════════════════════════════════════

def compress_sections_to_fit(section_heights: list,
                              available_height: int,
                              min_section_height: int = 90) -> list:
    """
    If total section height exceeds available space, proportionally
    compress section heights. Each section gets at least min_section_height.

    Args:
        section_heights  : list of estimated section heights
        available_height : total pixels available for all sections
        min_section_height: floor for any single section

    Returns:
        list of adjusted heights
    """
    total = sum(section_heights)
    if total <= available_height:
        return section_heights

    scale  = available_height / total
    result = []
    for h in section_heights:
        new_h = max(min_section_height, int(h * scale))
        result.append(new_h)
    return result


# ════════════════════════════════════════════════════════════════════════════
# STAT CARD LAYOUT  –  horizontal distribution of stat cards
# ════════════════════════════════════════════════════════════════════════════

def compute_stat_card_rects(stat_count: int,
                             block_x: int,
                             block_width: int,
                             item_height: int,
                             padding_h: int = STATS_PADDING_H,
                             item_gap: int  = STATS_ITEM_GAP) -> list:
    """
    Compute x, width for each stat card in a horizontal row.

    Returns:
        list of (x, width) tuples
    """
    if stat_count == 0:
        return []

    inner_w    = block_width - padding_h * 2
    total_gaps = item_gap * (stat_count - 1)
    item_w     = (inner_w - total_gaps) // stat_count

    rects = []
    x = block_x + padding_h
    for _ in range(stat_count):
        rects.append((x, item_w))
        x += item_w + item_gap
    return rects
