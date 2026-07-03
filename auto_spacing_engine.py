"""
auto_spacing_engine.py
======================
Linkphobot - Phase 5: Layout Engine
Dynamic Spacing & Whitespace Calculator

Algorithms:
  - Budget-based spacing (total available / block count)
  - Golden ratio vertical rhythm
  - Block gap distribution
  - Breathing room guarantees
  - Footer anchoring (always at bottom)
  - Spacing scaling by content density
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coordinate_system import (
    CANVAS_H, CANVAS_W, MARGIN_V, MARGIN_H,
    CONTENT_H, CONTENT_W, CONTENT_X, CONTENT_Y
)
from typing import List, Optional


# ════════════════════════════════════════════════════════════════════════════
# SPACING CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

# Minimum gaps between blocks (pixels)
MIN_GAP_AFTER_HEADER    = 16
MIN_GAP_BETWEEN_SECTION = 10
MIN_GAP_BEFORE_STATS    = 14
MIN_GAP_BEFORE_KEYPOINT = 14
MIN_GAP_BEFORE_FOOTER   = 14

# Comfortable gaps (used when space allows)
COMFORTABLE_GAP_HEADER   = 24
COMFORTABLE_GAP_SECTION  = 16
COMFORTABLE_GAP_STATS    = 22
COMFORTABLE_GAP_KEYPOINT = 18
COMFORTABLE_GAP_FOOTER   = 20

# Golden ratio constant
PHI = 1.618033988749895


# ════════════════════════════════════════════════════════════════════════════
# SPACING PROFILE
# ════════════════════════════════════════════════════════════════════════════

class SpacingProfile:
    """
    Resolved spacing values for a specific layout configuration.
    All values in pixels.
    """
    def __init__(self,
                 gap_after_header:   int = COMFORTABLE_GAP_HEADER,
                 gap_between_section:int = COMFORTABLE_GAP_SECTION,
                 gap_before_stats:   int = COMFORTABLE_GAP_STATS,
                 gap_before_keypoint:int = COMFORTABLE_GAP_KEYPOINT,
                 gap_before_footer:  int = COMFORTABLE_GAP_FOOTER,
                 section_pad_v:      int = 22,
                 section_pad_h:      int = 28,
                 header_pad_v:       int = 36,
                 header_pad_h:       int = 44,
                 stats_pad_v:        int = 24,
                 footer_pad_v:       int = 20):
        self.gap_after_header    = gap_after_header
        self.gap_between_section = gap_between_section
        self.gap_before_stats    = gap_before_stats
        self.gap_before_keypoint = gap_before_keypoint
        self.gap_before_footer   = gap_before_footer
        self.section_pad_v       = section_pad_v
        self.section_pad_h       = section_pad_h
        self.header_pad_v        = header_pad_v
        self.header_pad_h        = header_pad_h
        self.stats_pad_v         = stats_pad_v
        self.footer_pad_v        = footer_pad_v

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    def __repr__(self):
        return (f"SpacingProfile(gap_section={self.gap_between_section}, "
                f"gap_header={self.gap_after_header})")


# ════════════════════════════════════════════════════════════════════════════
# DENSITY-BASED SPACING RESOLVER
# ════════════════════════════════════════════════════════════════════════════

def resolve_spacing(n_sections: int,
                    has_stats: bool = True,
                    has_keypoints: bool = True,
                    canvas_h: int = CANVAS_H) -> SpacingProfile:
    """
    Resolve appropriate spacing for a given content density.

    Algorithm:
      1. Calculate fixed height used (margins + header min + footer min)
      2. Calculate variable height used by sections
      3. Compute available breathing room
      4. Distribute breathing room across gaps proportionally

    Args:
        n_sections  : number of section cards
        has_stats   : whether stats block is present
        has_keypoints: whether key points block is present
        canvas_h    : canvas pixel height

    Returns:
        SpacingProfile with all gap values resolved
    """
    usable_h = canvas_h - MARGIN_V * 2

    # Estimate fixed block heights (conservative)
    header_min   = 180
    section_min  = 100
    stats_min    = 130 if has_stats    else 0
    kp_min       = 110 if has_keypoints else 0
    footer_min   = 110

    # Total minimum content
    sections_min = section_min * n_sections
    total_min    = (header_min + sections_min + stats_min
                    + kp_min + footer_min)

    # Total minimum gaps (use min gaps)
    n_gaps = (1                              # after header
              + max(0, n_sections - 1)       # between sections
              + (1 if has_stats    else 0)   # before stats
              + (1 if has_keypoints else 0)  # before kp
              + 1)                           # before footer
    min_gap_total = (
        MIN_GAP_AFTER_HEADER
        + MIN_GAP_BETWEEN_SECTION * max(0, n_sections - 1)
        + (MIN_GAP_BEFORE_STATS   if has_stats     else 0)
        + (MIN_GAP_BEFORE_KEYPOINT if has_keypoints else 0)
        + MIN_GAP_BEFORE_FOOTER
    )

    # Available breathing room
    breathing_room = max(0, usable_h - total_min - min_gap_total)

    # Distribute: more space to header gap and section gaps
    # Proportions: header(3), section(2), stats(2), kp(2), footer(1)
    total_weight = 3 + 2 * max(1, n_sections - 1) + (2 if has_stats else 0) + (2 if has_keypoints else 0) + 1
    per_unit     = breathing_room / max(1, total_weight)

    gap_header   = MIN_GAP_AFTER_HEADER    + int(per_unit * 3)
    gap_section  = MIN_GAP_BETWEEN_SECTION + int(per_unit * 2)
    gap_stats    = MIN_GAP_BEFORE_STATS    + int(per_unit * 2) if has_stats     else 0
    gap_kp       = MIN_GAP_BEFORE_KEYPOINT + int(per_unit * 2) if has_keypoints else 0
    gap_footer   = MIN_GAP_BEFORE_FOOTER   + int(per_unit * 1)

    # Clamp to comfortable maximums
    gap_header  = min(gap_header,  COMFORTABLE_GAP_HEADER  * 2)
    gap_section = min(gap_section, COMFORTABLE_GAP_SECTION * 2)
    gap_footer  = min(gap_footer,  COMFORTABLE_GAP_FOOTER  * 2)

    # Scale interior padding based on sections count
    density_scale = max(0.75, 1.0 - (n_sections - 3) * 0.06)
    pad_v = max(14, int(22 * density_scale))
    pad_h = max(20, int(28 * density_scale))

    return SpacingProfile(
        gap_after_header    = gap_header,
        gap_between_section = gap_section,
        gap_before_stats    = gap_stats,
        gap_before_keypoint = gap_kp,
        gap_before_footer   = gap_footer,
        section_pad_v       = pad_v,
        section_pad_h       = pad_h,
        header_pad_v        = max(24, int(36 * density_scale)),
        header_pad_h        = max(28, int(44 * density_scale)),
        stats_pad_v         = max(16, int(24 * density_scale)),
        footer_pad_v        = 20,
    )


# ════════════════════════════════════════════════════════════════════════════
# VERTICAL BUDGET CALCULATOR
# ════════════════════════════════════════════════════════════════════════════

def compute_vertical_budget(block_heights: List[int],
                             gaps: List[int],
                             canvas_h: int = CANVAS_H,
                             margin_v: int = MARGIN_V) -> dict:
    """
    Calculate total vertical usage and available surplus/deficit.

    Args:
        block_heights : list of block heights in pixels
        gaps          : list of gaps between blocks (len = len(blocks) - 1)
        canvas_h      : canvas height
        margin_v      : top + bottom margin (total)

    Returns:
        dict with: total_used, available, surplus, deficit, overflow
    """
    usable     = canvas_h - margin_v * 2
    total_h    = sum(block_heights)
    total_gaps = sum(gaps[:max(0, len(block_heights) - 1)])
    total_used = total_h + total_gaps
    surplus    = max(0, usable - total_used)
    deficit    = max(0, total_used - usable)

    return {
        "usable":      usable,
        "total_blocks":total_h,
        "total_gaps":  total_gaps,
        "total_used":  total_used,
        "surplus":     surplus,
        "deficit":     deficit,
        "overflow":    deficit > 0,
        "usage_pct":   round(total_used / usable * 100, 1),
    }


# ════════════════════════════════════════════════════════════════════════════
# GOLDEN RATIO SPACING
# ════════════════════════════════════════════════════════════════════════════

def golden_ratio_split(total_height: int) -> tuple:
    """
    Split a height value into golden ratio proportions.

    Returns:
        (major, minor) where major / minor = phi
    """
    major = int(total_height / PHI)
    minor = total_height - major
    return major, minor


def golden_gap_sequence(n_gaps: int, total_gap_budget: int) -> List[int]:
    """
    Distribute gap budget across n gaps using golden ratio weighting.
    First gap (after header) gets the largest share.

    Args:
        n_gaps           : number of gaps
        total_gap_budget : total pixels to distribute

    Returns:
        list of gap values (largest first)
    """
    if n_gaps <= 0:
        return []
    if n_gaps == 1:
        return [total_gap_budget]

    # Generate weights: 1 + (n-1)*1/phi, 1 + (n-2)*1/phi, ...
    weights = [1.0 + (n_gaps - 1 - i) / PHI for i in range(n_gaps)]
    total_w = sum(weights)
    gaps    = [max(8, int(w / total_w * total_gap_budget)) for w in weights]

    # Redistribute rounding error to first gap
    diff = total_gap_budget - sum(gaps)
    gaps[0] += diff

    return gaps


# ════════════════════════════════════════════════════════════════════════════
# FOOTER ANCHOR
# ════════════════════════════════════════════════════════════════════════════

def anchor_footer_y(footer_h: int,
                    canvas_h: int = CANVAS_H,
                    margin_v: int = MARGIN_V) -> int:
    """
    Return the y position to pin footer to the bottom of the canvas.
    """
    return canvas_h - margin_v - footer_h


def compute_footer_gap(last_block_bottom: int,
                        footer_y: int) -> int:
    """
    Compute actual gap between last content block and footer.
    Returns 0 if footer is above last block (overlap situation).
    """
    return max(0, footer_y - last_block_bottom)


# ════════════════════════════════════════════════════════════════════════════
# SECTION GAP DISTRIBUTOR
# ════════════════════════════════════════════════════════════════════════════

def distribute_section_gaps(n_sections: int,
                              available_h: int,
                              section_heights: List[int],
                              min_gap: int = MIN_GAP_BETWEEN_SECTION) -> List[int]:
    """
    Distribute available space between sections as gaps.

    Algorithm:
      1. Calculate space remaining after all sections
      2. Ensure minimum gap between each
      3. Distribute surplus evenly

    Args:
        n_sections     : number of sections
        available_h    : total pixels available for sections + gaps
        section_heights: list of section heights
        min_gap        : minimum gap between any two sections

    Returns:
        list of n_sections-1 gap values
    """
    if n_sections <= 1:
        return []

    n_gaps       = n_sections - 1
    total_sec_h  = sum(section_heights)
    min_gap_total= min_gap * n_gaps
    surplus      = max(0, available_h - total_sec_h - min_gap_total)
    extra_per_gap= surplus // max(1, n_gaps)

    return [min_gap + extra_per_gap] * n_gaps
