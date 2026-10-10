"""Adaptive infographic renderer (Pillow only).

Every block is measured first: text is wrapped to the width it has, then the
stack is shrunk, and finally stripped of its least important blocks, until it
fits the canvas. Nothing is placed at a hard-coded y offset, so blocks cannot
overlap, and emoji (which the bundled fonts cannot draw) are replaced by
numbered badges.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .caption import normalize_hashtags
from .config import DEFAULT_BRAND, PALETTES, SIZES
from .content import validate

log = logging.getLogger("linkphobot.render")

Color = tuple[int, int, int]

MARGIN = 54
MIN_FONT_PX = 13
SCALES = (1.0, 0.94, 0.88, 0.82, 0.76)

# Each variant keeps less than the one before it. The first that fits wins.
VARIANTS = (
    {"bullets": 3, "keypoints": True, "stats": True},
    {"bullets": 3, "keypoints": False, "stats": True},
    {"bullets": 2, "keypoints": False, "stats": True},
    {"bullets": 2, "keypoints": False, "stats": False},
    {"bullets": 1, "keypoints": False, "stats": False},
)

# ------------------------------------------------------------------------ colour


def hex_to_rgb(value: str) -> Color:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _linear(channel: int) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: Color) -> float:
    r, g, b = rgb
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast(a: Color, b: Color) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def mix(a: Color, b: Color, t: float) -> Color:
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


WHITE: Color = (255, 255, 255)
BLACK: Color = (0, 0, 0)
NEAR_BLACK: Color = (17, 17, 17)


def ensure_contrast(fg: Color, bg: Color, ratio: float = 4.5) -> Color:
    """Nudge ``fg`` toward white or black until it reads against ``bg``."""
    target = WHITE if contrast(WHITE, bg) >= contrast(BLACK, bg) else BLACK
    out = fg
    for _ in range(16):
        if contrast(out, bg) >= ratio:
            return out
        out = mix(out, target, 0.12)
    return target


def darken_for_white(color: Color) -> Color:
    """Darken ``color`` until white text on it is readable (4.5:1)."""
    for _ in range(24):
        if contrast(WHITE, color) >= 4.5:
            return color
        color = mix(color, BLACK, 0.12)
    return color


def on_color(color: Color) -> Color:
    return WHITE if contrast(WHITE, color) >= contrast(NEAR_BLACK, color) else NEAR_BLACK


@dataclass(frozen=True)
class Style:
    bg: Color
    card_a: Color
    card_b: Color
    border: Color
    primary: Color
    header: Color
    accent: Color
    text: Color
    heading: Color
    on_accent: Color
    dark: bool


def make_style(theme: str) -> Style:
    bg_h, pri_h, acc_h, txt_h = PALETTES.get(theme, PALETTES["professional"])
    bg, primary, accent, text = (hex_to_rgb(c) for c in (bg_h, pri_h, acc_h, txt_h))
    dark = luminance(bg) < 0.2
    return Style(
        bg=bg,
        card_a=hex_to_rgb("#1A1A2E") if dark else WHITE,
        card_b=hex_to_rgb("#16213E") if dark else hex_to_rgb("#F0F4FF"),
        border=mix(bg, text, 0.14),
        primary=primary,
        header=darken_for_white(primary),
        accent=accent,
        text=text,
        heading=hex_to_rgb("#89B4FA") if dark else primary,
        on_accent=on_color(accent),
        dark=dark,
    )


# ------------------------------------------------------------------------- fonts

_REGULAR = (
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
)
_BOLD = (
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)


@lru_cache(maxsize=128)
def load_font(size: int, bold: bool = False):
    """Load a TrueType font at ``size`` px.

    Set LINKPHOBOT_FONT / LINKPHOBOT_FONT_BOLD to use your own font files.
    Falls back to Pillow's built-in scalable font, never to a tiny bitmap one.
    """
    custom = os.environ.get("LINKPHOBOT_FONT_BOLD" if bold else "LINKPHOBOT_FONT", "")
    for path in (custom, *(_BOLD if bold else _REGULAR)):
        if path and os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    log.warning("No system TrueType font found; using Pillow's built-in font")
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def font_size(font) -> int:
    return int(getattr(font, "size", 12))


def line_height(font) -> int:
    return round(font_size(font) * 1.3)


def text_width(font, text: str) -> float:
    return font.getlength(text)


# -------------------------------------------------------------------------- text

_EMOJI = re.compile(
    "[\U0001f000-\U0001faff\u2300-\u23ff\u2600-\u27bf\u2b00-\u2bff\ufe0f\u200d\u20e3]+"
)


def clean(text: object) -> str:
    """Strip emoji (the fonts have no glyphs for them) and collapse whitespace."""
    return re.sub(r"\s+", " ", _EMOJI.sub("", str(text or ""))).strip()


def ellipsize(text: str, font, max_w: float) -> str:
    if text_width(font, text) <= max_w:
        return text
    while text and text_width(font, text + "…") > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def wrap_text(text: str, font, max_w: float, max_lines: int) -> list[str]:
    """Greedy word wrap. Overlong words are split; overflow ends in an ellipsis."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        while len(word) > 1 and text_width(font, word) > max_w:
            k = len(word)
            while k > 1 and text_width(font, word[:k]) > max_w:
                k -= 1
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:k])
            word = word[k:]
        trial = f"{current} {word}".strip()
        if text_width(font, trial) <= max_w:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        kept = lines[:max_lines]
        kept[-1] = ellipsize(" ".join([kept[-1], *lines[max_lines:]]), font, max_w)
        return kept
    return lines


def _draw_lines(draw, lines, x, y, font, fill, align="left") -> int:
    lh = line_height(font)
    for i, line in enumerate(lines):
        px = x - text_width(font, line) / 2 if align == "center" else x
        draw.text((px, y + i * lh), line, font=font, fill=fill)
    return y + len(lines) * lh


def _draw_centered(draw, text, cx, cy, font, fill) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (left + right) / 2, cy - (top + bottom) / 2), text, font=font, fill=fill)


# ------------------------------------------------------------------------ layout


@dataclass
class Block:
    name: str
    h: int
    draw: Callable[[ImageDraw.ImageDraw, int], None]
    y: int = 0


@dataclass
class Ctx:
    width: int
    height: int
    scale: float
    style: Style
    brand: str
    card_w: int = field(init=False)

    def __post_init__(self) -> None:
        self.card_w = self.width - 2 * MARGIN

    def px(self, value: float) -> int:
        return round(value * self.scale)

    def font(self, size: float, bold: bool = False):
        return load_font(max(MIN_FONT_PX, round(size * self.scale)), bold)

    def fit(self, text: str, bold: bool, sizes, max_w: float, max_lines: int):
        """Largest size in ``sizes`` whose wrapped text fits ``max_lines``."""
        text = clean(text)
        if not text:
            return self.font(sizes[0], bold), []
        for size in sizes:
            font = self.font(size, bold)
            lines = wrap_text(text, font, max_w, 999)
            if len(lines) <= max_lines:
                return font, lines
        font = self.font(sizes[-1], bold)
        return font, wrap_text(text, font, max_w, max_lines)


def _header_block(ctx: Ctx, data: dict) -> Block:
    st, w = ctx.style, ctx.width
    badge_font = ctx.font(15, True)
    badge_text = clean(data["content_type"]).upper() or "INSIGHTS"
    badge_w = int(text_width(badge_font, badge_text)) + ctx.px(36)
    badge_h = ctx.px(34)
    title_font, title_lines = ctx.fit(data["title"], True, (52, 48, 44, 40, 36), w - 2 * MARGIN, 2)
    sub_font, sub_lines = ctx.fit(data["subtitle"], False, (24, 22, 20), w - 2 * MARGIN, 2)

    top_pad = ctx.px(40)
    title_y = top_pad + badge_h + ctx.px(22)
    sub_y = title_y + len(title_lines) * line_height(title_font) + ctx.px(12)
    h = sub_y + len(sub_lines) * line_height(sub_font) + ctx.px(34)

    def draw_header(draw: ImageDraw.ImageDraw, y: int) -> None:
        bottom = mix(st.header, BLACK, 0.22)
        for row in range(h):
            draw.line([(0, row), (w, row)], fill=mix(st.header, bottom, row / max(1, h - 1)))
        draw.rectangle([0, h - ctx.px(6), w, h], fill=st.accent)
        draw.rounded_rectangle(
            [(w - badge_w) // 2, top_pad, (w + badge_w) // 2, top_pad + badge_h],
            radius=badge_h // 2,
            fill=st.accent,
        )
        _draw_centered(draw, badge_text, w / 2, top_pad + badge_h / 2, badge_font, st.on_accent)
        _draw_lines(draw, title_lines, w / 2, title_y, title_font, WHITE, "center")
        sub_color = ensure_contrast((203, 213, 224), st.header)
        _draw_lines(draw, sub_lines, w / 2, sub_y, sub_font, sub_color, "center")

    return Block("header", h, draw_header)


def _section_block(ctx: Ctx, index: int, section: dict, max_bullets: int) -> Block:
    st = ctx.style
    pad = ctx.px(20)
    badge_d = ctx.px(40)
    text_off = pad + badge_d + ctx.px(14)
    inner_w = ctx.card_w - text_off - pad
    head_font, head_lines = ctx.fit(section["heading"], True, (26, 24, 22, 20), inner_w, 1)
    body_font = ctx.font(21)
    bullet_indent = ctx.px(20)
    bullets = [
        wrap_text(clean(b), body_font, inner_w - bullet_indent, 2)
        for b in section["content"][:max_bullets]
        if clean(b)
    ]
    gap = ctx.px(8)
    head_h = max(badge_d, len(head_lines) * line_height(head_font))
    bullets_h = sum(len(b) * line_height(body_font) for b in bullets)
    bullets_h += gap * max(0, len(bullets) - 1)
    h = pad + head_h + (ctx.px(10) if bullets else 0) + bullets_h + pad
    card = st.card_a if index % 2 == 0 else st.card_b
    heading_color = ensure_contrast(st.heading, card)
    body_color = ensure_contrast(st.text, card)

    def draw_card(draw: ImageDraw.ImageDraw, y: int) -> None:
        x0 = MARGIN
        draw.rounded_rectangle(
            [x0, y, x0 + ctx.card_w, y + h], radius=14, fill=card, outline=st.border
        )
        draw.rounded_rectangle([x0, y + 10, x0 + 7, y + h - 10], radius=4, fill=st.accent)
        cx, cy = x0 + pad + badge_d / 2, y + pad + badge_d / 2
        draw.ellipse(
            [cx - badge_d / 2, cy - badge_d / 2, cx + badge_d / 2, cy + badge_d / 2],
            fill=st.header,
        )
        _draw_centered(draw, str(index + 1), cx, cy, ctx.font(20, True), WHITE)
        text_x = x0 + text_off
        ty = y + pad + (head_h - len(head_lines) * line_height(head_font)) // 2
        ty = _draw_lines(draw, head_lines, text_x, ty, head_font, heading_color)
        ty = y + pad + head_h + ctx.px(10)
        for lines in bullets:
            dot = ctx.px(9)
            dot_y = ty + (line_height(body_font) - dot) // 2
            draw.ellipse([text_x, dot_y, text_x + dot, dot_y + dot], fill=st.accent)
            ty = _draw_lines(draw, lines, text_x + bullet_indent, ty, body_font, body_color)
            ty += gap

    return Block(f"section_{index + 1}", h, draw_card)


def _keypoints_block(ctx: Ctx, points: list[str]) -> Block:
    st = ctx.style
    pad = ctx.px(18)
    n = len(points)
    col_gap = ctx.px(20)
    col_w = (ctx.card_w - 2 * pad - col_gap * (n - 1)) / n
    font = ctx.font(18)
    indent = ctx.px(16)
    columns = [wrap_text(clean(p), font, col_w - indent, 2) for p in points]
    h = 2 * pad + max(len(c) for c in columns) * line_height(font)

    def draw_band(draw: ImageDraw.ImageDraw, y: int) -> None:
        draw.rounded_rectangle([MARGIN, y, MARGIN + ctx.card_w, y + h], radius=12, fill=st.header)
        for i, lines in enumerate(columns):
            x = MARGIN + pad + i * (col_w + col_gap)
            dot = ctx.px(8)
            dot_y = y + pad + (line_height(font) - dot) // 2
            draw.ellipse([x, dot_y, x + dot, dot_y + dot], fill=st.accent)
            _draw_lines(draw, lines, x + indent, y + pad, font, WHITE)

    return Block("key_points", h, draw_band)


def _stats_block(ctx: Ctx, stats: list[dict]) -> Block:
    st = ctx.style
    n = len(stats)
    gap = ctx.px(12)
    sw = (ctx.card_w - gap * (n - 1)) / n
    pad = ctx.px(14)
    label_font = ctx.font(17)
    cards = []
    for stat in stats:
        value_font, value_lines = ctx.fit(stat["value"], True, (34, 30, 26, 22), sw - 24, 1)
        label_lines = wrap_text(clean(stat["label"]), label_font, sw - 24, 2)
        cards.append((value_font, value_lines, label_lines))
    value_h = max(line_height(c[0]) for c in cards)
    label_h = max(len(c[2]) for c in cards) * line_height(label_font)
    h = ctx.px(5) + pad + value_h + ctx.px(4) + label_h + pad
    value_color = ensure_contrast(st.accent, st.card_b, 3.0)
    label_color = ensure_contrast(st.text, st.card_b)

    def draw_stats(draw: ImageDraw.ImageDraw, y: int) -> None:
        for i, (value_font, value_lines, label_lines) in enumerate(cards):
            x = MARGIN + i * (sw + gap)
            draw.rounded_rectangle(
                [x, y, x + sw, y + h], radius=12, fill=st.card_b, outline=st.border
            )
            draw.rounded_rectangle([x, y, x + sw, y + ctx.px(5)], radius=3, fill=st.accent)
            ty = y + ctx.px(5) + pad
            cx = x + sw / 2
            _draw_lines(draw, value_lines, cx, ty, value_font, value_color, "center")
            label_y = ty + value_h + ctx.px(4)
            _draw_lines(draw, label_lines, cx, label_y, label_font, label_color, "center")

    return Block("stats", h, draw_stats)


def _footer_block(ctx: Ctx, data: dict) -> Block:
    st, w = ctx.style, ctx.width
    cta_font, cta_lines = ctx.fit(data["call_to_action"], False, (21, 19, 17), ctx.card_w, 2)
    tags = " ".join(normalize_hashtags(data["hashtags"])[:5])
    tag_font, tag_lines = ctx.fit(tags, False, (17, 15), ctx.card_w, 1)
    brand_font, brand_lines = ctx.fit(ctx.brand, False, (15, 14), ctx.card_w, 1)

    top = ctx.px(14)
    h = (
        1
        + top
        + len(cta_lines) * line_height(cta_font)
        + (ctx.px(8) + line_height(tag_font) if tag_lines else 0)
        + ctx.px(10)
        + line_height(brand_font)
        + ctx.px(16)
    )
    cta_color = ensure_contrast(st.heading, st.bg)
    muted = ensure_contrast(mix(st.text, st.bg, 0.2), st.bg)

    def draw_footer(draw: ImageDraw.ImageDraw, y: int) -> None:
        draw.line([(MARGIN, y), (w - MARGIN, y)], fill=st.border, width=1)
        ty = y + 1 + top
        ty = _draw_lines(draw, cta_lines, w / 2, ty, cta_font, cta_color, "center")
        if tag_lines:
            ty = _draw_lines(draw, tag_lines, w / 2, ty + ctx.px(8), tag_font, muted, "center")
        _draw_lines(draw, brand_lines, w / 2, ty + ctx.px(10), brand_font, muted, "center")

    return Block("footer", h, draw_footer)


def _try_layout(data: dict, style: Style, brand: str, size: tuple[int, int], scale: float, variant):
    """Build and position all blocks for one (scale, variant). None if it does not fit."""
    width, height = size
    ctx = Ctx(width, height, scale, style, brand)
    base_gap = ctx.px(18)
    card_gap = ctx.px(14)

    header = _header_block(ctx, data)
    footer = _footer_block(ctx, data)
    middle: list[Block] = [
        _section_block(ctx, i, sec, variant["bullets"]) for i, sec in enumerate(data["sections"])
    ]
    gap_before = [base_gap] + [card_gap] * (len(middle) - 1)
    if variant["keypoints"] and data["key_points"]:
        middle.append(_keypoints_block(ctx, data["key_points"][:3]))
        gap_before.append(base_gap)
    if variant["stats"] and data["statistics"]:
        middle.append(_stats_block(ctx, data["statistics"][:3]))
        gap_before.append(base_gap)
    gaps = [*gap_before, base_gap]  # one gap before each block plus one before the footer

    free = height - header.h - footer.h - sum(b.h for b in middle) - sum(gaps)
    if free < 0:
        return None
    stretch = min(free // len(gaps), ctx.px(24))
    leftover = free - stretch * len(gaps)
    y = header.h + gaps[0] + stretch + leftover // 2
    for i, block in enumerate(middle):
        block.y = y
        y += block.h + gaps[i + 1] + stretch
    header.y = 0
    footer.y = height - footer.h
    return [header, *middle, footer]


def render_with_layout(
    content: dict,
    color_theme: str = "",
    size: str = "portrait",
    brand: str = "",
) -> tuple[Image.Image, list[dict]]:
    """Render and also return each block's vertical extent (used by tests)."""
    data = validate(content, clean(content.get("title", "")) or "Infographic")
    dims = SIZES.get(size, SIZES["portrait"])
    theme = color_theme or data["color_theme"]
    style = make_style(theme if theme in PALETTES else "professional")
    brand = clean(brand) or DEFAULT_BRAND

    layout = None
    for variant in VARIANTS:
        for scale in SCALES:
            layout = _try_layout(data, style, brand, dims, scale, variant)
            if layout:
                break
        if layout:
            break
    if layout is None:  # pragma: no cover - the last variant is small enough to always fit
        raise RuntimeError("Content could not be fitted onto the canvas")

    img = Image.new("RGB", dims, style.bg)
    draw = ImageDraw.Draw(img)
    for block in layout:
        block.draw(draw, block.y)
    boxes = [{"name": b.name, "y0": b.y, "y1": b.y + b.h} for b in layout]
    return img, boxes


def render_infographic(
    content: dict, color_theme: str = "", size: str = "portrait", brand: str = ""
) -> Image.Image:
    """Render validated content (see ``content.validate``) to a PIL image."""
    return render_with_layout(content, color_theme, size, brand)[0]
