"""Adaptive infographic renderer (Pillow only).

Every block is measured first: text is wrapped to the width it has, then the
stack is shrunk, and finally stripped of its least important blocks, until it
fits the canvas. Nothing is placed at a hard-coded y offset, so blocks cannot
overlap, and emoji (which the fonts cannot draw) are replaced by drawn icons.

Everything is drawn at ``SS`` times the final size and scaled down at the end,
which gives smooth edges on shapes, rings and icons. Fonts are bundled with the
app (``linkphobot/assets/fonts``) so the image looks the same on every machine.
"""

from __future__ import annotations

import base64
import io
import logging
import math
import os
import re
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .caption import normalize_hashtags
from .config import DEFAULT_BRAND, PALETTES, SIZES
from .content import validate
from .icons import draw_icon, pick_icons

log = logging.getLogger("linkphobot.render")

Color = tuple[int, int, int]

SS = 2  # supersampling factor
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


def visible(color: Color, bg: Color, ratio: float = 2.2) -> Color:
    """A decorative colour nudged until it can be seen against ``bg``."""
    return ensure_contrast(color, bg, ratio)


# ------------------------------------------------------------------------- fonts

_FONT_DIR = Path(__file__).parent / "assets" / "fonts"
# Stored as text (subset, compressed, base64) because Hugging Face rejects binary files
# in a plain git push. scripts/pack_fonts.py rebuilds them.
_BUNDLED = {
    "regular": "Inter-Regular.b64",
    "medium": "Inter-Medium.b64",
    "semibold": "Inter-SemiBold.b64",
    "bold": "Inter-Bold.b64",
    "display": "Poppins-Bold.b64",
}
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


@lru_cache(maxsize=8)
def _bundled_bytes(weight: str) -> bytes | None:
    name = _BUNDLED.get(weight, _BUNDLED["regular"])
    try:
        return zlib.decompress(base64.b64decode((_FONT_DIR / name).read_text()))
    except (OSError, ValueError, zlib.error):
        log.warning("Bundled font %s could not be read", name)
        return None


@lru_cache(maxsize=256)
def load_font(size: int, bold: bool = False, weight: str = ""):
    """Load a TrueType font at ``size`` px.

    ``weight`` is one of regular, medium, semibold, bold, display and
    overrides ``bold``. Set LINKPHOBOT_FONT / LINKPHOBOT_FONT_BOLD to use your own
    font files instead of the bundled Inter and Poppins. Falls back to system
    fonts, then to Pillow's built-in scalable font, never to a tiny bitmap one.
    """
    weight = weight or ("bold" if bold else "regular")
    heavy = weight not in ("regular", "medium")
    custom = os.environ.get("LINKPHOBOT_FONT_BOLD" if heavy else "LINKPHOBOT_FONT", "")
    if custom and os.path.isfile(custom):
        try:
            return ImageFont.truetype(custom, size)
        except OSError:
            pass
    data = _bundled_bytes(weight)
    if data:
        try:
            return ImageFont.truetype(io.BytesIO(data), size)
        except OSError:
            pass
    for path in _BOLD if heavy else _REGULAR:
        if os.path.isfile(path):
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


def line_height(font, factor: float = 1.3) -> int:
    return round(font_size(font) * factor)


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


# ----------------------------------------------------------------------- drawing


class Canvas:
    """The supersampled image plus its pen."""

    def __init__(self, size: tuple[int, int], bg: Color):
        self.img = Image.new("RGB", size, bg)
        self.draw = ImageDraw.Draw(self.img)

    def lines(self, lines, x, y, font, fill, align="left", factor: float = 1.3) -> int:
        lh = line_height(font, factor)
        for i, line in enumerate(lines):
            px = x - text_width(font, line) / 2 if align == "center" else x
            self.draw.text((px, y + i * lh), line, font=font, fill=fill)
        return y + len(lines) * lh

    def centered(self, text, cx, cy, font, fill) -> None:
        self.draw.text((cx, cy), text, font=font, fill=fill, anchor="mm")

    def shadow(self, box, radius: int, blur: int, dy: int, alpha: int, color=(0, 0, 0)) -> None:
        """A soft drop shadow under a rounded box."""
        x0, y0, x1, y1 = (round(v) for v in box)
        pad = blur * 3
        w, h = x1 - x0, y1 - y0
        layer = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
        ImageDraw.Draw(layer).rounded_rectangle([pad, pad, pad + w, pad + h], radius, fill=alpha)
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
        self.img.paste(Image.new("RGB", layer.size, color), (x0 - pad, y0 - pad + dy), layer)
        self.draw = ImageDraw.Draw(self.img)

    def overlay(self, box, paint: Callable[[ImageDraw.ImageDraw], None]) -> None:
        """Draw translucent shapes (RGBA) inside ``box`` and blend them in."""
        x0, y0, x1, y1 = box
        layer = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        paint(ImageDraw.Draw(layer))
        region = self.img.crop(box).convert("RGBA")
        self.img.paste(Image.alpha_composite(region, layer).convert("RGB"), (x0, y0))
        self.draw = ImageDraw.Draw(self.img)

    def gradient(self, box, top: Color, bottom: Color) -> None:
        x0, y0, x1, y1 = box
        span = max(1, y1 - y0 - 1)
        for row in range(y1 - y0):
            self.draw.line([(x0, y0 + row), (x1, y0 + row)], fill=mix(top, bottom, row / span))


# ------------------------------------------------------------------------ layout


def _up(value: float) -> int:
    """Round up to a whole number of final pixels (a multiple of SS)."""
    return -(-int(math.ceil(value)) // SS) * SS


@dataclass
class Block:
    name: str
    h: int
    draw: Callable[[Canvas, int], None]
    y: int = 0


@dataclass
class Ctx:
    width: int  # final pixels
    height: int
    scale: float
    style: Style
    brand: str
    card_w: int = field(init=False)
    margin: int = field(init=False)

    def __post_init__(self) -> None:
        self.margin = MARGIN * SS
        self.card_w = self.width * SS - 2 * self.margin

    @property
    def W(self) -> int:  # noqa: N802 - canvas width in supersampled pixels
        return self.width * SS

    def px(self, value: float) -> int:
        """Design pixels to supersampled pixels, always a whole number of final pixels."""
        return SS * round(value * self.scale)

    def font(self, size: float, weight: str = "regular"):
        return load_font(max(MIN_FONT_PX * SS, round(size * self.scale * SS)), weight=weight)

    def fit(self, text: str, weight: str, sizes, max_w: float, max_lines: int, factor=1.3):
        """Largest size in ``sizes`` whose wrapped text fits ``max_lines``."""
        text = clean(text)
        if not text:
            return self.font(sizes[0], weight), []
        for size in sizes:
            font = self.font(size, weight)
            lines = wrap_text(text, font, max_w, 999)
            if len(lines) <= max_lines:
                return font, lines
        font = self.font(sizes[-1], weight)
        return font, wrap_text(text, font, max_w, max_lines)


def _header_block(ctx: Ctx, data: dict) -> Block:
    st, W = ctx.style, ctx.W
    inner = W - 2 * ctx.margin
    badge_font = ctx.font(15, "bold")
    badge_text = clean(data["content_type"]).upper() or "INSIGHTS"
    badge_w = int(text_width(badge_font, badge_text)) + ctx.px(40)
    badge_h = ctx.px(34)
    title_font, title_lines = ctx.fit(
        data["title"], "display", (52, 48, 44, 40, 36, 32), inner, 2
    )
    sub_font, sub_lines = ctx.fit(data["subtitle"], "regular", (24, 22, 20), inner, 2)

    top_pad = ctx.px(40)
    title_y = top_pad + badge_h + ctx.px(22)
    title_lh = line_height(title_font, 1.2)
    rule_y = title_y + len(title_lines) * title_lh + ctx.px(12)
    rule_h = ctx.px(5)
    sub_y = rule_y + rule_h + ctx.px(14)
    h = _up(sub_y + len(sub_lines) * line_height(sub_font) + ctx.px(34))

    def draw_header(cv: Canvas, y: int) -> None:
        bottom = mix(st.header, BLACK, 0.3)
        cv.gradient((0, 0, W, h), mix(st.header, WHITE, 0.06), bottom)

        def decor(d: ImageDraw.ImageDraw) -> None:
            d.ellipse([W - ctx.px(330), -ctx.px(190), W + ctx.px(110), ctx.px(250)],
                      fill=(255, 255, 255, 22))
            d.ellipse([W - ctx.px(230), -ctx.px(120), W + ctx.px(40), ctx.px(150)],
                      fill=(255, 255, 255, 18))
            d.ellipse([-ctx.px(120), h - ctx.px(150), ctx.px(190), h + ctx.px(110)],
                      fill=(255, 255, 255, 16))
            step = ctx.px(22)
            for gx in range(4):
                for gy in range(3):
                    cx, cy = ctx.px(34) + gx * step, ctx.px(34) + gy * step
                    r = ctx.px(2.4)
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 70))

        cv.overlay((0, 0, W, h), decor)
        cv.draw.rectangle([0, h - ctx.px(6), W, h], fill=st.accent)
        cv.draw.rounded_rectangle(
            [(W - badge_w) // 2, top_pad, (W + badge_w) // 2, top_pad + badge_h],
            radius=badge_h // 2,
            fill=st.accent,
        )
        cv.centered(badge_text, W / 2, top_pad + badge_h / 2, badge_font, st.on_accent)
        cv.lines(title_lines, W / 2, title_y, title_font, WHITE, "center", 1.2)
        rule_w = ctx.px(72)
        cv.draw.rounded_rectangle(
            [(W - rule_w) // 2, rule_y, (W + rule_w) // 2, rule_y + rule_h],
            radius=rule_h // 2, fill=st.accent,
        )
        sub_color = ensure_contrast((203, 213, 224), mix(st.header, BLACK, 0.15))
        cv.lines(sub_lines, W / 2, sub_y, sub_font, sub_color, "center")

    return Block("header", h, draw_header)


@dataclass
class _Card:
    w: int
    h: int
    index: int
    icon: str
    head_font: object
    head_lines: list
    body_font: object
    bullets: list


def _measure_card(ctx: Ctx, index: int, section: dict, icon: str, width: int,
                  max_bullets: int, narrow: bool) -> _Card:
    pad = ctx.px(22)
    tile = ctx.px(56)
    text_off = pad + tile + ctx.px(14)
    inner_w = width - text_off - pad
    head_font, head_lines = ctx.fit(
        section["heading"], "bold", (25, 23, 21, 19) if narrow else (27, 25, 23, 21),
        inner_w, 2,
    )
    body_font = ctx.font(19 if narrow else 21)
    body_w = width - 2 * pad - ctx.px(22)
    bullets = [
        wrap_text(clean(b), body_font, body_w, 3 if narrow else 2)
        for b in section["content"][:max_bullets]
        if clean(b)
    ]
    gap = ctx.px(9)
    head_h = max(tile, len(head_lines) * line_height(head_font, 1.22))
    bullets_h = sum(len(b) * line_height(body_font, 1.32) for b in bullets)
    bullets_h += gap * max(0, len(bullets) - 1)
    h = pad + head_h + (ctx.px(14) if bullets else 0) + bullets_h + pad
    return _Card(width, _up(h), index, icon, head_font, head_lines, body_font, bullets)


def _draw_card(ctx: Ctx, cv: Canvas, card: _Card, x: int, y: int, h: int) -> None:
    st = ctx.style
    pad, tile = ctx.px(22), ctx.px(56)
    radius = ctx.px(18)
    cv.shadow((x, y, x + card.w, y + h), radius, ctx.px(9), ctx.px(5), 46 if not st.dark else 90)
    cv.draw.rounded_rectangle([x, y, x + card.w, y + h], radius=radius, fill=st.card_a,
                              outline=st.border, width=SS)
    # icon tile
    tx, ty = x + pad, y + pad
    cv.draw.rounded_rectangle([tx, ty, tx + tile, ty + tile], radius=ctx.px(16), fill=st.header)
    draw_icon(cv.draw, card.icon, tx + tile / 2, ty + tile / 2, tile * 0.52, WHITE)
    # number badge on the tile corner
    nb = ctx.px(24)
    nx, ny = tx + tile - nb * 0.55, ty - nb * 0.45
    cv.draw.ellipse([nx, ny, nx + nb, ny + nb], fill=st.accent, outline=st.card_a, width=ctx.px(2))
    cv.centered(str(card.index + 1), nx + nb / 2, ny + nb / 2, ctx.font(13, "bold"),
                st.on_accent)
    # heading
    head_color = ensure_contrast(st.heading, st.card_a)
    head_lh = line_height(card.head_font, 1.22)
    head_block = len(card.head_lines) * head_lh
    head_h = max(tile, head_block)
    hy = y + pad + (head_h - head_block) // 2
    cv.lines(card.head_lines, x + pad + tile + ctx.px(14), hy, card.head_font, head_color,
             factor=1.22)
    # bullets
    body_color = ensure_contrast(st.text, st.card_a)
    marker = visible(st.accent, st.card_a)
    by = y + pad + head_h + ctx.px(14)
    gap = ctx.px(9)
    lh = line_height(card.body_font, 1.32)
    indent = ctx.px(22)
    for lines in card.bullets:
        d = ctx.px(9)
        dy = by + (lh - d) // 2
        cv.draw.rounded_rectangle([x + pad, dy, x + pad + d, dy + d], radius=d // 3, fill=marker)
        by = cv.lines(lines, x + pad + indent, by, card.body_font, body_color, factor=1.32)
        by += gap


def _section_rows(ctx: Ctx, data: dict, max_bullets: int, row_gap: int) -> list[Block]:
    """Sections as a two-column grid (one column for one or two sections)."""
    sections = data["sections"]
    n = len(sections)
    icons = pick_icons(sections)
    cols = 2 if n >= 3 else 1
    col_gap = ctx.px(18)
    col_w = (ctx.card_w - col_gap) // 2 if cols == 2 else ctx.card_w
    rows: list[list[_Card]] = []
    i = 0
    while i < n:
        if cols == 2 and n - i >= 2 and not (n - i == 1):
            rows.append([
                _measure_card(ctx, i, sections[i], icons[i], col_w, max_bullets, True),
                _measure_card(ctx, i + 1, sections[i + 1], icons[i + 1], col_w, max_bullets, True),
            ])
            i += 2
        else:
            rows.append([
                _measure_card(ctx, i, sections[i], icons[i], ctx.card_w, max_bullets, False)
            ])
            i += 1
    blocks = []
    for k, row in enumerate(rows):
        h = max(c.h for c in row)

        def draw_row(cv: Canvas, y: int, row=row, h=h) -> None:
            x = ctx.margin
            for card in row:
                _draw_card(ctx, cv, card, x, y, h)
                x += card.w + col_gap

        blocks.append(Block(f"section_row_{k + 1}", h, draw_row))
    return blocks


def _keypoints_block(ctx: Ctx, points: list[str]) -> Block:
    st = ctx.style
    pad = ctx.px(20)
    n = len(points)
    col_gap = ctx.px(22)
    mark = ctx.px(28)
    col_w = (ctx.card_w - 2 * pad - col_gap * (n - 1)) / n
    font = ctx.font(18, "medium")
    indent = mark + ctx.px(10)
    columns = [wrap_text(clean(p), font, col_w - indent, 3) for p in points]
    h = _up(2 * pad + max(mark, max(len(c) for c in columns) * line_height(font, 1.28)))
    radius = ctx.px(16)

    def draw_band(cv: Canvas, y: int) -> None:
        x0 = ctx.margin
        cv.shadow((x0, y, x0 + ctx.card_w, y + h), radius, ctx.px(8), ctx.px(4), 60)
        cv.draw.rounded_rectangle([x0, y, x0 + ctx.card_w, y + h], radius=radius, fill=st.header,
                                  outline=mix(st.header, WHITE, 0.22), width=SS)
        for i, lines in enumerate(columns):
            x = x0 + pad + i * (col_w + col_gap)
            cv.draw.ellipse([x, y + pad, x + mark, y + pad + mark], fill=st.accent)
            draw_icon(cv.draw, "check", x + mark / 2, y + pad + mark / 2, mark * 0.5,
                      st.on_accent)
            cv.lines(lines, x + indent, y + pad + ctx.px(2), font, WHITE, factor=1.28)

    return Block("key_points", h, draw_band)


_PERCENT = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*%")


def _percent(value: str) -> float | None:
    match = _PERCENT.search(value or "")
    if not match:
        return None
    number = float(match.group(1).replace(",", "."))
    return number / 100 if 0 <= number <= 100 else None


def _stats_block(ctx: Ctx, stats: list[dict]) -> Block:
    st = ctx.style
    n = len(stats)
    gap = ctx.px(14)
    sw = (ctx.card_w - gap * (n - 1)) / n
    pad = ctx.px(16)
    ring = ctx.px(74)
    text_x = pad + ring + ctx.px(14)
    text_w = sw - text_x - pad
    label_font = ctx.font(16, "medium")
    icons = pick_icons([{"heading": s["label"], "content": []} for s in stats])
    cards = []
    for stat, icon in zip(stats, icons, strict=False):
        value_font, value_lines = ctx.fit(stat["value"], "display", (34, 30, 27, 24, 21), text_w, 1)
        label_lines = wrap_text(clean(stat["label"]), label_font, text_w, 3)
        cards.append((value_font, value_lines, label_lines, _percent(stat["value"]), icon))
    text_h = max(
        line_height(c[0], 1.15) + ctx.px(4) + len(c[2]) * line_height(label_font, 1.28)
        for c in cards
    )
    h = _up(2 * pad + max(ring, text_h))
    value_color = ensure_contrast(st.heading, st.card_b)
    label_color = ensure_contrast(st.text, st.card_b)
    radius = ctx.px(16)

    def draw_stats(cv: Canvas, y: int) -> None:
        for i, (value_font, value_lines, label_lines, fraction, icon) in enumerate(cards):
            x = ctx.margin + i * (sw + gap)
            cv.shadow((x, y, x + sw, y + h), radius, ctx.px(8), ctx.px(4),
                      80 if st.dark else 38)
            cv.draw.rounded_rectangle([x, y, x + sw, y + h], radius=radius, fill=st.card_b,
                                      outline=st.border, width=SS)
            cx, cy = x + pad + ring / 2, y + h / 2
            track = mix(st.card_b, st.heading, 0.16)
            thick = ctx.px(9)
            box = [cx - ring / 2, cy - ring / 2, cx + ring / 2, cy + ring / 2]
            if fraction is not None:
                cv.draw.arc(box, 0, 360, fill=track, width=thick)
                if fraction > 0:
                    arc_color = visible(st.accent, st.card_b, 2.2)
                    cv.draw.arc(box, -90, -90 + 360 * fraction, fill=arc_color, width=thick)
                    for ang in (-90, -90 + 360 * fraction):
                        r = ring / 2 - thick / 2
                        ex = cx + r * math.cos(math.radians(ang))
                        ey = cy + r * math.sin(math.radians(ang))
                        cv.draw.ellipse([ex - thick / 2, ey - thick / 2, ex + thick / 2,
                                         ey + thick / 2], fill=arc_color)
            else:
                cv.draw.ellipse(box, fill=track)
            draw_icon(cv.draw, icon, cx, cy, ring * 0.36, st.header if not st.dark else st.heading)
            tx = x + text_x
            ty = y + (h - (line_height(value_font, 1.15) + ctx.px(4)
                           + max(len(c[2]) for c in cards) * line_height(label_font, 1.28))) // 2
            ty = cv.lines(value_lines, tx, ty, value_font, value_color, factor=1.15)
            cv.lines(label_lines, tx, ty + ctx.px(4), label_font, label_color, factor=1.28)

    return Block("stats", h, draw_stats)


def _footer_block(ctx: Ctx, data: dict) -> Block:
    st, W = ctx.style, ctx.W
    cta_font, cta_lines = ctx.fit(
        data["call_to_action"], "semibold", (21, 19, 17), ctx.card_w - ctx.px(48), 2
    )
    cta_pad = ctx.px(13)
    cta_h = 2 * cta_pad + len(cta_lines) * line_height(cta_font, 1.28)
    tag_font = ctx.font(16, "medium")
    chip_h = ctx.px(32)
    chip_pad = ctx.px(14)
    chip_gap = ctx.px(10)
    chips, used = [], 0
    for tag in normalize_hashtags(data["hashtags"])[:5]:
        w = int(text_width(tag_font, tag)) + 2 * chip_pad
        if used + w + (chip_gap if chips else 0) > ctx.card_w:
            break
        used += w + (chip_gap if chips else 0)
        chips.append((tag, w))
    brand_font, brand_lines = ctx.fit(ctx.brand, "medium", (15, 14), ctx.card_w, 1)

    top = ctx.px(14)
    h = _up(
        top + cta_h
        + (ctx.px(12) + chip_h if chips else 0)
        + ctx.px(12) + line_height(brand_font)
        + ctx.px(16)
    )
    muted = ensure_contrast(mix(st.text, st.bg, 0.2), st.bg)
    chip_bg = mix(st.bg, st.heading, 0.12)
    chip_fg = ensure_contrast(st.heading, chip_bg)

    def draw_footer(cv: Canvas, y: int) -> None:
        ty = y + top
        x0 = ctx.margin
        cv.draw.rounded_rectangle([x0, ty, x0 + ctx.card_w, ty + cta_h], radius=cta_h // 2,
                                  fill=st.accent)
        cv.lines(cta_lines, W / 2, ty + cta_pad, cta_font, st.on_accent, "center", 1.28)
        ty += cta_h
        if chips:
            ty += ctx.px(12)
            x = (W - used) / 2
            for tag, w in chips:
                cv.draw.rounded_rectangle([x, ty, x + w, ty + chip_h], radius=chip_h // 2,
                                          fill=chip_bg)
                cv.centered(tag, x + w / 2, ty + chip_h / 2, tag_font, chip_fg)
                x += w + chip_gap
            ty += chip_h
        cv.lines(brand_lines, W / 2, ty + ctx.px(12), brand_font, muted, "center")

    return Block("footer", h, draw_footer)


def _try_layout(data: dict, style: Style, brand: str, size: tuple[int, int], scale: float, variant):
    """Build and position all blocks for one (scale, variant). None if it does not fit."""
    width, height = size
    H = height * SS
    ctx = Ctx(width, height, scale, style, brand)
    base_gap = ctx.px(16)
    row_gap = ctx.px(16)

    header = _header_block(ctx, data)
    footer = _footer_block(ctx, data)
    middle: list[Block] = _section_rows(ctx, data, variant["bullets"], row_gap)
    gap_before = [base_gap] + [row_gap] * (len(middle) - 1)
    if variant["keypoints"] and data["key_points"]:
        middle.append(_keypoints_block(ctx, data["key_points"][:3]))
        gap_before.append(base_gap)
    if variant["stats"] and data["statistics"]:
        middle.append(_stats_block(ctx, data["statistics"][:3]))
        gap_before.append(base_gap)
    gaps = [*gap_before, base_gap]  # one gap before each block plus one before the footer

    free = H - header.h - footer.h - sum(b.h for b in middle) - sum(gaps)
    if free < 0:
        return None
    stretch = min(free // len(gaps) // SS * SS, ctx.px(44))
    leftover = free - stretch * len(gaps)
    y = header.h + gaps[0] + stretch + leftover // 2 // SS * SS
    for i, block in enumerate(middle):
        block.y = y
        y += block.h + gaps[i + 1] + stretch
    header.y = 0
    footer.y = H - footer.h
    return [header, *middle, footer]


def render_with_layout(
    content: dict,
    color_theme: str = "",
    size: str = "portrait",
    brand: str = "",
) -> tuple[Image.Image, list[dict]]:
    """Render and also return each block's vertical extent in final pixels (used by tests)."""
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

    cv = Canvas((dims[0] * SS, dims[1] * SS), style.bg)
    cv.gradient((0, 0, dims[0] * SS, dims[1] * SS), style.bg, mix(style.bg, style.primary, 0.05))
    for block in layout:
        block.draw(cv, block.y)
    img = cv.img.resize(dims, Image.LANCZOS)
    boxes = [{"name": b.name, "y0": b.y // SS, "y1": (b.y + b.h) // SS} for b in layout]
    return img, boxes


def render_infographic(
    content: dict, color_theme: str = "", size: str = "portrait", brand: str = ""
) -> Image.Image:
    """Render validated content (see ``content.validate``) to a PIL image."""
    return render_with_layout(content, color_theme, size, brand)[0]
