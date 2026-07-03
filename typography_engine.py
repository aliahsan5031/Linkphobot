"""
typography_engine.py
====================
Linkphobot - Phase 4: Typography Scaling Engine
Master Orchestrator

Single entry point that integrates:
  - text_measurement.py   : pixel-accurate measurement
  - multiline_wrapping.py : smart word wrapping
  - font_scaling.py       : dynamic size resolution
  - overflow_handler.py   : overflow detection & prevention

Public API:
  TypographyEngine          : main class
  TypographySpec            : resolved spec for one text element
  resolve_all()             : resolve full infographic typography
  fit_text()                : fit text into a box
  draw_fitted_text()        : measure + wrap + draw in one call
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from text_measurement import (
    measure_text, measure_line_height, fits_in_box,
    count_lines_needed, char_density_ratio,
)
from multiline_wrapping import (
    wrap_text, wrap_title, wrap_bullet,
    wrap_and_truncate, wrapped_block_height,
    draw_wrapped_text,
)
from font_scaling import (
    get_base_size, get_density_scale,
    scale_title, scale_subtitle, scale_section_heading,
    scale_bullet_font, scale_stat_value,
    scale_font_to_fit_box, scale_font_for_lines,
    resolve_typography, _load_font,
    BASE_SCALE, SIZE_CLAMPS,
)
from overflow_handler import (
    detect_text_overflow, detect_layout_overflow,
    overflow_amount, fit_text_to_box,
    truncate_bullets_to_fit, redistribute_heights,
    split_sections_into_pages, generate_overflow_report,
    apply_emergency_overflow_fix,
)


# ════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY SPEC  –  resolved spec for a single text element
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class TypographySpec:
    """Resolved typography parameters for one text element."""
    element_type:  str
    text:          str
    font:          object                  # PIL ImageFont
    font_size:     int
    font_weight:   str
    color:         str                     # hex string
    align:         str                     # "left" | "center" | "right"
    max_width:     int
    max_height:    int
    line_spacing:  int = 6
    lines:         List[str] = field(default_factory=list)
    rendered_h:    int = 0
    overflows:     bool = False

    def total_height(self) -> int:
        """Return rendered pixel height."""
        return self.rendered_h

    def __repr__(self):
        return (f"TypographySpec({self.element_type!r}, "
                f"size={self.font_size}, lines={len(self.lines)}, "
                f"h={self.rendered_h}px, overflow={self.overflows})")


# ════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY ENGINE  –  main class
# ════════════════════════════════════════════════════════════════════════════

class TypographyEngine:
    """
    Phase 4 Typography Engine.

    Resolves fonts, wraps text, detects overflow, and draws
    text elements onto PIL images with correct sizing.

    Usage:
        engine = TypographyEngine(content_dict)
        spec   = engine.resolve("title")
        engine.draw(draw_ctx, spec, x=54, y=100)
    """

    ELEMENT_COLORS = {
        # element_type -> color_theme_key (resolved at draw time via template)
        "title":        "text_on_dark",
        "subtitle":     "text_on_dark_sub",
        "section_head": "text_primary",
        "bullet":       "text_secondary",
        "stat_value":   "accent",
        "stat_label":   "text_secondary",
        "key_point":    "text_on_dark",
        "cta":          "text_primary",
        "hashtag":      "secondary",
        "caption":      "text_muted",
        "label":        "accent",
        "badge":        "text_on_dark",
    }

    ELEMENT_ALIGN = {
        "title":        "center",
        "subtitle":     "center",
        "section_head": "left",
        "bullet":       "left",
        "stat_value":   "center",
        "stat_label":   "center",
        "key_point":    "left",
        "cta":          "center",
        "hashtag":      "center",
        "caption":      "left",
        "label":        "left",
        "badge":        "center",
    }

    def __init__(self,
                 content: Optional[dict] = None,
                 canvas_width: int = 1080,
                 margin: int = 54,
                 line_spacing: int = 6):
        """
        Initialise the engine with optional content for global resolution.

        Args:
            content      : Phase 1 content dict (optional)
            canvas_width : canvas pixel width
            margin       : left/right margin
            line_spacing : default line spacing
        """
        self.content       = content or {}
        self.canvas_width  = canvas_width
        self.margin        = margin
        self.content_width = canvas_width - margin * 2
        self.line_spacing  = line_spacing
        self._resolved     = {}    # cache: element_type -> {"size","weight"}
        self._fonts        = {}    # cache: (weight, size) -> font

    # ── Font caching ──────────────────────────────────────────────────
    def _font(self, weight: str, size: int) -> ImageFont.FreeTypeFont:
        key = (weight, size)
        if key not in self._fonts:
            self._fonts[key] = _load_font(weight, size)
        return self._fonts[key]

    # ── Resolve global typography ──────────────────────────────────────
    def resolve_all(self) -> Dict[str, dict]:
        """
        Resolve font sizes for all element types from content.
        Results are cached inside the engine instance.

        Returns:
            dict of {element_type: {"size": int, "weight": str}}
        """
        if not self._resolved:
            self._resolved = resolve_typography(
                self.content, self.canvas_width, self.margin
            )
        return self._resolved

    def get_size(self, element_type: str) -> Tuple[int, str]:
        """
        Return (font_size, font_weight) for an element type.
        Triggers global resolution if not already done.
        """
        resolved = self.resolve_all()
        spec     = resolved.get(element_type, {
            "size":   get_base_size(element_type),
            "weight": "regular",
        })
        return spec["size"], spec["weight"]

    # ── Resolve single element ─────────────────────────────────────────
    def resolve(self,
                element_type: str,
                text: str,
                max_width: int,
                max_height: int = 9999,
                color: str = "#333333",
                force_size: Optional[int] = None,
                force_weight: Optional[str] = None) -> TypographySpec:
        """
        Resolve a complete TypographySpec for one text element.

        Will auto-shrink font if text overflows the box.

        Args:
            element_type : type key (e.g. "title", "bullet")
            text         : text string
            max_width    : available pixel width
            max_height   : available pixel height
            color        : hex color for rendering
            force_size   : override resolved font size
            force_weight : override resolved font weight

        Returns:
            TypographySpec with all fields populated
        """
        size, weight = self.get_size(element_type)
        if force_size   is not None: size   = force_size
        if force_weight is not None: weight = force_weight

        align = self.ELEMENT_ALIGN.get(element_type, "left")

        # Check if text fits; if not, scale down
        font = self._font(weight, size)
        h    = wrapped_block_height(text, font, max_width, self.line_spacing)

        if h > max_height and max_height < 9999:
            # Scale down to fit
            font, size = scale_font_to_fit_box(
                text, weight, max_width, max_height,
                size, min_size=10, line_spacing=self.line_spacing
            )

        # Wrap text
        lines = wrap_text(text, font, max_width)
        lh    = measure_line_height(font)
        rendered_h = len(lines) * (lh + self.line_spacing) - self.line_spacing
        overflows  = rendered_h > max_height and max_height < 9999

        return TypographySpec(
            element_type  = element_type,
            text          = text,
            font          = font,
            font_size     = size,
            font_weight   = weight,
            color         = color,
            align         = align,
            max_width     = max_width,
            max_height    = max_height,
            line_spacing  = self.line_spacing,
            lines         = lines,
            rendered_h    = rendered_h,
            overflows      = overflows,
        )

    # ── Draw from spec ─────────────────────────────────────────────────
    def draw(self,
             draw: ImageDraw.ImageDraw,
             spec: TypographySpec,
             x: int,
             y: int) -> int:
        """
        Draw a resolved TypographySpec onto a PIL ImageDraw context.

        Args:
            draw : PIL ImageDraw object
            spec : resolved TypographySpec
            x, y : top-left drawing origin

        Returns:
            total pixel height consumed
        """
        from templates import hex_to_rgb
        rgb  = hex_to_rgb(spec.color)
        font = spec.font
        lh   = measure_line_height(font)
        step = lh + spec.line_spacing
        cy   = y

        for line in spec.lines:
            from text_measurement import text_width as tw
            lw = tw(line, font)
            if spec.align == "center":
                lx = x + (spec.max_width - lw) // 2
            elif spec.align == "right":
                lx = x + spec.max_width - lw
            else:
                lx = x
            draw.text((lx, cy), line, font=font, fill=rgb)
            cy += step

        return cy - y

    # ── Convenience: measure + wrap + draw in one call ─────────────────
    def draw_text(self,
                  draw: ImageDraw.ImageDraw,
                  element_type: str,
                  text: str,
                  x: int, y: int,
                  max_width: int,
                  color: str,
                  max_height: int = 9999,
                  align: Optional[str] = None) -> int:
        """
        Resolve, wrap, and draw text in a single call.

        Returns:
            total pixel height consumed
        """
        spec = self.resolve(element_type, text, max_width,
                            max_height, color)
        if align:
            spec.align = align
        return self.draw(draw, spec, x, y)

    # ── Overflow report ────────────────────────────────────────────────
    def overflow_report(self) -> dict:
        """Return overflow risk assessment for loaded content."""
        return generate_overflow_report(self.content)

    # ── Emergency trim ─────────────────────────────────────────────────
    def trim_for_single_page(self) -> dict:
        """
        Return a trimmed version of content suitable for single-page render.
        """
        return apply_emergency_overflow_fix(self.content)


# ════════════════════════════════════════════════════════════════════════════
# STANDALONE HELPERS  –  use without instantiating the class
# ════════════════════════════════════════════════════════════════════════════

def fit_text(text: str,
             element_type: str,
             box_width: int,
             box_height: int,
             line_spacing: int = 6) -> TypographySpec:
    """
    Fit any text into a pixel box, returning a ready TypographySpec.
    No content context needed.

    Example:
        spec = fit_text("AI in Healthcare", "title", 900, 200)
        engine.draw(draw_ctx, spec, x=54, y=60)
    """
    engine = TypographyEngine()
    return engine.resolve(element_type, text, box_width,
                          box_height, "#333333")


def draw_fitted_text(draw: ImageDraw.ImageDraw,
                     text: str,
                     element_type: str,
                     x: int, y: int,
                     max_width: int,
                     color: str,
                     max_height: int = 9999,
                     line_spacing: int = 6) -> int:
    """
    One-liner: resolve typography + draw text.

    Returns:
        pixel height consumed

    Example:
        h = draw_fitted_text(draw, "My Title", "title",
                             x=54, y=80, max_width=900, color="#FFFFFF")
    """
    engine = TypographyEngine(line_spacing=line_spacing)
    spec   = engine.resolve(element_type, text, max_width,
                            max_height, color)
    return engine.draw(draw, spec, x, y)
