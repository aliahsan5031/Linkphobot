"""
hierarchy_engine.py
===================
Linkphobot - Phase 2: JSON Structure Generator
Visual Hierarchy & Typography Engine

Responsibilities:
- Assign correct TypographyStyle to every text element
- Manage z-index layering for all elements
- Determine element priority ordering
- Apply alignment rules per block type
- Scale font sizes based on content density
- Manage color assignments from theme
"""

from layout_schema import (
    TypographyStyle, COLOR_THEMES,
    CANVAS_WIDTH, CANVAS_HEIGHT, CONTENT_WIDTH
)
from spacing_rules import (
    FONT_DISPLAY, FONT_BODY, FONT_MONO,
    HEADER_TITLE_FONT, HEADER_SUBTITLE_FONT,
    SECTION_HEADING_FONT, SECTION_BULLET_FONT,
    STATS_VALUE_FONT, STATS_LABEL_FONT, STATS_HEADING_FONT,
    KP_ITEM_FONT, KP_HEADING_FONT,
    FOOTER_CTA_FONT, FOOTER_HASHTAG_FONT,
)


# ════════════════════════════════════════════════════════════════════════════
# Z-INDEX LAYER SYSTEM
# ════════════════════════════════════════════════════════════════════════════

class ZIndex:
    CANVAS_BG        = 0
    BLOCK_BG         = 1
    ACCENT_BAR       = 2
    BLOCK_CONTENT    = 3
    ICON             = 4
    TEXT             = 5
    STAT_VALUE       = 6
    HIGHLIGHT        = 7


# ════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY FACTORY
# Builds TypographyStyle for each element type
# ════════════════════════════════════════════════════════════════════════════

def get_typography(element_type: str,
                   color_theme: str,
                   section_count: int = 4,
                   bullet_count: int = 4) -> TypographyStyle:
    """
    Return the correct TypographyStyle for a given element type and theme.

    Font sizes are slightly reduced when content density is high
    (many sections with many bullets) to prevent overflow.

    Args:
        element_type  : one of the defined element type strings
        color_theme   : theme name key
        section_count : number of sections (used for density scaling)
        bullet_count  : max bullets per section (used for density scaling)

    Returns:
        TypographyStyle instance
    """
    # Density scaling factor: reduce fonts slightly if very dense
    density = section_count * bullet_count
    scale   = 1.0 if density <= 20 else (0.93 if density <= 28 else 0.87)

    def sz(base: int) -> int:
        return max(14, int(base * scale))

    styles = {
        # ── Header ─────────────────────────────────────────────────────
        "title": TypographyStyle(
            font_family="Inter", font_size=sz(HEADER_TITLE_FONT),
            font_weight="800", line_height=1.15, letter_spacing=-1.5,
            color_key="text_primary", uppercase=False,
        ),
        "subtitle": TypographyStyle(
            font_family="Inter", font_size=sz(HEADER_SUBTITLE_FONT),
            font_weight="400", line_height=1.35, letter_spacing=0.0,
            color_key="text_secondary",
        ),
        # ── Section ────────────────────────────────────────────────────
        "section_heading": TypographyStyle(
            font_family="Inter", font_size=sz(SECTION_HEADING_FONT),
            font_weight="700", line_height=1.2, letter_spacing=-0.3,
            color_key="text_primary",
        ),
        "bullet": TypographyStyle(
            font_family="Inter", font_size=sz(SECTION_BULLET_FONT),
            font_weight="400", line_height=1.38, letter_spacing=0.0,
            color_key="text_secondary",
        ),
        # ── Statistics ─────────────────────────────────────────────────
        "stat_heading": TypographyStyle(
            font_family="Inter", font_size=sz(STATS_HEADING_FONT),
            font_weight="700", line_height=1.2, letter_spacing=0.0,
            color_key="text_primary",
        ),
        "stat_value": TypographyStyle(
            font_family="Inter", font_size=sz(STATS_VALUE_FONT),
            font_weight="800", line_height=1.1, letter_spacing=-1.0,
            color_key="accent",
        ),
        "stat_label": TypographyStyle(
            font_family="Inter", font_size=sz(STATS_LABEL_FONT),
            font_weight="500", line_height=1.3, letter_spacing=0.0,
            color_key="text_secondary",
        ),
        # ── Key Points ─────────────────────────────────────────────────
        "kp_heading": TypographyStyle(
            font_family="Inter", font_size=sz(KP_HEADING_FONT),
            font_weight="700", line_height=1.2, letter_spacing=0.0,
            color_key="text_primary",
        ),
        "kp_item": TypographyStyle(
            font_family="Inter", font_size=sz(KP_ITEM_FONT),
            font_weight="500", line_height=1.35, letter_spacing=0.0,
            color_key="text_primary",
        ),
        # ── Footer ─────────────────────────────────────────────────────
        "cta": TypographyStyle(
            font_family="Inter", font_size=sz(FOOTER_CTA_FONT),
            font_weight="600", line_height=1.35, letter_spacing=0.0,
            color_key="text_primary",
        ),
        "hashtag": TypographyStyle(
            font_family="Inter", font_size=sz(FOOTER_HASHTAG_FONT),
            font_weight="400", line_height=1.4, letter_spacing=0.0,
            color_key="secondary",
        ),
        # ── Labels ─────────────────────────────────────────────────────
        "label": TypographyStyle(
            font_family="Inter", font_size=sz(18),
            font_weight="600", line_height=1.2, letter_spacing=1.0,
            color_key="accent", uppercase=True,
        ),
        "caption": TypographyStyle(
            font_family="Inter", font_size=sz(16),
            font_weight="400", line_height=1.4, letter_spacing=0.0,
            color_key="text_muted",
        ),
    }

    return styles.get(element_type, styles["bullet"])


# ════════════════════════════════════════════════════════════════════════════
# ALIGNMENT RULES
# ════════════════════════════════════════════════════════════════════════════

ALIGNMENT_MAP = {
    "title":           "center",
    "subtitle":        "center",
    "section_heading": "left",
    "bullet":          "left",
    "stat_value":      "center",
    "stat_label":      "center",
    "stat_heading":    "center",
    "kp_heading":      "left",
    "kp_item":         "left",
    "cta":             "center",
    "hashtag":         "center",
    "label":           "left",
    "caption":         "left",
}

def get_alignment(element_type: str) -> str:
    return ALIGNMENT_MAP.get(element_type, "left")


# ════════════════════════════════════════════════════════════════════════════
# COLOR RESOLVER
# ════════════════════════════════════════════════════════════════════════════

def get_color(color_key: str, theme: str) -> str:
    """
    Resolve a color key to a hex value for the given theme.

    Args:
        color_key : key from the ColorTheme dict (e.g. "primary", "accent")
        theme     : theme name string

    Returns:
        hex color string e.g. "#6C3FC5"
    """
    palette = COLOR_THEMES.get(theme, COLOR_THEMES["professional"])
    return palette.get(color_key, "#333333")


def get_theme_colors(theme: str) -> dict:
    """Return the full color dict for a theme."""
    return COLOR_THEMES.get(theme, COLOR_THEMES["professional"]).copy()


# ════════════════════════════════════════════════════════════════════════════
# BLOCK PRIORITY & INCLUSION RULES
# ════════════════════════════════════════════════════════════════════════════

def should_include_stats(statistics: list) -> bool:
    """Include stats block only if there is meaningful stat data."""
    return len(statistics) >= 1 and any(s.get("value") for s in statistics)


def should_include_keypoints(key_points: list) -> bool:
    """Include key points block only if there are points."""
    return len(key_points) >= 1


def get_block_order(content_type: str) -> list:
    """
    Return the preferred block rendering order for a content type.

    Returns:
        list of block type strings in top-to-bottom order
    """
    orders = {
        "educational": ["header", "sections", "stats",  "key_points", "footer"],
        "how-to":      ["header", "sections", "key_points", "footer"],
        "statistics":  ["header", "stats", "sections",  "key_points", "footer"],
        "framework":   ["header", "sections", "key_points", "footer"],
        "comparison":  ["header", "sections", "stats",  "footer"],
        "listicle":    ["header", "sections", "key_points", "footer"],
    }
    return orders.get(content_type, orders["educational"])


# ════════════════════════════════════════════════════════════════════════════
# SECTION ALTERNATING STYLE
# Alternate card style between sections for visual rhythm
# ════════════════════════════════════════════════════════════════════════════

def get_section_card_style(section_index: int, theme: str) -> dict:
    """
    Return card style config for a section.
    Alternates between solid fill and border-only cards.

    Returns:
        dict with keys: bg_color_key, use_gradient, accent_side, border_width
    """
    if section_index % 2 == 0:
        return {
            "bg_color_key": "card_bg",
            "use_gradient": False,
            "accent_side":  True,
            "border_width": 1,
        }
    else:
        return {
            "bg_color_key": "stat_bg",
            "use_gradient": False,
            "accent_side":  True,
            "border_width": 0,
        }


# ════════════════════════════════════════════════════════════════════════════
# FONT SIZE SCALING  –  adaptive scaling for long titles
# ════════════════════════════════════════════════════════════════════════════

def scale_title_font(title: str, base_size: int = HEADER_TITLE_FONT) -> int:
    """
    Reduce title font size for longer titles to prevent overflow.

    Args:
        title     : title string
        base_size : base font size

    Returns:
        adjusted font size
    """
    length = len(title)
    if length <= 20:
        return base_size
    elif length <= 32:
        return max(48, int(base_size * 0.88))
    elif length <= 44:
        return max(42, int(base_size * 0.78))
    else:
        return max(36, int(base_size * 0.68))


def scale_section_heading_font(heading: str,
                                base_size: int = SECTION_HEADING_FONT) -> int:
    """Scale section heading font for long headings."""
    length = len(heading)
    if length <= 20:
        return base_size
    elif length <= 32:
        return max(22, int(base_size * 0.88))
    else:
        return max(20, int(base_size * 0.80))
