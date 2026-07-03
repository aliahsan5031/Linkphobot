"""
renderer.py
===========
Linkphobot - Phase 3: Fixed Template Renderer
Core Drawing Primitives

Low-level drawing functions used by all higher-level renderers.
All functions operate on a PIL ImageDraw context.

Functions:
  draw_title()
  draw_card()
  draw_icon()
  draw_text_block()
  draw_gradient_rect()
  draw_rounded_rect()
  draw_divider()
  draw_bullet_dot()
  draw_accent_bar()
  draw_stat_card()
  draw_badge()
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from font_loader import get_font, wrap_text, measure_text
from templates import InfographicTemplate, hex_to_rgb, hex_to_rgba
from typing import Tuple, Optional, List

Color  = Tuple[int,int,int]
ColorA = Tuple[int,int,int,int]


# ════════════════════════════════════════════════════════════════════════════
# GRADIENT HELPERS
# ════════════════════════════════════════════════════════════════════════════

def draw_gradient_rect(img: Image.Image,
                       x: int, y: int, w: int, h: int,
                       color_start: str, color_end: str,
                       direction: str = "vertical",
                       radius: int = 0) -> None:
    """
    Draw a smooth linear gradient rectangle on img.

    Args:
        direction: "vertical" | "horizontal" | "diagonal"
        radius:    corner radius (applied via mask)
    """
    r1,g1,b1 = hex_to_rgb(color_start)
    r2,g2,b2 = hex_to_rgb(color_end)

    # Build gradient on a small strip then resize
    if direction == "horizontal":
        grad = Image.new("RGB", (w, 1))
        for i in range(w):
            t   = i / max(w-1, 1)
            col = (int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))
            grad.putpixel((i,0), col)
        grad = grad.resize((w, h), Image.NEAREST)
    elif direction == "diagonal":
        grad = Image.new("RGB", (w, h))
        for j in range(h):
            for i in range(w):
                t   = (i/max(w-1,1) + j/max(h-1,1)) / 2
                col = (int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))
                grad.putpixel((i,j), col)
    else:  # vertical
        grad = Image.new("RGB", (1, h))
        for j in range(h):
            t   = j / max(h-1, 1)
            col = (int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))
            grad.putpixel((0,j), col)
        grad = grad.resize((w, h), Image.NEAREST)

    if radius > 0:
        # Create rounded mask
        mask = Image.new("L", (w, h), 0)
        md   = ImageDraw.Draw(mask)
        md.rounded_rectangle([0,0,w-1,h-1], radius=radius, fill=255)
        img.paste(grad, (x, y), mask)
    else:
        img.paste(grad, (x, y))


# ════════════════════════════════════════════════════════════════════════════
# ROUNDED RECTANGLE
# ════════════════════════════════════════════════════════════════════════════

def draw_rounded_rect(draw: ImageDraw.ImageDraw,
                      x: int, y: int, w: int, h: int,
                      radius: int, fill: Optional[Color] = None,
                      outline: Optional[Color] = None,
                      outline_width: int = 1) -> None:
    """Draw a rounded rectangle with optional fill and outline."""
    coords = [x, y, x+w-1, y+h-1]
    if fill:
        draw.rounded_rectangle(coords, radius=radius, fill=fill)
    if outline:
        draw.rounded_rectangle(coords, radius=radius, outline=outline,
                                width=outline_width)


# ════════════════════════════════════════════════════════════════════════════
# CARD SHADOW
# ════════════════════════════════════════════════════════════════════════════

def draw_card_shadow(img: Image.Image,
                     x: int, y: int, w: int, h: int,
                     radius: int = 14, shadow_offset: int = 4,
                     shadow_blur: int = 8,
                     shadow_color: Tuple = (0,0,0,40)) -> None:
    """Draw a soft drop shadow under a card."""
    sx, sy  = x + shadow_offset, y + shadow_offset
    shadow  = Image.new("RGBA", img.size, (0,0,0,0))
    sd      = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([sx, sy, sx+w-1, sy+h-1],
                          radius=radius, fill=shadow_color)
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
    img.paste(shadow, (0,0), shadow)


# ════════════════════════════════════════════════════════════════════════════
# CORE DRAW FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def draw_card(img: Image.Image,
              x: int, y: int, w: int, h: int,
              fill_color: str,
              radius: int = 14,
              border_color: Optional[str] = None,
              border_width: int = 1,
              shadow: bool = False,
              gradient: bool = False,
              gradient_end: Optional[str] = None,
              gradient_dir: str = "vertical") -> None:
    """
    Draw a card (rounded rectangle) on img.

    Args:
        img         : PIL Image to draw on
        x,y,w,h     : position and size
        fill_color  : hex color string
        radius      : corner radius
        border_color: optional hex border color
        border_width: border thickness
        shadow      : draw soft drop shadow
        gradient    : use gradient fill
        gradient_end: end color for gradient
        gradient_dir: gradient direction
    """
    draw = ImageDraw.Draw(img)

    if shadow:
        draw_card_shadow(img, x, y, w, h, radius)

    if gradient and gradient_end:
        draw_gradient_rect(img, x, y, w, h, fill_color, gradient_end,
                           gradient_dir, radius)
    else:
        rgb = hex_to_rgb(fill_color)
        draw_rounded_rect(draw, x, y, w, h, radius, fill=rgb)

    if border_color:
        draw = ImageDraw.Draw(img)
        rgb  = hex_to_rgb(border_color)
        draw_rounded_rect(draw, x, y, w, h, radius, outline=rgb,
                          outline_width=border_width)


def draw_title(draw: ImageDraw.ImageDraw,
               text: str,
               x: int, y: int, max_w: int,
               font_size: int,
               color: str,
               weight: str = "extrabold",
               align: str = "center",
               line_spacing: int = 8) -> int:
    """
    Draw wrapped title text. Returns total height used.

    Args:
        draw        : ImageDraw context
        text        : text string
        x,y         : top-left origin
        max_w       : max width for wrapping
        font_size   : pixel size
        color       : hex color
        weight      : font weight string
        align       : "left" | "center" | "right"
        line_spacing: extra px between lines

    Returns:
        total pixel height of drawn text
    """
    font  = get_font(weight, font_size)
    lines = wrap_text(text, font, max_w)
    rgb   = hex_to_rgb(color)
    _, lh = measure_text("Ag", font)
    step  = lh + line_spacing
    cy    = y

    for line in lines:
        lw, _ = measure_text(line, font)
        if align == "center":
            lx = x + (max_w - lw) // 2
        elif align == "right":
            lx = x + max_w - lw
        else:
            lx = x
        draw.text((lx, cy), line, font=font, fill=rgb)
        cy += step

    return cy - y


def draw_text_block(draw: ImageDraw.ImageDraw,
                    text: str,
                    x: int, y: int, max_w: int,
                    font_size: int,
                    color: str,
                    weight: str = "regular",
                    align: str = "left",
                    line_spacing: int = 6,
                    max_lines: int = 99) -> int:
    """
    Draw a wrapped multi-line text block. Returns total height used.
    """
    font  = get_font(weight, font_size)
    lines = wrap_text(text, font, max_w)[:max_lines]
    rgb   = hex_to_rgb(color)
    _, lh = measure_text("Ag", font)
    step  = lh + line_spacing
    cy    = y

    for line in lines:
        lw, _ = measure_text(line, font)
        if align == "center":
            lx = x + (max_w - lw) // 2
        elif align == "right":
            lx = x + max_w - lw
        else:
            lx = x
        draw.text((lx, cy), line, font=font, fill=rgb)
        cy += step

    return cy - y


def draw_icon(draw: ImageDraw.ImageDraw,
              emoji: str,
              x: int, y: int,
              size: int = 32,
              color: Optional[str] = None) -> None:
    """
    Draw an emoji icon at position (x, y).

    Args:
        draw  : ImageDraw context
        emoji : emoji character string
        x, y  : top-left position
        size  : font size for the emoji
        color : optional hex override (most emojis ignore color)
    """
    font = get_font("regular", size)
    rgb  = hex_to_rgb(color) if color else (80, 80, 80)
    try:
        draw.text((x, y), emoji, font=font, fill=rgb, embedded_color=True)
    except TypeError:
        draw.text((x, y), emoji, font=font, fill=rgb)


def draw_bullet_dot(draw: ImageDraw.ImageDraw,
                    cx: int, cy: int,
                    radius: int = 4,
                    color: str = "#FF6B35") -> None:
    """Draw a filled circle bullet dot."""
    rgb = hex_to_rgb(color)
    draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=rgb)


def draw_accent_bar(draw: ImageDraw.ImageDraw,
                    x: int, y: int,
                    w: int, h: int,
                    color: str,
                    radius: int = 3) -> None:
    """Draw a thin accent bar (left-side or top)."""
    rgb = hex_to_rgb(color)
    draw_rounded_rect(draw, x, y, w, h, radius, fill=rgb)


def draw_divider(draw: ImageDraw.ImageDraw,
                 x: int, y: int, w: int,
                 color: str = "#E2E8F0",
                 thickness: int = 2) -> None:
    """Draw a horizontal divider line."""
    rgb = hex_to_rgb(color)
    draw.rectangle([x, y, x+w, y+thickness], fill=rgb)


def draw_stat_card(img: Image.Image,
                   x: int, y: int, w: int, h: int,
                   value: str, label: str,
                   tmpl: "InfographicTemplate") -> None:
    """
    Draw a complete stat card with value + label.

    Args:
        img         : PIL Image to draw on
        x,y,w,h     : card position + size
        value       : large number/stat string (e.g. "$4.5B", "73%")
        label       : descriptive label below the value
        tmpl        : active InfographicTemplate
    """
    draw = ImageDraw.Draw(img)

    # Card background
    draw_card(img, x, y, w, h,
              fill_color=tmpl.stat_bg,
              radius=tmpl.stat_radius,
              shadow=False)

    # Top accent line
    draw_accent_bar(draw, x, y, w, 3, tmpl.accent, radius=2)

    pad   = 16
    inner_w = w - pad*2
    cy    = y + pad + 4

    # Value
    val_font = get_font(tmpl.weight_stat_val, tmpl.font_stat_value)
    vw, vh   = measure_text(value, val_font)
    vx       = x + (w - vw) // 2
    draw.text((vx, cy), value, font=val_font, fill=hex_to_rgb(tmpl.accent))
    cy += vh + 8

    # Label (wrapped)
    lbl_font  = get_font(tmpl.weight_stat_lbl, tmpl.font_stat_label)
    lbl_lines = wrap_text(label, lbl_font, inner_w)
    _, llh    = measure_text("Ag", lbl_font)
    for lline in lbl_lines[:3]:
        lw2, _ = measure_text(lline, lbl_font)
        draw.text((x + (w-lw2)//2, cy), lline, font=lbl_font,
                  fill=hex_to_rgb(tmpl.text_secondary))
        cy += llh + 4


def draw_badge(draw: ImageDraw.ImageDraw,
               x: int, y: int,
               text: str,
               bg_color: str,
               text_color: str,
               font_size: int = 15,
               pad_h: int = 12,
               pad_v: int = 6,
               radius: int = 20) -> Tuple[int,int]:
    """
    Draw a pill-shaped badge. Returns (width, height).
    """
    font    = get_font("semibold", font_size)
    tw, th  = measure_text(text, font)
    bw      = tw + pad_h*2
    bh      = th + pad_v*2
    rgb_bg  = hex_to_rgb(bg_color)
    rgb_txt = hex_to_rgb(text_color)
    draw_rounded_rect(draw, x, y, bw, bh, radius, fill=rgb_bg)
    draw.text((x+pad_h, y+pad_v), text, font=font, fill=rgb_txt)
    return bw, bh
