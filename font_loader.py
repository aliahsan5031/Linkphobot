"""
font_loader.py
==============
Linkphobot - Phase 3: Fixed Template Renderer
Font Loading & Management System
"""

import os
from PIL import ImageFont

_FONT_SEARCH_PATHS = [
    "/content/linkphobot/phase3/fonts/",
    "/tmp/linkphobot_fonts/",
    "/usr/share/fonts/truetype/liberation/",
    "/usr/share/fonts/truetype/dejavu/",
    "/usr/share/fonts/truetype/ubuntu/",
    "/usr/share/fonts/truetype/",
    "/usr/local/share/fonts/",
    "/Library/Fonts/",
    "C:/Windows/Fonts/",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
]

_FONT_FILE_MAP = {
    "regular":   ["Inter-Regular.ttf",   "LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
    "medium":    ["Inter-Medium.ttf",    "LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
    "semibold":  ["Inter-SemiBold.ttf",  "LiberationSans-Bold.ttf",   "DejaVuSans-Bold.ttf"],
    "bold":      ["Inter-Bold.ttf",      "LiberationSans-Bold.ttf",   "DejaVuSans-Bold.ttf"],
    "extrabold": ["Inter-ExtraBold.ttf", "LiberationSans-Bold.ttf",   "DejaVuSans-Bold.ttf"],
    "black":     ["Inter-Black.ttf",     "Inter-ExtraBold.ttf",       "LiberationSans-Bold.ttf"],
}

_WEIGHT_ALIAS = {
    "400":"regular","normal":"regular","regular":"regular",
    "500":"medium","medium":"medium",
    "600":"semibold","semibold":"semibold",
    "700":"bold","bold":"bold",
    "800":"extrabold","extrabold":"extrabold",
    "900":"black","black":"black",
}

_FONT_CACHE   = {}
_RESOLVED     = {}


def _find_font(lw):
    for d in _FONT_SEARCH_PATHS:
        if not os.path.isdir(d):
            continue
        for fname in _FONT_FILE_MAP.get(lw, _FONT_FILE_MAP["regular"]):
            fp = os.path.join(d, fname)
            if os.path.isfile(fp):
                return fp
    return None


def get_font(weight="regular", size=24):
    size = max(8, min(200, int(size)))
    lw   = _WEIGHT_ALIAS.get(str(weight).lower(), "regular")
    key  = (lw, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    if lw not in _RESOLVED:
        _RESOLVED[lw] = _find_font(lw)
    path = _RESOLVED.get(lw)
    if path:
        try:
            f = ImageFont.truetype(path, size)
            _FONT_CACHE[key] = f
            return f
        except Exception:
            pass
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def measure_text(text, font):
    try:
        b = font.getbbox(text)
        return b[2]-b[0], b[3]-b[1]
    except Exception:
        return len(text)*(getattr(font,"size",12)//2), getattr(font,"size",12)


def wrap_text(text, font, max_width):
    if not text:
        return [""]
    words = text.split()
    lines, cur = [], []
    for word in words:
        test = " ".join(cur+[word])
        w, _ = measure_text(test, font)
        if w <= max_width:
            cur.append(word)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [word]
    if cur:
        lines.append(" ".join(cur))
    return lines or [text]


def text_block_height(text, font, max_width, line_spacing=6):
    lines = wrap_text(text, font, max_width)
    _, lh = measure_text("Ag", font)
    return len(lines) * (lh + line_spacing)


def warmup_fonts():
    sizes   = [16,18,20,22,24,26,28,30,32,36,40,44,48,56,64,72]
    weights = ["regular","medium","semibold","bold","extrabold"]
    for w in weights:
        for s in sizes:
            get_font(w, s)
    print(f"[font_loader] Warmed up {len(sizes)*len(weights)} font variants")
