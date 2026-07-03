"""
layout_schema.py
================
Linkphobot - Phase 2: JSON Structure Generator
Layout Schema & Data Models

Defines every data structure used in the infographic layout system.
All coordinates are in pixels on a 1080x1350 canvas.

Coordinate system:
  - Origin (0,0) at TOP-LEFT
  - X increases right
  - Y increases down
  - All values in integer pixels
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


# ════════════════════════════════════════════════════════════════════════════
# CANVAS CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

CANVAS_WIDTH  = 1080
CANVAS_HEIGHT = 1350
CANVAS_RATIO  = "4:5"

MARGIN_LEFT   = 54
MARGIN_RIGHT  = 54
MARGIN_TOP    = 54
MARGIN_BOTTOM = 54

CONTENT_WIDTH  = CANVAS_WIDTH  - MARGIN_LEFT - MARGIN_RIGHT   # 972px
CONTENT_HEIGHT = CANVAS_HEIGHT - MARGIN_TOP  - MARGIN_BOTTOM  # 1242px


# ════════════════════════════════════════════════════════════════════════════
# COLOR THEME PALETTES
# ════════════════════════════════════════════════════════════════════════════

COLOR_THEMES = {
    "tech_purple":      {"primary":"#6C3FC5","secondary":"#9B72E8","accent":"#00D4FF","background":"#0D0D1A","surface":"#1A1A2E","text_primary":"#FFFFFF","text_secondary":"#B0B0C8","text_muted":"#6B6B85","border":"#2D2D45","card_bg":"#16162A","stat_bg":"#1E1E35","gradient_start":"#6C3FC5","gradient_end":"#00D4FF"},
    "dev_dark":         {"primary":"#89B4FA","secondary":"#CBA6F7","accent":"#A6E3A1","background":"#11111B","surface":"#1E1E2E","text_primary":"#CDD6F4","text_secondary":"#BAC2DE","text_muted":"#6C7086","border":"#313244","card_bg":"#181825","stat_bg":"#1E1E2E","gradient_start":"#89B4FA","gradient_end":"#CBA6F7"},
    "finance_navy":     {"primary":"#0A2342","secondary":"#1B4F72","accent":"#F7C948","background":"#F8F9FA","surface":"#FFFFFF","text_primary":"#0A2342","text_secondary":"#2C3E50","text_muted":"#7F8C8D","border":"#D5E8F0","card_bg":"#FFFFFF","stat_bg":"#EBF5FB","gradient_start":"#0A2342","gradient_end":"#1B4F72"},
    "health_blue":      {"primary":"#0077B6","secondary":"#00B4D8","accent":"#F4A261","background":"#FFFFFF","surface":"#F0F8FF","text_primary":"#03045E","text_secondary":"#0077B6","text_muted":"#90E0EF","border":"#CAF0F8","card_bg":"#F0F8FF","stat_bg":"#E0F7FF","gradient_start":"#0077B6","gradient_end":"#00B4D8"},
    "eco_green":        {"primary":"#1B4332","secondary":"#2D6A4F","accent":"#95D5B2","background":"#F0FFF4","surface":"#FFFFFF","text_primary":"#1B4332","text_secondary":"#2D6A4F","text_muted":"#74C69D","border":"#B7E4C7","card_bg":"#FFFFFF","stat_bg":"#D8F3DC","gradient_start":"#1B4332","gradient_end":"#74C69D"},
    "executive_navy":   {"primary":"#1A1F36","secondary":"#2D3561","accent":"#FF6B35","background":"#FAFBFF","surface":"#FFFFFF","text_primary":"#1A1F36","text_secondary":"#2D3561","text_muted":"#8892B0","border":"#E2E8F0","card_bg":"#FFFFFF","stat_bg":"#EEF2FF","gradient_start":"#1A1F36","gradient_end":"#FF6B35"},
    "creative_coral":   {"primary":"#FF4E50","secondary":"#FC6767","accent":"#F9D423","background":"#FFFBF0","surface":"#FFFFFF","text_primary":"#1A0A00","text_secondary":"#FF4E50","text_muted":"#A0522D","border":"#FFE4CC","card_bg":"#FFFFFF","stat_bg":"#FFF3E0","gradient_start":"#FF4E50","gradient_end":"#F9D423"},
    "engineering_navy": {"primary":"#0A192F","secondary":"#172A45","accent":"#64FFDA","background":"#F5F5F5","surface":"#FFFFFF","text_primary":"#0A192F","text_secondary":"#172A45","text_muted":"#8892B0","border":"#CCD6F6","card_bg":"#FFFFFF","stat_bg":"#E8F4FD","gradient_start":"#0A192F","gradient_end":"#64FFDA"},
    "data_indigo":      {"primary":"#3C1053","secondary":"#7B2D8B","accent":"#FFB347","background":"#FAF8FF","surface":"#FFFFFF","text_primary":"#3C1053","text_secondary":"#7B2D8B","text_muted":"#9B59B6","border":"#E8D5F5","card_bg":"#FFFFFF","stat_bg":"#F3E5F5","gradient_start":"#3C1053","gradient_end":"#FFB347"},
    "clean_blue":       {"primary":"#2563EB","secondary":"#1D4ED8","accent":"#FBBF24","background":"#F8FAFC","surface":"#FFFFFF","text_primary":"#0F172A","text_secondary":"#1E40AF","text_muted":"#64748B","border":"#DBEAFE","card_bg":"#FFFFFF","stat_bg":"#EFF6FF","gradient_start":"#2563EB","gradient_end":"#FBBF24"},
    "edu_teal":         {"primary":"#004E64","secondary":"#00A5CF","accent":"#F4A261","background":"#FFF8F0","surface":"#FFFFFF","text_primary":"#004E64","text_secondary":"#00A5CF","text_muted":"#7ABFCC","border":"#B3E5F0","card_bg":"#FFFFFF","stat_bg":"#E0F5FA","gradient_start":"#004E64","gradient_end":"#F4A261"},
    "people_warm":      {"primary":"#B5451B","secondary":"#E07B39","accent":"#FFD166","background":"#FFFAF5","surface":"#FFFFFF","text_primary":"#3D1A00","text_secondary":"#B5451B","text_muted":"#C4845A","border":"#FFD9B3","card_bg":"#FFFFFF","stat_bg":"#FFF0E0","gradient_start":"#B5451B","gradient_end":"#FFD166"},
    "cyber_dark":       {"primary":"#0D0D0D","secondary":"#1A1A2E","accent":"#00FF41","background":"#0A0A0A","surface":"#111111","text_primary":"#00FF41","text_secondary":"#CCCCCC","text_muted":"#555555","border":"#1E1E1E","card_bg":"#111111","stat_bg":"#0D1A0D","gradient_start":"#0D0D0D","gradient_end":"#00FF41"},
    "professional":     {"primary":"#1E3A5F","secondary":"#2E6DA4","accent":"#FF6B35","background":"#FAFBFF","surface":"#FFFFFF","text_primary":"#1E3A5F","text_secondary":"#2E6DA4","text_muted":"#6B7280","border":"#E5EAF0","card_bg":"#FFFFFF","stat_bg":"#EEF4FF","gradient_start":"#1E3A5F","gradient_end":"#FF6B35"},
}


# ════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY SCALE
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class TypographyStyle:
    font_family:    str
    font_size:      int
    font_weight:    str
    line_height:    float
    letter_spacing: float
    color_key:      str
    uppercase:      bool = False
    italic:         bool = False


# ════════════════════════════════════════════════════════════════════════════
# POSITION & DIMENSION
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class Rect:
    x:      int
    y:      int
    width:  int
    height: int

    @property
    def right(self)    -> int: return self.x + self.width
    @property
    def bottom(self)   -> int: return self.y + self.height
    @property
    def center_x(self) -> int: return self.x + self.width  // 2
    @property
    def center_y(self) -> int: return self.y + self.height // 2

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class Padding:
    top: int; right: int; bottom: int; left: int
    def to_dict(self) -> dict:
        return {"top": self.top, "right": self.right, "bottom": self.bottom, "left": self.left}


# ════════════════════════════════════════════════════════════════════════════
# ELEMENT NODES
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class TextElement:
    element_id:     str
    element_type:   str
    text:           str
    rect:           Rect
    typography:     TypographyStyle
    z_index:        int   = 1
    opacity:        float = 1.0
    align:          str   = "left"
    max_lines:      int   = 10
    color_override: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["rect"]       = self.rect.to_dict()
        d["typography"] = asdict(self.typography)
        return d


@dataclass
class ShapeElement:
    element_id:            str
    element_type:          str
    rect:                  Rect
    color_key:             str
    corner_radius:         int   = 0
    border_width:          int   = 0
    border_color_key:      str   = "border"
    opacity:               float = 1.0
    z_index:               int   = 0
    gradient:              bool  = False
    gradient_direction:    str   = "vertical"
    color_override:        Optional[str] = None
    border_color_override: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["rect"] = self.rect.to_dict()
        return d


@dataclass
class IconElement:
    element_id:     str
    element_type:   str   = "icon"
    emoji:          str   = ""
    icon_name:      str   = ""
    rect:           Rect  = field(default_factory=lambda: Rect(0, 0, 40, 40))
    font_size:      int   = 32
    z_index:        int   = 2
    color_key:      str   = "accent"
    color_override: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["rect"] = self.rect.to_dict()
        return d


# ════════════════════════════════════════════════════════════════════════════
# LAYOUT BLOCKS
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class HeaderBlock:
    block_id:         str  = "header"
    block_type:       str  = "header"
    rect:             Rect = field(default_factory=lambda: Rect(0,0,0,0))
    background:       Optional[ShapeElement] = None
    accent_bar:       Optional[ShapeElement] = None
    title_element:    Optional[TextElement]  = None
    subtitle_element: Optional[TextElement]  = None
    icon_element:     Optional[IconElement]  = None
    z_index:          int  = 1

    def to_dict(self) -> dict:
        return {"block_id": self.block_id, "block_type": self.block_type,
                "rect": self.rect.to_dict(), "z_index": self.z_index,
                "background":       self.background.to_dict()       if self.background       else None,
                "accent_bar":       self.accent_bar.to_dict()       if self.accent_bar       else None,
                "title_element":    self.title_element.to_dict()    if self.title_element    else None,
                "subtitle_element": self.subtitle_element.to_dict() if self.subtitle_element else None,
                "icon_element":     self.icon_element.to_dict()     if self.icon_element     else None}


@dataclass
class BulletItem:
    item_id:      str
    text:         str
    rect:         Rect
    text_element: Optional[TextElement]  = None
    dot_element:  Optional[ShapeElement] = None

    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "text": self.text, "rect": self.rect.to_dict(),
                "text_element": self.text_element.to_dict() if self.text_element else None,
                "dot_element":  self.dot_element.to_dict()  if self.dot_element  else None}


@dataclass
class SectionBlock:
    block_id:        str  = "section_0"
    block_type:      str  = "section"
    section_index:   int  = 0
    heading:         str  = ""
    icon_emoji:      str  = ""
    rect:            Rect = field(default_factory=lambda: Rect(0,0,0,0))
    background:      Optional[ShapeElement] = None
    accent_bar:      Optional[ShapeElement] = None
    heading_element: Optional[TextElement]  = None
    icon_element:    Optional[IconElement]  = None
    bullet_items:    list = field(default_factory=list)
    z_index:         int  = 1

    def to_dict(self) -> dict:
        return {"block_id": self.block_id, "block_type": self.block_type,
                "section_index": self.section_index, "heading": self.heading,
                "icon_emoji": self.icon_emoji, "rect": self.rect.to_dict(), "z_index": self.z_index,
                "background":      self.background.to_dict()      if self.background      else None,
                "accent_bar":      self.accent_bar.to_dict()      if self.accent_bar      else None,
                "heading_element": self.heading_element.to_dict() if self.heading_element else None,
                "icon_element":    self.icon_element.to_dict()    if self.icon_element    else None,
                "bullet_items":    [b.to_dict() for b in self.bullet_items]}


@dataclass
class StatItem:
    item_id:       str
    value:         str
    label:         str
    context:       str
    rect:          Rect
    background:    Optional[ShapeElement] = None
    value_element: Optional[TextElement]  = None
    label_element: Optional[TextElement]  = None

    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "value": self.value, "label": self.label,
                "context": self.context, "rect": self.rect.to_dict(),
                "background":    self.background.to_dict()    if self.background    else None,
                "value_element": self.value_element.to_dict() if self.value_element else None,
                "label_element": self.label_element.to_dict() if self.label_element else None}


@dataclass
class StatsBlock:
    block_id:   str  = "stats"
    block_type: str  = "stats"
    rect:       Rect = field(default_factory=lambda: Rect(0,0,0,0))
    background: Optional[ShapeElement] = None
    heading:    Optional[TextElement]  = None
    stat_items: list = field(default_factory=list)
    z_index:    int  = 1

    def to_dict(self) -> dict:
        return {"block_id": self.block_id, "block_type": self.block_type,
                "rect": self.rect.to_dict(), "z_index": self.z_index,
                "background": self.background.to_dict() if self.background else None,
                "heading":    self.heading.to_dict()    if self.heading    else None,
                "stat_items": [s.to_dict() for s in self.stat_items]}


@dataclass
class KeyPointsBlock:
    block_id:    str  = "key_points"
    block_type:  str  = "key_points"
    rect:        Rect = field(default_factory=lambda: Rect(0,0,0,0))
    background:  Optional[ShapeElement] = None
    heading:     Optional[TextElement]  = None
    point_items: list = field(default_factory=list)
    z_index:     int  = 1

    def to_dict(self) -> dict:
        return {"block_id": self.block_id, "block_type": self.block_type,
                "rect": self.rect.to_dict(), "z_index": self.z_index,
                "background":  self.background.to_dict() if self.background else None,
                "heading":     self.heading.to_dict()    if self.heading    else None,
                "point_items": [p.to_dict() for p in self.point_items]}


@dataclass
class FooterBlock:
    block_id:        str  = "footer"
    block_type:      str  = "footer"
    rect:            Rect = field(default_factory=lambda: Rect(0,0,0,0))
    background:      Optional[ShapeElement] = None
    cta_element:     Optional[TextElement]  = None
    hashtag_element: Optional[TextElement]  = None
    divider:         Optional[ShapeElement] = None
    z_index:         int  = 1

    def to_dict(self) -> dict:
        return {"block_id": self.block_id, "block_type": self.block_type,
                "rect": self.rect.to_dict(), "z_index": self.z_index,
                "background":      self.background.to_dict()      if self.background      else None,
                "cta_element":     self.cta_element.to_dict()     if self.cta_element     else None,
                "hashtag_element": self.hashtag_element.to_dict() if self.hashtag_element else None,
                "divider":         self.divider.to_dict()         if self.divider         else None}


# ════════════════════════════════════════════════════════════════════════════
# ROOT LAYOUT OBJECT
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class InfographicLayout:
    layout_id:        str
    canvas_width:     int
    canvas_height:    int
    color_theme:      str
    colors:           dict
    topic:            str
    title:            str
    content_type:     str
    generated_at:     str
    canvas_background:  Optional[ShapeElement] = None
    header_block:       Optional[HeaderBlock]  = None
    section_blocks:     list = field(default_factory=list)
    stats_block:        Optional[StatsBlock]      = None
    key_points_block:   Optional[KeyPointsBlock]  = None
    footer_block:       Optional[FooterBlock]     = None
    total_blocks:       int  = 0
    total_elements:     int  = 0
    layout_height_used: int  = 0
    overflow:           bool = False

    def to_dict(self) -> dict:
        return {
            "layout_id": self.layout_id, "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height, "color_theme": self.color_theme,
            "colors": self.colors, "topic": self.topic, "title": self.title,
            "content_type": self.content_type, "generated_at": self.generated_at,
            "canvas_background": self.canvas_background.to_dict() if self.canvas_background else None,
            "header_block":      self.header_block.to_dict()      if self.header_block      else None,
            "section_blocks":    [s.to_dict() for s in self.section_blocks],
            "stats_block":       self.stats_block.to_dict()       if self.stats_block       else None,
            "key_points_block":  self.key_points_block.to_dict()  if self.key_points_block  else None,
            "footer_block":      self.footer_block.to_dict()      if self.footer_block      else None,
            "meta": {"total_blocks": self.total_blocks, "total_elements": self.total_elements,
                     "layout_height_used": self.layout_height_used, "overflow": self.overflow}}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
