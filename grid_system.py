"""
grid_system.py
==============
Linkphobot - Phase 5: Layout Engine
12-Column Grid System for 1080px Canvas

Provides:
  - 12-column grid with gutters
  - Named column spans (full, two-thirds, half, one-third, quarter)
  - Grid cell Rect generation
  - Row builder for horizontal layouts
  - Stat card, key point, and badge grid helpers
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coordinate_system import (
    Rect, CANVAS_W, MARGIN_H, CONTENT_W, CONTENT_X
)
from typing import List


# ════════════════════════════════════════════════════════════════════════════
# GRID CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

GRID_COLUMNS   = 12
GRID_GUTTER    = 16          # px between columns
GRID_MARGIN    = MARGIN_H    # left/right canvas margin (54px)

# Column width = (content_width - gutters_total) / columns
_TOTAL_GUTTERS = GRID_GUTTER * (GRID_COLUMNS - 1)
COLUMN_WIDTH   = (CONTENT_W - _TOTAL_GUTTERS) // GRID_COLUMNS   # ~72px


# ════════════════════════════════════════════════════════════════════════════
# SPAN NAMES  –  convenience constants
# ════════════════════════════════════════════════════════════════════════════

SPAN_FULL        = 12    # 972px
SPAN_TWO_THIRDS  = 8     # ~648px
SPAN_HALF        = 6     # ~486px
SPAN_ONE_THIRD   = 4     # ~324px
SPAN_QUARTER     = 3     # ~243px
SPAN_SIXTH       = 2     # ~162px
SPAN_TWELFTH     = 1     # ~72px

# Human-readable name -> span columns
SPAN_MAP = {
    "full":        SPAN_FULL,
    "two_thirds":  SPAN_TWO_THIRDS,
    "half":        SPAN_HALF,
    "one_third":   SPAN_ONE_THIRD,
    "quarter":     SPAN_QUARTER,
    "sixth":       SPAN_SIXTH,
    "twelfth":     SPAN_TWELFTH,
}


# ════════════════════════════════════════════════════════════════════════════
# CORE GRID CALCULATOR
# ════════════════════════════════════════════════════════════════════════════

def column_width(span: int) -> int:
    """
    Return pixel width for a given column span.

    Args:
        span: number of columns (1-12)

    Returns:
        pixel width including internal gutters, excluding outer gutters
    """
    span   = max(1, min(GRID_COLUMNS, span))
    width  = COLUMN_WIDTH * span + GRID_GUTTER * (span - 1)
    return width


def column_x(col_start: int) -> int:
    """
    Return the x pixel position for a column start index (0-based).

    Args:
        col_start: 0-based column index

    Returns:
        absolute x pixel on canvas
    """
    col_start = max(0, min(GRID_COLUMNS - 1, col_start))
    return CONTENT_X + col_start * (COLUMN_WIDTH + GRID_GUTTER)


def grid_rect(col_start: int, span: int, y: int, height: int) -> Rect:
    """
    Return a Rect positioned on the grid.

    Args:
        col_start : 0-based starting column (0-11)
        span      : number of columns to span (1-12)
        y         : top y position in pixels
        height    : height in pixels

    Returns:
        Rect with correct x, y, width, height
    """
    x = column_x(col_start)
    w = column_width(span)
    return Rect(x, y, w, height)


def full_width_rect(y: int, height: int) -> Rect:
    """Return a full-width content rect at given y."""
    return Rect(CONTENT_X, y, CONTENT_W, height)


# ════════════════════════════════════════════════════════════════════════════
# ROW BUILDER  –  horizontal cell distribution
# ════════════════════════════════════════════════════════════════════════════

def build_row(y: int, height: int, spans: List[int],
              gutter: int = GRID_GUTTER) -> List[Rect]:
    """
    Build a horizontal row of grid cells with given column spans.

    Args:
        y      : top y position
        height : row height
        spans  : list of column spans, must sum to <= 12
        gutter : gap between cells

    Returns:
        list of Rect objects

    Example:
        # Three equal columns
        rects = build_row(y=400, height=120, spans=[4, 4, 4])
    """
    rects = []
    cx    = CONTENT_X
    for span in spans:
        w = column_width(span)
        rects.append(Rect(cx, y, w, height))
        cx += w + gutter
    return rects


def build_equal_row(y: int, height: int, n_cells: int,
                    gutter: int = GRID_GUTTER) -> List[Rect]:
    """
    Build a row of n equally-sized cells filling the full content width.

    Args:
        n_cells: number of cells (1-4 recommended)

    Returns:
        list of n Rect objects
    """
    total_gutter = gutter * (n_cells - 1)
    cell_w       = (CONTENT_W - total_gutter) // n_cells
    rects        = []
    cx           = CONTENT_X
    for _ in range(n_cells):
        rects.append(Rect(cx, y, cell_w, height))
        cx += cell_w + gutter
    return rects


# ════════════════════════════════════════════════════════════════════════════
# NAMED LAYOUT PRESETS
# ════════════════════════════════════════════════════════════════════════════

def stat_card_rects(y: int, height: int, n_stats: int,
                    gutter: int = 12) -> List[Rect]:
    """
    Return Rect list for n_stats stat cards in a horizontal row.
    Supports 1, 2, or 3 stat cards.
    """
    n = min(3, max(1, n_stats))
    return build_equal_row(y, height, n, gutter)


def two_column_section_rects(y: int,
                               left_h: int, right_h: int,
                               gutter: int = GRID_GUTTER) -> List[Rect]:
    """
    Return two half-width Rects for a 2-column section layout.
    """
    lw = column_width(6)
    rw = CONTENT_W - lw - gutter
    return [
        Rect(CONTENT_X, y, lw, left_h),
        Rect(CONTENT_X + lw + gutter, y, rw, right_h),
    ]


def key_point_row_rects(y: int, height: int, n_points: int,
                         gutter: int = GRID_GUTTER) -> List[Rect]:
    """
    Return Rect list for key point items in a horizontal row.
    Up to 3 points side-by-side; 4+ goes full-width stacked.
    """
    if n_points <= 3:
        return build_equal_row(y, height, n_points, gutter)
    else:
        return [full_width_rect(y + i * (height + gutter), height)
                for i in range(n_points)]


# ════════════════════════════════════════════════════════════════════════════
# GRID DEBUG  –  for visualisation / testing
# ════════════════════════════════════════════════════════════════════════════

def get_all_column_rects(y: int = 0, height: int = 20) -> List[Rect]:
    """Return all 12 individual column rects for a given y/height."""
    return [grid_rect(col, 1, y, height) for col in range(GRID_COLUMNS)]


def grid_summary() -> str:
    """Return a human-readable grid summary string."""
    lines = [
        f"Grid System - 1080px Canvas",
        f"  Columns:      {GRID_COLUMNS}",
        f"  Gutter:       {GRID_GUTTER}px",
        f"  Margin:       {GRID_MARGIN}px",
        f"  Content W:    {CONTENT_W}px",
        f"  Column W:     {COLUMN_WIDTH}px (1 col)",
        "",
        "  Span widths:",
    ]
    for name, span in SPAN_MAP.items():
        w = column_width(span)
        lines.append(f"    {name:12s} ({span:2d} cols) = {w}px")
    return "\n".join(lines)
