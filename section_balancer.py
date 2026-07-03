"""
section_balancer.py
===================
Linkphobot - Phase 5: Layout Engine
Section Height Balancing & Weight Distribution

Algorithms:
  - Visual weight scoring per section
  - Proportional height allocation
  - Height floor/ceiling enforcement
  - Carousel page balancing
  - Two-column section pairing
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coordinate_system import (
    Rect, CONTENT_X, CONTENT_W
)
from typing import List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════════════
# HEIGHT CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

MIN_SECTION_HEIGHT  = 90
MAX_SECTION_HEIGHT  = 320
DEFAULT_SECTION_H   = 150

# Internal padding assumed when estimating
SECTION_PAD_V   = 22
SECTION_PAD_H   = 28
HEADING_H_EST   = 36    # heading row height estimate
BULLET_H_EST    = 30    # per-bullet height estimate (single line)
BULLET_GAP      = 10
SECTION_ICON_H  = 36
HEAD_BULLET_GAP = 14    # gap between heading and first bullet


# ════════════════════════════════════════════════════════════════════════════
# VISUAL WEIGHT SCORER
# ════════════════════════════════════════════════════════════════════════════

def score_section_weight(section: dict) -> float:
    """
    Assign a visual weight score to a section based on content volume.

    Scoring:
      - Heading length:    0.5 pts per 10 chars
      - Bullet count:      2.0 pts per bullet
      - Avg bullet length: 0.3 pts per 10 chars
      - Has icon:          +0.5

    Higher score -> section needs more vertical space.

    Args:
        section: dict with keys "heading", "content", "icon_suggestion"

    Returns:
        float weight score
    """
    heading  = section.get("heading", "")
    bullets  = section.get("content", [])
    icon     = section.get("icon_suggestion", "")

    score  = len(heading) * 0.05
    score += len(bullets) * 2.0
    if bullets:
        avg_len = sum(len(b) for b in bullets) / len(bullets)
        score  += avg_len * 0.03
    if icon:
        score += 0.5

    return max(1.0, score)


def score_all_sections(sections: List[dict]) -> List[float]:
    """Return weight scores for all sections."""
    return [score_section_weight(s) for s in sections]


# ════════════════════════════════════════════════════════════════════════════
# HEIGHT ESTIMATOR
# ════════════════════════════════════════════════════════════════════════════

def estimate_section_height(section: dict,
                              content_width: int = CONTENT_W,
                              pad_v: int = SECTION_PAD_V,
                              pad_h: int = SECTION_PAD_H,
                              bullet_h: int = BULLET_H_EST,
                              bullet_gap: int = BULLET_GAP) -> int:
    """
    Estimate pixel height for a section card.

    Uses character-count heuristic for wrapping estimation.

    Returns:
        estimated height in pixels
    """
    bullets  = section.get("content", [])
    heading  = section.get("heading", "")

    inner_w  = content_width - pad_h * 2 - 13  # accent bar

    # Heading: estimate wrap lines
    chars_per_line_head = max(10, inner_w // 16)   # ~16px per char at 28px font
    head_lines = max(1, -(-len(heading) // chars_per_line_head))
    head_h     = max(SECTION_ICON_H, head_lines * 32)

    # Bullets
    chars_per_line_bull = max(10, (inner_w - 20) // 11)  # ~11px per char at 21px
    total_bull_h = 0
    for b in bullets:
        lines = max(1, -(-len(b) // chars_per_line_bull))
        total_bull_h += lines * (bullet_h - 4) + bullet_gap
    if bullets:
        total_bull_h -= bullet_gap

    total = (pad_v
             + head_h + HEAD_BULLET_GAP
             + total_bull_h
             + pad_v)

    return max(MIN_SECTION_HEIGHT, min(MAX_SECTION_HEIGHT, total))


def estimate_all_section_heights(sections: List[dict],
                                  content_width: int = CONTENT_W) -> List[int]:
    """Estimate heights for all sections."""
    return [estimate_section_height(s, content_width) for s in sections]


# ════════════════════════════════════════════════════════════════════════════
# PROPORTIONAL HEIGHT ALLOCATOR
# ════════════════════════════════════════════════════════════════════════════

def allocate_heights_proportional(sections: List[dict],
                                   available_height: int,
                                   n_gaps: Optional[int] = None,
                                   gap_size: int = 14) -> List[int]:
    """
    Allocate section heights proportionally by visual weight.
    Ensures no section goes below MIN_SECTION_HEIGHT.

    Algorithm:
      1. Score each section
      2. Deduct gap budget from available height
      3. Distribute remainder by weight ratio
      4. Clamp each height to [min, max]
      5. Redistribute unclaimed pixels to largest sections

    Args:
        sections        : list of section dicts
        available_height: total pixels for sections + gaps
        n_gaps          : number of gaps (default: n_sections - 1)
        gap_size        : pixels per gap

    Returns:
        list of allocated heights
    """
    if not sections:
        return []

    n      = len(sections)
    n_gaps = n - 1 if n_gaps is None else n_gaps

    # Deduct gap budget
    gap_budget      = gap_size * n_gaps
    height_budget   = max(MIN_SECTION_HEIGHT * n, available_height - gap_budget)

    # Compute weights
    weights     = score_all_sections(sections)
    total_weight= sum(weights)

    # Initial allocation
    heights = []
    for w in weights:
        h = int(height_budget * w / total_weight)
        h = max(MIN_SECTION_HEIGHT, min(MAX_SECTION_HEIGHT, h))
        heights.append(h)

    # Redistribution: if we're over/under budget, adjust
    allocated   = sum(heights)
    diff        = height_budget - allocated

    if diff != 0:
        # Apply diff to largest section
        idx = heights.index(max(heights))
        heights[idx] = max(MIN_SECTION_HEIGHT,
                           min(MAX_SECTION_HEIGHT, heights[idx] + diff))

    return heights


def compress_heights_to_fit(heights: List[int],
                              available: int,
                              gap: int = 14) -> List[int]:
    """
    Proportionally compress heights until they fit in available space.

    Args:
        heights  : list of required heights
        available: total available pixels (including gaps)
        gap      : gap between sections

    Returns:
        list of compressed heights
    """
    n          = len(heights)
    gap_total  = gap * max(0, n - 1)
    h_budget   = available - gap_total

    if sum(heights) <= h_budget:
        return heights

    scale  = h_budget / max(1, sum(heights))
    result = [max(MIN_SECTION_HEIGHT, int(h * scale)) for h in heights]

    # Fine-tune: trim from tallest until fits
    while sum(result) > h_budget and any(r > MIN_SECTION_HEIGHT for r in result):
        idx = result.index(max(result))
        if result[idx] <= MIN_SECTION_HEIGHT:
            break
        result[idx] -= 1

    return result


# ════════════════════════════════════════════════════════════════════════════
# CAROUSEL PAGE BALANCER
# ════════════════════════════════════════════════════════════════════════════

def balance_sections_across_pages(sections: List[dict],
                                   max_sections_page1: int = 2,
                                   max_sections_other: int = 3) -> List[List[dict]]:
    """
    Split sections into balanced carousel pages.

    Page 1 gets fewer sections (header takes space).
    Subsequent pages get more sections.

    Args:
        sections             : full section list
        max_sections_page1   : max sections on first page
        max_sections_other   : max sections on other pages

    Returns:
        list of section lists, one per page
    """
    if not sections:
        return [[]]

    pages = []
    pages.append(sections[:max_sections_page1])
    rest  = sections[max_sections_page1:]

    while rest:
        pages.append(rest[:max_sections_other])
        rest = rest[max_sections_other:]

    return pages


def score_page_balance(page_sections: List[List[dict]]) -> float:
    """
    Score how balanced the pages are (0 = perfect, higher = worse).
    Compares total visual weight per page.
    """
    if len(page_sections) <= 1:
        return 0.0

    page_weights = []
    for page in page_sections:
        total = sum(score_section_weight(s) for s in page)
        page_weights.append(total)

    avg  = sum(page_weights) / len(page_weights)
    diff = sum(abs(w - avg) for w in page_weights)
    return diff / max(1, avg)


# ════════════════════════════════════════════════════════════════════════════
# TWO-COLUMN PAIRING
# ════════════════════════════════════════════════════════════════════════════

def pair_sections_for_two_column(sections: List[dict]) -> List[Tuple]:
    """
    Pair sections for a 2-column layout.

    Pairs sections by adjacent index: (0,1), (2,3), ...
    Lone section at end is placed full-width.

    Returns:
        list of (section_a, section_b | None) tuples
    """
    pairs = []
    i = 0
    while i < len(sections):
        if i + 1 < len(sections):
            pairs.append((sections[i], sections[i + 1]))
            i += 2
        else:
            pairs.append((sections[i], None))
            i += 1
    return pairs


def equal_height_for_pair(sec_a: dict, sec_b: dict) -> int:
    """
    Return the larger estimated height for a section pair,
    so both cards in a row have equal height.
    """
    h_a = estimate_section_height(sec_a)
    h_b = estimate_section_height(sec_b) if sec_b else 0
    return max(h_a, h_b)


# ════════════════════════════════════════════════════════════════════════════
# BALANCE REPORT
# ════════════════════════════════════════════════════════════════════════════

def generate_balance_report(sections: List[dict],
                             available_h: int) -> dict:
    """
    Generate a full balance analysis report for sections.

    Returns:
        dict with weights, estimated heights, allocated heights, balance score
    """
    weights    = score_all_sections(sections)
    estimated  = estimate_all_section_heights(sections)
    allocated  = allocate_heights_proportional(sections, available_h)
    pages      = balance_sections_across_pages(sections)
    balance    = score_page_balance(pages)

    return {
        "n_sections":       len(sections),
        "available_h":      available_h,
        "weights":          [round(w, 2) for w in weights],
        "estimated_h":      estimated,
        "allocated_h":      allocated,
        "total_estimated":  sum(estimated),
        "total_allocated":  sum(allocated),
        "pages":            len(pages),
        "page_sizes":       [len(p) for p in pages],
        "balance_score":    round(balance, 3),
        "fits_single_page": sum(estimated) <= available_h,
    }
