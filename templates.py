"""
templates.py
============
Linkphobot - Phase 3: Fixed Template Renderer
Template System - Business / Educational / Technical

Each template defines:
  - color palette
  - typography scale
  - layout geometry
  - card style
  - spacing overrides
  - visual personality
"""

from dataclasses import dataclass, field
from typing import Tuple

# ── Type aliases ──────────────────────────────────────────────────────────
Color = Tuple[int,int,int]        # RGB
ColorA= Tuple[int,int,int,int]    # RGBA


def hex_to_rgb(h: str) -> Color:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))


def hex_to_rgba(h: str, alpha: int = 255) -> ColorA:
    r,g,b = hex_to_rgb(h)
    return (r,g,b,alpha)


# ════════════════════════════════════════════════════════════════════════════
# TEMPLATE DATACLASS
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class InfographicTemplate:
    name:        str
    description: str

    # Canvas
    canvas_w:    int = 1080
    canvas_h:    int = 1350
    margin:      int = 54

    # Color palette (hex strings)
    bg_color:         str = "#FAFBFF"
    primary:          str = "#1E3A5F"
    secondary:        str = "#2E6DA4"
    accent:           str = "#FF6B35"
    card_bg:          str = "#FFFFFF"
    card_bg_alt:      str = "#EEF4FF"
    text_primary:     str = "#1E3A5F"
    text_secondary:   str = "#4A5568"
    text_muted:       str = "#718096"
    text_on_dark:     str = "#FFFFFF"
    text_on_dark_sub: str = "#CBD5E0"
    border_color:     str = "#E2E8F0"
    stat_bg:          str = "#EEF4FF"
    dot_color:        str = "#FF6B35"
    header_gradient_start: str = "#1E3A5F"
    header_gradient_end:   str = "#2E6DA4"

    # Typography scale (font sizes in px)
    font_title:        int = 62
    font_subtitle:     int = 27
    font_section_head: int = 28
    font_bullet:       int = 21
    font_stat_value:   int = 42
    font_stat_label:   int = 17
    font_kp_item:      int = 21
    font_cta:          int = 23
    font_hashtag:      int = 18
    font_label:        int = 15

    # Font weights
    weight_title:      str = "extrabold"
    weight_subtitle:   str = "regular"
    weight_section:    str = "bold"
    weight_bullet:     str = "regular"
    weight_stat_val:   str = "extrabold"
    weight_stat_lbl:   str = "medium"
    weight_kp:         str = "semibold"
    weight_cta:        str = "semibold"
    weight_hashtag:    str = "regular"

    # Card geometry
    card_radius:       int = 16
    header_radius:     int = 20
    stat_radius:       int = 12
    accent_bar_w:      int = 5     # left accent bar on section cards
    header_bar_h:      int = 5     # top accent bar on header

    # Spacing
    block_gap:         int = 16
    section_pad_v:     int = 22
    section_pad_h:     int = 28
    header_pad_v:      int = 36
    header_pad_h:      int = 44
    stats_pad_v:       int = 24
    stats_pad_h:       int = 28
    footer_pad_v:      int = 20
    footer_pad_h:      int = 32
    bullet_gap:        int = 10
    line_spacing:      int = 6

    # Visual style flags
    dark_header:       bool = True   # header card is dark colored
    alternate_cards:   bool = True   # alternate card bg colors
    show_icons:        bool = True   # show emoji icons in section headers
    show_dots:         bool = True   # show bullet dots
    header_gradient:   bool = True   # gradient on header
    card_shadow:       bool = True   # subtle card shadow effect

    # Properties
    @property
    def content_w(self) -> int:
        return self.canvas_w - self.margin * 2

    def rgb(self, attr: str) -> Color:
        return hex_to_rgb(getattr(self, attr))

    def rgba(self, attr: str, alpha: int = 255) -> ColorA:
        return hex_to_rgba(getattr(self, attr), alpha)


# ════════════════════════════════════════════════════════════════════════════
# TEMPLATE DEFINITIONS
# ════════════════════════════════════════════════════════════════════════════

TEMPLATE_BUSINESS = InfographicTemplate(
    name        = "business",
    description = "Clean executive style — navy + orange, formal authority",

    bg_color          = "#F8FAFC",
    primary           = "#1A1F36",
    secondary         = "#2D3561",
    accent            = "#FF6B35",
    card_bg           = "#FFFFFF",
    card_bg_alt       = "#F0F4FF",
    text_primary      = "#1A1F36",
    text_secondary    = "#374151",
    text_muted        = "#6B7280",
    text_on_dark      = "#FFFFFF",
    text_on_dark_sub  = "#C8CDE8",
    border_color      = "#E5E7EB",
    stat_bg           = "#EEF2FF",
    dot_color         = "#FF6B35",
    header_gradient_start = "#1A1F36",
    header_gradient_end   = "#2D3561",

    font_title        = 60,
    font_subtitle     = 26,
    font_section_head = 27,
    font_bullet       = 20,
    font_stat_value   = 44,
    font_stat_label   = 17,
    font_kp_item      = 21,
    font_cta          = 23,
    font_hashtag      = 17,

    card_radius       = 14,
    header_radius     = 18,
    accent_bar_w      = 5,
    header_bar_h      = 0,   # no top bar, uses gradient only
    block_gap         = 14,
    dark_header       = True,
    alternate_cards   = True,
    show_icons        = True,
    show_dots         = True,
    header_gradient   = True,
    card_shadow       = True,
)

TEMPLATE_EDUCATIONAL = InfographicTemplate(
    name        = "educational",
    description = "Bright teal + warm orange, approachable learning style",

    bg_color          = "#FFF8F0",
    primary           = "#004E64",
    secondary         = "#00A5CF",
    accent            = "#F4A261",
    card_bg           = "#FFFFFF",
    card_bg_alt       = "#E0F5FA",
    text_primary      = "#004E64",
    text_secondary    = "#1A4A5A",
    text_muted        = "#5A8A96",
    text_on_dark      = "#FFFFFF",
    text_on_dark_sub  = "#B0D8E0",
    border_color      = "#B3E5F0",
    stat_bg           = "#E0F5FA",
    dot_color         = "#F4A261",
    header_gradient_start = "#004E64",
    header_gradient_end   = "#00A5CF",

    font_title        = 58,
    font_subtitle     = 25,
    font_section_head = 26,
    font_bullet       = 21,
    font_stat_value   = 42,
    font_stat_label   = 17,
    font_kp_item      = 21,
    font_cta          = 22,
    font_hashtag      = 17,

    card_radius       = 18,
    header_radius     = 22,
    accent_bar_w      = 6,
    header_bar_h      = 6,
    block_gap         = 16,
    dark_header       = True,
    alternate_cards   = True,
    show_icons        = True,
    show_dots         = True,
    header_gradient   = True,
    card_shadow       = False,
)

TEMPLATE_TECHNICAL = InfographicTemplate(
    name        = "technical",
    description = "Dark background, purple + cyan, developer/AI aesthetic",

    bg_color          = "#0D0D1A",
    primary           = "#6C3FC5",
    secondary         = "#9B72E8",
    accent            = "#00D4FF",
    card_bg           = "#16162A",
    card_bg_alt       = "#1E1E35",
    text_primary      = "#FFFFFF",
    text_secondary    = "#B0B0C8",
    text_muted        = "#6B6B85",
    text_on_dark      = "#FFFFFF",
    text_on_dark_sub  = "#B0B0C8",
    border_color      = "#2D2D45",
    stat_bg           = "#1E1E35",
    dot_color         = "#00D4FF",
    header_gradient_start = "#6C3FC5",
    header_gradient_end   = "#1A0A35",

    font_title        = 58,
    font_subtitle     = 24,
    font_section_head = 26,
    font_bullet       = 20,
    font_stat_value   = 44,
    font_stat_label   = 16,
    font_kp_item      = 20,
    font_cta          = 22,
    font_hashtag      = 17,

    card_radius       = 14,
    header_radius     = 16,
    accent_bar_w      = 4,
    header_bar_h      = 4,
    block_gap         = 14,
    dark_header       = False,  # header same dark bg as canvas
    alternate_cards   = True,
    show_icons        = True,
    show_dots         = True,
    header_gradient   = True,
    card_shadow       = False,
)

# ── Theme → template mapping (from Phase 1/2 color_theme values) ──────────
THEME_TO_TEMPLATE = {
    "tech_purple":      TEMPLATE_TECHNICAL,
    "dev_dark":         TEMPLATE_TECHNICAL,
    "cyber_dark":       TEMPLATE_TECHNICAL,
    "data_indigo":      TEMPLATE_TECHNICAL,
    "engineering_navy": TEMPLATE_BUSINESS,
    "finance_navy":     TEMPLATE_BUSINESS,
    "executive_navy":   TEMPLATE_BUSINESS,
    "clean_blue":       TEMPLATE_BUSINESS,
    "professional":     TEMPLATE_BUSINESS,
    "people_warm":      TEMPLATE_EDUCATIONAL,
    "health_blue":      TEMPLATE_EDUCATIONAL,
    "eco_green":        TEMPLATE_EDUCATIONAL,
    "edu_teal":         TEMPLATE_EDUCATIONAL,
    "creative_coral":   TEMPLATE_EDUCATIONAL,
}

TEMPLATE_REGISTRY = {
    "business":    TEMPLATE_BUSINESS,
    "educational": TEMPLATE_EDUCATIONAL,
    "technical":   TEMPLATE_TECHNICAL,
}


def get_template(name_or_theme: str) -> InfographicTemplate:
    """
    Return template by name ('business','educational','technical')
    or by Phase 1/2 color_theme value (auto-maps).
    """
    t = (TEMPLATE_REGISTRY.get(name_or_theme)
         or THEME_TO_TEMPLATE.get(name_or_theme)
         or TEMPLATE_BUSINESS)
    return t
