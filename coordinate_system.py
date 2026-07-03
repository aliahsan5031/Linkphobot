"""
coordinate_system.py
====================
Linkphobot - Phase 5: Layout Engine
Canvas Coordinate Model

Defines:
  - Canvas constants
  - Point, Rect, Margin, Anchor dataclasses
  - Collision detection
  - Zone definitions (header/body/footer)
  - Anchor point helpers
  - Coordinate validation
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════════════
# CANVAS CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

CANVAS_W      = 1080
CANVAS_H      = 1350
MARGIN_H      = 54          # left / right margin
MARGIN_V      = 54          # top / bottom margin
CONTENT_W     = CANVAS_W - MARGIN_H * 2   # 972px
CONTENT_H     = CANVAS_H - MARGIN_V * 2   # 1242px
CONTENT_X     = MARGIN_H
CONTENT_Y     = MARGIN_V

# Named vertical zones (as fraction of canvas height)
ZONE_HEADER_FRAC   = 0.33   # top 33% reserved for header
ZONE_BODY_FRAC     = 0.54   # middle 54% for sections
ZONE_FOOTER_FRAC   = 0.13   # bottom 13% for footer

ZONE_HEADER_H  = int(CANVAS_H * ZONE_HEADER_FRAC)   # ~445px
ZONE_BODY_H    = int(CANVAS_H * ZONE_BODY_FRAC)      # ~729px
ZONE_FOOTER_H  = CANVAS_H - ZONE_HEADER_H - ZONE_BODY_H  # ~176px

ZONE_HEADER_Y  = MARGIN_V
ZONE_BODY_Y    = ZONE_HEADER_Y + ZONE_HEADER_H
ZONE_FOOTER_Y  = ZONE_BODY_Y  + ZONE_BODY_H


# ════════════════════════════════════════════════════════════════════════════
# POINT
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class Point:
    x: int = 0
    y: int = 0

    def offset(self, dx: int = 0, dy: int = 0) -> "Point":
        return Point(self.x + dx, self.y + dy)

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)

    def __repr__(self):
        return f"Point({self.x}, {self.y})"


# ════════════════════════════════════════════════════════════════════════════
# MARGIN
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class Margin:
    top:    int = 0
    right:  int = 0
    bottom: int = 0
    left:   int = 0

    @classmethod
    def uniform(cls, value: int) -> "Margin":
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, vertical: int, horizontal: int) -> "Margin":
        return cls(vertical, horizontal, vertical, horizontal)

    @property
    def horizontal(self) -> int:
        return self.left + self.right

    @property
    def vertical(self) -> int:
        return self.top + self.bottom

    def to_dict(self) -> dict:
        return {"top": self.top, "right": self.right,
                "bottom": self.bottom, "left": self.left}


# ════════════════════════════════════════════════════════════════════════════
# RECT
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class Rect:
    x:      int = 0
    y:      int = 0
    width:  int = 0
    height: int = 0

    # ── Derived properties ────────────────────────────────────────────
    @property
    def right(self)    -> int: return self.x + self.width
    @property
    def bottom(self)   -> int: return self.y + self.height
    @property
    def center_x(self) -> int: return self.x + self.width  // 2
    @property
    def center_y(self) -> int: return self.y + self.height // 2
    @property
    def top_left(self)     -> Point: return Point(self.x, self.y)
    @property
    def top_right(self)    -> Point: return Point(self.right, self.y)
    @property
    def bottom_left(self)  -> Point: return Point(self.x, self.bottom)
    @property
    def bottom_right(self) -> Point: return Point(self.right, self.bottom)
    @property
    def center(self)       -> Point: return Point(self.center_x, self.center_y)
    @property
    def area(self)         -> int:   return self.width * self.height

    # ── Mutation helpers ──────────────────────────────────────────────
    def with_padding(self, pad: "Margin") -> "Rect":
        """Return inner Rect after applying padding."""
        return Rect(
            x      = self.x + pad.left,
            y      = self.y + pad.top,
            width  = max(0, self.width  - pad.horizontal),
            height = max(0, self.height - pad.vertical),
        )

    def move_to(self, x: int, y: int) -> "Rect":
        return Rect(x, y, self.width, self.height)

    def resize(self, width: int, height: int) -> "Rect":
        return Rect(self.x, self.y, width, height)

    def expand(self, dx: int = 0, dy: int = 0) -> "Rect":
        return Rect(self.x - dx, self.y - dy,
                    self.width + dx*2, self.height + dy*2)

    def translate(self, dx: int = 0, dy: int = 0) -> "Rect":
        return Rect(self.x + dx, self.y + dy, self.width, self.height)

    # ── Spatial tests ─────────────────────────────────────────────────
    def contains_point(self, p: Point) -> bool:
        return self.x <= p.x <= self.right and self.y <= p.y <= self.bottom

    def intersects(self, other: "Rect") -> bool:
        """Return True if two rects overlap (touching edges = False)."""
        return (self.x < other.right  and self.right  > other.x and
                self.y < other.bottom and self.bottom > other.y)

    def contains_rect(self, other: "Rect") -> bool:
        """Return True if other is fully inside self."""
        return (self.x <= other.x and self.y <= other.y and
                self.right >= other.right and self.bottom >= other.bottom)

    def fits_in(self, container: "Rect") -> bool:
        """Return True if this rect fits within container dimensions."""
        return self.width <= container.width and self.height <= container.height

    # ── Serialisation ─────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y,
                "width": self.width, "height": self.height}

    def to_list(self) -> List[int]:
        return [self.x, self.y, self.x + self.width, self.y + self.height]

    def __repr__(self):
        return f"Rect(x={self.x}, y={self.y}, w={self.width}, h={self.height})"


# ════════════════════════════════════════════════════════════════════════════
# ANCHOR
# ════════════════════════════════════════════════════════════════════════════

class Anchor:
    """Named anchor points for alignment calculations."""
    TOP_LEFT     = "top_left"
    TOP_CENTER   = "top_center"
    TOP_RIGHT    = "top_right"
    MID_LEFT     = "mid_left"
    MID_CENTER   = "mid_center"
    MID_RIGHT    = "mid_right"
    BOT_LEFT     = "bot_left"
    BOT_CENTER   = "bot_center"
    BOT_RIGHT    = "bot_right"


def get_anchor_point(rect: Rect, anchor: str) -> Point:
    """Return the pixel Point for a named anchor on a Rect."""
    mapping = {
        Anchor.TOP_LEFT:   rect.top_left,
        Anchor.TOP_CENTER: Point(rect.center_x, rect.y),
        Anchor.TOP_RIGHT:  rect.top_right,
        Anchor.MID_LEFT:   Point(rect.x, rect.center_y),
        Anchor.MID_CENTER: rect.center,
        Anchor.MID_RIGHT:  Point(rect.right, rect.center_y),
        Anchor.BOT_LEFT:   rect.bottom_left,
        Anchor.BOT_CENTER: Point(rect.center_x, rect.bottom),
        Anchor.BOT_RIGHT:  rect.bottom_right,
    }
    return mapping.get(anchor, rect.top_left)


# ════════════════════════════════════════════════════════════════════════════
# CANVAS ZONE RECTS
# ════════════════════════════════════════════════════════════════════════════

CANVAS_RECT = Rect(0, 0, CANVAS_W, CANVAS_H)
CONTENT_RECT = Rect(CONTENT_X, CONTENT_Y, CONTENT_W, CONTENT_H)

HEADER_ZONE = Rect(CONTENT_X, ZONE_HEADER_Y, CONTENT_W, ZONE_HEADER_H)
BODY_ZONE   = Rect(CONTENT_X, ZONE_BODY_Y,   CONTENT_W, ZONE_BODY_H)
FOOTER_ZONE = Rect(CONTENT_X, ZONE_FOOTER_Y, CONTENT_W, ZONE_FOOTER_H)


# ════════════════════════════════════════════════════════════════════════════
# COLLISION DETECTION
# ════════════════════════════════════════════════════════════════════════════

def detect_overlaps(rects: List[Rect]) -> List[Tuple[int, int]]:
    """
    Return list of (i, j) index pairs where rects[i] overlaps rects[j].
    """
    overlaps = []
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if rects[i].intersects(rects[j]):
                overlaps.append((i, j))
    return overlaps


def has_overlaps(rects: List[Rect]) -> bool:
    """Return True if any two rects in the list overlap."""
    return len(detect_overlaps(rects)) > 0


def validate_layout(rects: List[Rect],
                    container: Rect = CONTENT_RECT) -> dict:
    """
    Validate a list of layout rects.

    Returns:
        dict with keys:
          valid        : bool
          overlaps     : list of (i,j) pairs
          out_of_bounds: list of rect indices outside container
          total_height : int
    """
    overlaps      = detect_overlaps(rects)
    out_of_bounds = [i for i, r in enumerate(rects)
                     if not container.contains_rect(r)]
    total_h       = (max(r.bottom for r in rects) - min(r.y for r in rects)
                     if rects else 0)

    return {
        "valid":         len(overlaps) == 0 and len(out_of_bounds) == 0,
        "overlaps":      overlaps,
        "out_of_bounds": out_of_bounds,
        "total_height":  total_h,
    }


# ════════════════════════════════════════════════════════════════════════════
# COORDINATE UTILITIES
# ════════════════════════════════════════════════════════════════════════════

def center_rect_in(inner: Rect, outer: Rect) -> Rect:
    """Return inner Rect centered within outer Rect."""
    cx = outer.x + (outer.width  - inner.width)  // 2
    cy = outer.y + (outer.height - inner.height) // 2
    return inner.move_to(cx, cy)


def align_rect(rect: Rect, container: Rect, align: str = "left") -> Rect:
    """
    Horizontally align a rect within a container.

    Args:
        align: "left" | "center" | "right"
    """
    if align == "center":
        x = container.x + (container.width - rect.width) // 2
    elif align == "right":
        x = container.right - rect.width
    else:
        x = container.x
    return rect.move_to(x, rect.y)


def stack_rects_vertical(rects: List[Rect],
                          start_y: int,
                          x: int,
                          gap: int = 0) -> List[Rect]:
    """
    Return new list of Rects stacked vertically from start_y with gap.
    """
    result = []
    cy = start_y
    for r in rects:
        result.append(r.move_to(x, cy))
        cy += r.height + gap
    return result


def distribute_horizontal(rects: List[Rect],
                           container: Rect,
                           gap: int = 12) -> List[Rect]:
    """
    Distribute rects evenly across container width.
    All rects get equal width.
    """
    if not rects:
        return []
    n      = len(rects)
    total_gap = gap * (n - 1)
    item_w    = (container.width - total_gap) // n
    result    = []
    cx        = container.x
    for r in rects:
        result.append(Rect(cx, r.y, item_w, r.height))
        cx += item_w + gap
    return result
