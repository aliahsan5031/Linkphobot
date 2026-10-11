"""Small vector icons drawn with Pillow primitives, plus keyword-based icon choice.

Every icon is drawn in a unit box (-1..1 on both axes) and scaled to ``size``
pixels, so the same code works at any resolution. Colours are passed in, which
keeps the icons readable on every theme.
"""

from __future__ import annotations

import math

from PIL import ImageDraw

Point = tuple[float, float]


class _Pen:
    """Maps unit coordinates to pixels and draws strokes with round joins."""

    def __init__(self, draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float, color):
        self.d = draw
        self.cx, self.cy = cx, cy
        self.r = size / 2
        self.color = color
        self.lw = max(2, round(size * 0.1))

    def pt(self, x: float, y: float) -> Point:
        return self.cx + x * self.r, self.cy + y * self.r

    def dot(self, x: float, y: float, radius: float | None = None) -> None:
        px, py = self.pt(x, y)
        rad = radius if radius is not None else self.lw / 2
        self.d.ellipse([px - rad, py - rad, px + rad, py + rad], fill=self.color)

    def line(self, pts: list[Point], close: bool = False) -> None:
        pixels = [self.pt(*p) for p in pts]
        if close:
            pixels.append(pixels[0])
        self.d.line(pixels, fill=self.color, width=self.lw, joint="curve")
        for px, py in pixels[:: max(1, len(pixels) - 1)]:  # round the two ends
            rad = self.lw / 2
            self.d.ellipse([px - rad, py - rad, px + rad, py + rad], fill=self.color)

    def poly(self, pts: list[Point]) -> None:
        self.d.polygon([self.pt(*p) for p in pts], fill=self.color)

    def circle(self, x: float, y: float, rad: float, fill: bool = False) -> None:
        px, py = self.pt(x, y)
        box = [px - rad * self.r, py - rad * self.r, px + rad * self.r, py + rad * self.r]
        if fill:
            self.d.ellipse(box, fill=self.color)
        else:
            self.d.ellipse(box, outline=self.color, width=self.lw)

    def rect(self, x0, y0, x1, y1, fill: bool = True, radius: float = 0.0) -> None:
        a, b = self.pt(x0, y0), self.pt(x1, y1)
        r = radius * self.r
        if fill:
            self.d.rounded_rectangle([*a, *b], radius=r, fill=self.color)
        else:
            self.d.rounded_rectangle([*a, *b], radius=r, outline=self.color, width=self.lw)

    def pie(self, x, y, rad, start, end) -> None:
        px, py = self.pt(x, y)
        box = [px - rad * self.r, py - rad * self.r, px + rad * self.r, py + rad * self.r]
        self.d.pieslice(box, start, end, fill=self.color)

    def arc(self, x, y, rad, start, end) -> None:
        px, py = self.pt(x, y)
        box = [px - rad * self.r, py - rad * self.r, px + rad * self.r, py + rad * self.r]
        self.d.arc(box, start, end, fill=self.color, width=self.lw)


def _check(p: _Pen) -> None:
    p.line([(-0.62, 0.02), (-0.2, 0.46), (0.64, -0.46)])


def _bolt(p: _Pen) -> None:
    p.poly([(0.18, -0.9), (-0.55, 0.12), (-0.05, 0.12), (-0.2, 0.9), (0.55, -0.2), (0.05, -0.2)])


def _target(p: _Pen) -> None:
    p.circle(0, 0, 0.82)
    p.circle(0, 0, 0.45)
    p.circle(0, 0, 0.12, fill=True)


def _bulb(p: _Pen) -> None:
    p.arc(0, -0.2, 0.55, 140, 40)
    p.line([(-0.38, 0.12), (-0.28, 0.45), (0.28, 0.45), (0.38, 0.12)])
    p.line([(-0.22, 0.72), (0.22, 0.72)])
    p.line([(0, -0.2), (0, 0.2)])


def _chart(p: _Pen) -> None:
    p.rect(-0.8, 0.05, -0.4, 0.8, radius=0.06)
    p.rect(-0.2, -0.35, 0.2, 0.8, radius=0.06)
    p.rect(0.4, -0.8, 0.8, 0.8, radius=0.06)


def _trend(p: _Pen) -> None:
    p.line([(-0.85, 0.55), (-0.25, -0.05), (0.15, 0.3), (0.8, -0.5)])
    p.line([(0.3, -0.55), (0.82, -0.55), (0.82, -0.05)])


def _shield(p: _Pen) -> None:
    p.line([(0, -0.88), (0.75, -0.55), (0.7, 0.15), (0, 0.9), (-0.7, 0.15), (-0.75, -0.55)],
           close=True)
    p.line([(-0.3, 0.0), (-0.06, 0.26), (0.34, -0.22)])


def _people(p: _Pen) -> None:
    p.circle(-0.3, -0.42, 0.3, fill=True)
    p.pie(-0.3, 0.92, 0.62, 180, 360)
    p.circle(0.5, -0.3, 0.24, fill=True)
    p.pie(0.5, 0.78, 0.46, 180, 360)


def _gear(p: _Pen) -> None:
    for k in range(8):
        a = k * math.pi / 4
        c, s = math.cos(a), math.sin(a)
        w = 0.17
        p.poly([(0.6 * c - w * s, 0.6 * s + w * c), (0.92 * c - w * s, 0.92 * s + w * c),
                (0.92 * c + w * s, 0.92 * s - w * c), (0.6 * c + w * s, 0.6 * s - w * c)])
    p.circle(0, 0, 0.62)
    p.circle(0, 0, 0.24)


def _clock(p: _Pen) -> None:
    p.circle(0, 0, 0.84)
    p.line([(0, -0.5), (0, 0), (0.38, 0.22)])


def _globe(p: _Pen) -> None:
    p.circle(0, 0, 0.84)
    p.d.ellipse(
        [*p.pt(-0.38, -0.84), *p.pt(0.38, 0.84)], outline=p.color, width=p.lw
    )
    p.line([(-0.84, 0), (0.84, 0)])


def _lock(p: _Pen) -> None:
    p.rect(-0.62, -0.05, 0.62, 0.88, fill=True, radius=0.14)
    p.arc(0, -0.22, 0.4, 180, 360)
    p.line([(-0.4, -0.22), (-0.4, 0.0)])
    p.line([(0.4, -0.22), (0.4, 0.0)])


def _heart(p: _Pen) -> None:
    p.circle(-0.33, -0.3, 0.37, fill=True)
    p.circle(0.33, -0.3, 0.37, fill=True)
    p.poly([(-0.68, -0.08), (0.68, -0.08), (0, 0.84)])


def _dollar(p: _Pen) -> None:
    p.circle(0, 0, 0.84)
    p.line([(0.3, -0.38), (0.0, -0.52), (-0.3, -0.34), (-0.3, -0.14), (0.3, 0.14), (0.3, 0.34),
            (0.0, 0.52), (-0.3, 0.38)])
    p.line([(0, -0.66), (0, -0.5)])
    p.line([(0, 0.5), (0, 0.66)])


def _code(p: _Pen) -> None:
    p.line([(-0.35, -0.5), (-0.85, 0), (-0.35, 0.5)])
    p.line([(0.35, -0.5), (0.85, 0), (0.35, 0.5)])
    p.line([(0.12, -0.62), (-0.12, 0.62)])


def _book(p: _Pen) -> None:
    p.line([(-0.85, -0.6), (-0.05, -0.45), (-0.05, 0.75), (-0.85, 0.6)], close=True)
    p.line([(0.85, -0.6), (0.05, -0.45), (0.05, 0.75), (0.85, 0.6)], close=True)


def _star(p: _Pen) -> None:
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = 0.92 if k % 2 == 0 else 0.4
        pts.append((rad * math.cos(ang), rad * math.sin(ang)))
    p.poly(pts)


def _chat(p: _Pen) -> None:
    p.rect(-0.85, -0.7, 0.85, 0.35, fill=False, radius=0.22)
    p.line([(-0.35, 0.35), (-0.45, 0.85), (0.1, 0.35)])


def _network(p: _Pen) -> None:
    nodes = [(0, -0.6), (-0.65, 0.45), (0.65, 0.45)]
    p.line([nodes[0], nodes[1], nodes[2]], close=True)
    for x, y in nodes:
        p.circle(x, y, 0.2, fill=True)


def _cap(p: _Pen) -> None:
    p.poly([(0, -0.7), (0.95, -0.2), (0, 0.3), (-0.95, -0.2)])
    p.line([(-0.55, 0.12), (-0.55, 0.62), (0, 0.85), (0.55, 0.62), (0.55, 0.12)])


ICONS = {
    "check": _check, "bolt": _bolt, "target": _target, "bulb": _bulb, "chart": _chart,
    "trend": _trend, "shield": _shield, "people": _people, "gear": _gear, "clock": _clock,
    "globe": _globe, "lock": _lock, "heart": _heart, "dollar": _dollar, "code": _code,
    "book": _book, "star": _star, "chat": _chat, "network": _network, "cap": _cap,
}

# Icon -> words that suggest it. Matched as substrings of the lower-cased text.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "heart": ("health", "patient", "care", "medic", "wellness", "wellbeing", "clinic", "mental"),
    "dollar": ("cost", "revenue", "price", "money", "saving", "budget", "invest", "financ",
               "profit", "salary", "income", "earn", "sales", "pay"),
    "shield": ("secur", "privacy", "risk", "safe", "protect", "complian", "ethic", "trust",
               "regulat", "govern"),
    "lock": ("encrypt", "password", "authent", "access control", "breach", "confidential"),
    "people": ("team", "people", "leader", "culture", "communit", "collaborat", "hire", "talent",
               "customer", "audience", "employee", "mentor", "stakeholder"),
    "chart": ("data", "analytic", "metric", "report", "kpi", "measure", "dashboard", "statistic"),
    "trend": ("growth", "trend", "scale", "increase", "future", "forecast", "market", "rise"),
    "target": ("goal", "strateg", "focus", "objective", "roadmap", "priorit", "vision", "mission"),
    "bulb": ("idea", "innovat", "creativ", "solution", "insight", "brainstorm", "invent"),
    "gear": ("process", "automat", "workflow", "tool", "engineer", "system", "implement",
             "build", "optimi", "operat", "infrastructure"),
    "clock": ("time", "speed", "fast", "schedule", "deadline", "productiv", "efficien", "routine",
              "habit"),
    "globe": ("global", "remote", "world", "international", "online", "internet", "web",
              "language", "travel"),
    "code": ("code", "software", "develop", "program", "python", "api", "algorithm", "debug",
             "framework"),
    "network": ("ai", "artificial", "machine", "neural", "model", "cloud", "llm", "intelligen",
                "network", "digital"),
    "book": ("read", "knowledge", "guide", "learn", "course", "tutorial", "resource", "book"),
    "cap": ("educat", "skill", "train", "study", "career", "certif", "student", "school"),
    "chat": ("communic", "feedback", "message", "conversation", "meeting", "interview",
             "story", "network", "present", "speak", "write", "content"),
    "bolt": ("energy", "power", "quick", "boost", "performance", "accelerat", "agile", "launch"),
    "star": ("quality", "best", "excellen", "brand", "reputation", "award", "top", "success"),
}

FALLBACK_ORDER = ("target", "bulb", "bolt", "gear", "chart", "star", "trend", "check")


def draw_icon(draw: ImageDraw.ImageDraw, name: str, cx: float, cy: float, size: float,
              color) -> None:
    """Draw icon ``name`` centred on (cx, cy), fitting a ``size`` px square."""
    painter = ICONS.get(name, _check)
    painter(_Pen(draw, cx, cy, size, color))


def _score(icon: str, heading: str, body: str) -> int:
    score = 0
    for word in KEYWORDS.get(icon, ()):
        if len(word) <= 3:  # short words such as "ai" must match a whole word
            padded_h, padded_b = f" {heading} ", f" {body} "
            score += 3 * (f" {word} " in padded_h) + (f" {word} " in padded_b)
        else:
            score += 3 * (word in heading) + (word in body)
    return score


def pick_icons(sections: list[dict]) -> list[str]:
    """One distinct icon per section, chosen from its words; deterministic."""
    used: set[str] = set()
    chosen: list[str] = []
    for section in sections:
        heading = str(section.get("heading", "")).lower()
        body = " ".join(str(b) for b in section.get("content", [])).lower()
        ranked = sorted(KEYWORDS, key=lambda icon: -_score(icon, heading, body))
        best = next((i for i in ranked if i not in used and _score(i, heading, body) > 0), None)
        if best is None:
            best = next((i for i in FALLBACK_ORDER if i not in used), FALLBACK_ORDER[0])
        used.add(best)
        chosen.append(best)
    return chosen
