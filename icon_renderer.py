"""
icon_renderer.py
================
Linkphobot - Phase 3: Fixed Template Renderer
Icon & Visual Element Rendering System

Functions:
  draw_icon_circle()    : emoji in a colored circle badge
  draw_number_badge()   : numbered step circle
  draw_checkmark()      : tick mark icon
  draw_arrow()          : directional arrow
  draw_progress_bar()   : horizontal progress indicator
  draw_sparkline()      : mini bar chart for stats
  draw_brand_strip()    : bottom branding strip
  draw_section_number() : large section number
  draw_tag_row()        : row of hashtag pills
"""

from PIL import Image, ImageDraw
from font_loader import get_font, measure_text, wrap_text
from templates import InfographicTemplate, hex_to_rgb
from renderer import draw_rounded_rect, draw_bullet_dot


# ════════════════════════════════════════════════════════════════════════════
# ICON CIRCLE  –  emoji inside a colored circle
# ════════════════════════════════════════════════════════════════════════════

def draw_icon_circle(draw: ImageDraw.ImageDraw,
                     cx: int, cy: int,
                     emoji: str,
                     circle_color: str,
                     size: int = 48) -> None:
    """
    Draw an emoji inside a filled circle.

    Args:
        draw         : ImageDraw context
        cx, cy       : center of circle
        emoji        : emoji character
        circle_color : hex fill color for circle
        size         : diameter of circle
    """
    r   = size // 2
    rgb = hex_to_rgb(circle_color)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=rgb)

    font    = get_font("regular", size - 14)
    ew, eh  = measure_text(emoji, font)
    ex      = cx - ew // 2
    ey      = cy - eh // 2
    try:
        draw.text((ex, ey), emoji, font=font, fill=(255,255,255,255),
                  embedded_color=True)
    except TypeError:
        draw.text((ex, ey), emoji, font=font, fill=(255,255,255))


# ════════════════════════════════════════════════════════════════════════════
# NUMBER BADGE  –  step circle with number
# ════════════════════════════════════════════════════════════════════════════

def draw_number_badge(draw: ImageDraw.ImageDraw,
                      cx: int, cy: int,
                      number: int,
                      bg_color: str,
                      text_color: str,
                      size: int = 36) -> None:
    """
    Draw a filled circle with a number inside (for step-by-step content).
    """
    r    = size // 2
    rgb  = hex_to_rgb(bg_color)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=rgb)

    font    = get_font("bold", size - 12)
    txt     = str(number)
    tw, th  = measure_text(txt, font)
    draw.text((cx-tw//2, cy-th//2), txt,
              font=font, fill=hex_to_rgb(text_color))


# ════════════════════════════════════════════════════════════════════════════
# PROGRESS BAR
# ════════════════════════════════════════════════════════════════════════════

def draw_progress_bar(draw: ImageDraw.ImageDraw,
                      x: int, y: int, w: int, h: int,
                      percent: float,
                      bg_color: str,
                      fill_color: str,
                      radius: int = 4) -> None:
    """
    Draw a horizontal progress bar.

    Args:
        percent: 0.0 – 1.0
    """
    pct = max(0.0, min(1.0, percent))
    bg  = hex_to_rgb(bg_color)
    fg  = hex_to_rgb(fill_color)
    draw_rounded_rect(draw, x, y, w, h, radius, fill=bg)
    if pct > 0:
        fw = max(h, int(w * pct))
        draw_rounded_rect(draw, x, y, fw, h, radius, fill=fg)


# ════════════════════════════════════════════════════════════════════════════
# SPARKLINE  –  mini bar chart
# ════════════════════════════════════════════════════════════════════════════

def draw_sparkline(draw: ImageDraw.ImageDraw,
                   x: int, y: int, w: int, h: int,
                   values: list,
                   bar_color: str,
                   bg_color: str = "#E5EAF0") -> None:
    """
    Draw a mini bar chart (sparkline) from a list of numeric values.
    """
    if not values:
        return
    bg  = hex_to_rgb(bg_color)
    fg  = hex_to_rgb(bar_color)
    draw.rectangle([x, y, x+w, y+h], fill=bg)

    n       = len(values)
    max_v   = max(values) or 1
    bar_w   = max(2, (w - (n-1)*2) // n)
    bx      = x
    for v in values:
        bh = int((v / max_v) * h)
        if bh > 0:
            draw.rectangle([bx, y+h-bh, bx+bar_w, y+h], fill=fg)
        bx += bar_w + 2


# ════════════════════════════════════════════════════════════════════════════
# BRAND STRIP  –  bottom watermark / branding bar
# ════════════════════════════════════════════════════════════════════════════

def draw_brand_strip(draw: ImageDraw.ImageDraw,
                     x: int, y: int, w: int,
                     brand_text: str = "Made with Linkphobot",
                     tmpl: "InfographicTemplate" = None) -> int:
    """
    Draw a small branding strip. Returns height used.
    """
    font    = get_font("regular", 14)
    tw, th  = measure_text(brand_text, font)
    color   = tmpl.text_muted if tmpl else "#999999"
    draw.text((x + (w-tw)//2, y), brand_text,
              font=font, fill=hex_to_rgb(color))
    return th + 4


# ════════════════════════════════════════════════════════════════════════════
# SECTION NUMBER  –  large decorative number
# ════════════════════════════════════════════════════════════════════════════

def draw_section_number(draw: ImageDraw.ImageDraw,
                        x: int, y: int,
                        number: int,
                        color: str,
                        size: int = 80,
                        alpha_hex: str = "18") -> None:
    """
    Draw a large decorative section number (low opacity, background element).
    """
    font    = get_font("black", size)
    txt     = str(number).zfill(2)
    # Parse color and make it semi-transparent looking by blending with white
    r,g,b   = hex_to_rgb(color)
    alpha   = int(alpha_hex, 16)
    blended = (
        int(r + (255-r)*(1 - alpha/255)),
        int(g + (255-g)*(1 - alpha/255)),
        int(b + (255-b)*(1 - alpha/255)),
    )
    draw.text((x, y), txt, font=font, fill=blended)


# ════════════════════════════════════════════════════════════════════════════
# TAG ROW  –  horizontal row of hashtag pills
# ════════════════════════════════════════════════════════════════════════════

def draw_tag_row(draw: ImageDraw.ImageDraw,
                 x: int, y: int, max_w: int,
                 tags: list,
                 bg_color: str,
                 text_color: str,
                 font_size: int = 15,
                 gap: int = 8,
                 pad_h: int = 10,
                 pad_v: int = 5) -> int:
    """
    Draw a row of hashtag pill badges. Wraps to next line if needed.
    Returns total height used.
    """
    font    = get_font("regular", font_size)
    bg_rgb  = hex_to_rgb(bg_color)
    txt_rgb = hex_to_rgb(text_color)

    cx  = x
    cy  = y
    _, fh = measure_text("Ag", font)
    row_h = fh + pad_v*2

    for tag in tags:
        tw, _ = measure_text(tag, font)
        pill_w = tw + pad_h*2

        if cx + pill_w > x + max_w and cx > x:
            cx  = x
            cy += row_h + gap

        draw_rounded_rect(draw, cx, cy, pill_w, row_h, 20, fill=bg_rgb)
        draw.text((cx+pad_h, cy+pad_v), tag, font=font, fill=txt_rgb)
        cx += pill_w + gap

    return (cy + row_h) - y


# ════════════════════════════════════════════════════════════════════════════
# CHECKMARK ICON  –  tick with circle
# ════════════════════════════════════════════════════════════════════════════

def draw_checkmark(draw: ImageDraw.ImageDraw,
                   cx: int, cy: int,
                   color: str,
                   size: int = 20) -> None:
    """Draw a simple checkmark tick symbol."""
    r   = size // 2
    rgb = hex_to_rgb(color)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=rgb, width=2)
    # Tick path
    lw = max(2, size//10)
    pts = [
        (cx - r//2, cy),
        (cx - r//6, cy + r//2),
        (cx + r//2, cy - r//3),
    ]
    draw.line(pts, fill=rgb, width=lw)


# ════════════════════════════════════════════════════════════════════════════
# ARROW
# ════════════════════════════════════════════════════════════════════════════

def draw_arrow(draw: ImageDraw.ImageDraw,
               x1: int, y1: int,
               x2: int, y2: int,
               color: str,
               width: int = 3) -> None:
    """Draw a simple straight arrow from (x1,y1) to (x2,y2)."""
    rgb = hex_to_rgb(color)
    draw.line([(x1,y1),(x2,y2)], fill=rgb, width=width)
    # Arrowhead (simple triangle approximation)
    import math
    angle = math.atan2(y2-y1, x2-x1)
    ah    = 12
    a1    = angle + math.pi*5/6
    a2    = angle - math.pi*5/6
    p1    = (x2 + int(ah*math.cos(a1)), y2 + int(ah*math.sin(a1)))
    p2    = (x2 + int(ah*math.cos(a2)), y2 + int(ah*math.sin(a2)))
    draw.polygon([(x2,y2), p1, p2], fill=rgb)
