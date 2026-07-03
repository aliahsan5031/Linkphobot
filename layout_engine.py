"""
layout_engine.py
================
Linkphobot - Phase 5: Layout Engine
Master Layout Orchestrator

Pipeline:
  1. Accept Phase 1 content dict
  2. Score and estimate all block heights
  3. Resolve spacing via auto_spacing_engine
  4. Balance section heights via section_balancer
  5. Place all blocks using coordinate_system
  6. Validate no overlaps or out-of-bounds
  7. Return LayoutPlan with every block's Rect

Public API:
  LayoutEngine.compute(content) -> LayoutPlan
  LayoutPlan.to_dict()          -> serialisable dict
  generate_layout_plan(content) -> LayoutPlan   (one-liner)
"""

import os
import sys
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coordinate_system import (
    Rect, Point, Margin, CANVAS_W, CANVAS_H,
    MARGIN_H, MARGIN_V, CONTENT_W, CONTENT_X, CONTENT_Y,
    CONTENT_RECT, validate_layout, stack_rects_vertical,
)
from grid_system import (
    full_width_rect, stat_card_rects, build_equal_row,
    grid_summary,
)
from auto_spacing_engine import (
    SpacingProfile, resolve_spacing,
    compute_vertical_budget, anchor_footer_y,
    distribute_section_gaps,
)
from section_balancer import (
    estimate_section_height, estimate_all_section_heights,
    allocate_heights_proportional, compress_heights_to_fit,
    balance_sections_across_pages, generate_balance_report,
    MIN_SECTION_HEIGHT,
)


# ════════════════════════════════════════════════════════════════════════════
# BLOCK PLAN  –  resolved Rect + metadata for one block
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class BlockPlan:
    block_id:    str
    block_type:  str          # header | section | stats | key_points | footer
    rect:        Rect
    page:        int = 1      # which carousel page this block belongs to
    metadata:    dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "block_id":   self.block_id,
            "block_type": self.block_type,
            "rect":       self.rect.to_dict(),
            "page":       self.page,
            "metadata":   self.metadata,
        }


# ════════════════════════════════════════════════════════════════════════════
# PAGE PLAN  –  all blocks on one carousel page
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class PagePlan:
    page_number:   int
    blocks:        List[BlockPlan] = field(default_factory=list)
    canvas_w:      int = CANVAS_W
    canvas_h:      int = CANVAS_H
    height_used:   int = 0
    overflow:      bool = False
    spacing:       Optional[SpacingProfile] = None

    def add_block(self, block: BlockPlan) -> None:
        self.blocks.append(block)
        self.height_used = (max(b.rect.bottom for b in self.blocks)
                            - MARGIN_V)

    def get_block(self, block_type: str) -> Optional[BlockPlan]:
        for b in self.blocks:
            if b.block_type == block_type:
                return b
        return None

    def get_sections(self) -> List[BlockPlan]:
        return [b for b in self.blocks if b.block_type == "section"]

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "canvas_w":    self.canvas_w,
            "canvas_h":    self.canvas_h,
            "height_used": self.height_used,
            "overflow":    self.overflow,
            "blocks":      [b.to_dict() for b in self.blocks],
        }


# ════════════════════════════════════════════════════════════════════════════
# LAYOUT PLAN  –  root object (may contain multiple pages)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class LayoutPlan:
    topic:         str
    title:         str
    color_theme:   str
    content_type:  str
    generated_at:  str
    pages:         List[PagePlan] = field(default_factory=list)
    total_pages:   int = 0
    balance_report: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "topic":          self.topic,
            "title":          self.title,
            "color_theme":    self.color_theme,
            "content_type":   self.content_type,
            "generated_at":   self.generated_at,
            "total_pages":    self.total_pages,
            "pages":          [p.to_dict() for p in self.pages],
            "balance_report": self.balance_report,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        return path


# ════════════════════════════════════════════════════════════════════════════
# BLOCK HEIGHT ESTIMATORS  –  non-section blocks
# ════════════════════════════════════════════════════════════════════════════

def _estimate_header_height(title: str, subtitle: str,
                              pad_v: int = 36) -> int:
    """Estimate header card height from text content."""
    t_len  = len(title)
    s_len  = len(subtitle)

    # Title: wider chars, bigger font (~50px per line at 62px font)
    t_lines = max(1, -(-t_len // 18))
    t_h     = t_lines * 72 + 8

    # Subtitle: smaller font (~25px per line at 27px font)
    s_lines = max(1, -(-s_len // 38))
    s_h     = s_lines * 34

    badge_h = 36
    total   = pad_v + badge_h + 14 + t_h + 16 + s_h + pad_v
    return max(180, min(520, total))


def _estimate_stats_height(n_stats: int, pad_v: int = 24) -> int:
    """Estimate stats block height."""
    if n_stats == 0:
        return 0
    return pad_v + 36 + 16 + 110 + pad_v   # heading + item_h


def _estimate_keypoints_height(key_points: list,
                                 pad_v: int = 22) -> int:
    """Estimate key points block height."""
    if not key_points:
        return 0
    per_item = 30    # ~30px per key point line
    return pad_v + 36 + 14 + len(key_points) * (per_item + 10) + pad_v


def _estimate_footer_height(cta: str, hashtags: list,
                              pad_v: int = 20) -> int:
    """Estimate footer block height."""
    cta_h  = max(1, -(-len(cta) // 42)) * 30
    tags_h = 28
    return pad_v + cta_h + 14 + 2 + 14 + tags_h + pad_v


# ════════════════════════════════════════════════════════════════════════════
# LAYOUT ENGINE  –  main class
# ════════════════════════════════════════════════════════════════════════════

class LayoutEngine:
    """
    Phase 5 Layout Engine.

    Computes pixel-accurate Rect positions for every block
    in a LinkedIn infographic, supporting multi-page carousel output.

    Usage:
        engine = LayoutEngine()
        plan   = engine.compute(content_dict)
        plan.save("layout_plan.json")
    """

    def __init__(self,
                 canvas_w: int = CANVAS_W,
                 canvas_h: int = CANVAS_H,
                 verbose:  bool = True):
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.verbose  = verbose

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    # ── Main entry ─────────────────────────────────────────────────────────
    def compute(self, content: dict) -> LayoutPlan:
        """
        Compute the complete layout plan for an infographic.

        Args:
            content: Phase 1 content dict

        Returns:
            LayoutPlan with Rects for every block on every page
        """
        title       = content.get("title", "")
        subtitle    = content.get("subtitle", "")
        sections    = content.get("sections", [])
        statistics  = content.get("statistics", [])
        key_points  = content.get("key_points", [])
        cta         = content.get("call_to_action", "")
        hashtags    = content.get("hashtags", [])
        color_theme = content.get("color_theme", "professional")
        c_type      = content.get("content_type", "educational")
        topic       = content.get("topic", title)

        self._log("\n[Layout Engine] Computing layout...")
        self._log(f"  Sections: {len(sections)}  Stats: {len(statistics)}  KP: {len(key_points)}")

        has_stats = len(statistics) >= 1
        has_kp    = len(key_points) >= 1

        # ── Resolve spacing ───────────────────────────────────────────
        spacing = resolve_spacing(len(sections), has_stats, has_kp)
        self._log(f"  Spacing: gap_section={spacing.gap_between_section}px")

        # ── Estimate all heights ──────────────────────────────────────
        header_h  = _estimate_header_height(title, subtitle, spacing.header_pad_v)
        stats_h   = _estimate_stats_height(len(statistics), spacing.stats_pad_v)
        kp_h      = _estimate_keypoints_height(key_points)
        footer_h  = _estimate_footer_height(cta, hashtags)
        sec_hs    = estimate_all_section_heights(sections)

        self._log(f"  Header:  {header_h}px")
        self._log(f"  Footer:  {footer_h}px")
        if has_stats:  self._log(f"  Stats:   {stats_h}px")
        if has_kp:     self._log(f"  KP:      {kp_h}px")

        # ── Balance report ────────────────────────────────────────────
        usable_h = self.canvas_h - MARGIN_V * 2
        fixed_h  = (header_h
                    + (stats_h  + spacing.gap_before_stats    if has_stats else 0)
                    + (kp_h     + spacing.gap_before_keypoint if has_kp    else 0)
                    + footer_h + spacing.gap_before_footer
                    + spacing.gap_after_header)
        available_for_sections = max(
            MIN_SECTION_HEIGHT * len(sections),
            usable_h - fixed_h - spacing.gap_between_section * max(0, len(sections) - 1)
        )

        bal_report = generate_balance_report(sections, available_for_sections)
        self._log(f"  Balance: {len(sections)} sections, {bal_report['pages']} pages")
        self._log(f"  Fits single page: {bal_report['fits_single_page']}")

        # ── Split sections into pages ─────────────────────────────────
        page_groups = balance_sections_across_pages(
            sections,
            max_sections_page1=2,
            max_sections_other=3,
        )
        total_pages = len(page_groups)

        # ── Build each page ───────────────────────────────────────────
        plan = LayoutPlan(
            topic         = topic,
            title         = title,
            color_theme   = color_theme,
            content_type  = c_type,
            generated_at  = datetime.now().isoformat(),
            total_pages   = total_pages,
            balance_report= bal_report,
        )

        sec_offset = 0
        for page_idx, page_secs in enumerate(page_groups):
            is_first = (page_idx == 0)
            is_last  = (page_idx == total_pages - 1)

            page_plan = self._build_page(
                page_num    = page_idx + 1,
                sections    = page_secs,
                sec_offset  = sec_offset,
                statistics  = statistics  if is_last else [],
                key_points  = key_points  if is_last else [],
                cta         = cta         if is_last else "",
                hashtags    = hashtags    if is_last else [],
                title       = title       if is_first else f"(cont.) {title[:30]}",
                subtitle    = subtitle    if is_first else "",
                spacing     = spacing,
                show_header = True,
                show_footer = is_last,
                header_h    = header_h    if is_first else 100,
                stats_h     = stats_h,
                kp_h        = kp_h,
                footer_h    = footer_h,
                has_stats   = is_last and has_stats,
                has_kp      = is_last and has_kp,
            )
            plan.pages.append(page_plan)
            sec_offset += len(page_secs)

        self._log(f"  Layout complete: {total_pages} page(s)")
        return plan

    # ── Single page builder ────────────────────────────────────────────────
    def _build_page(self,
                    page_num:   int,
                    sections:   list,
                    sec_offset: int,
                    statistics: list,
                    key_points: list,
                    cta:        str,
                    hashtags:   list,
                    title:      str,
                    subtitle:   str,
                    spacing:    SpacingProfile,
                    show_header:bool,
                    show_footer:bool,
                    header_h:   int,
                    stats_h:    int,
                    kp_h:       int,
                    footer_h:   int,
                    has_stats:  bool,
                    has_kp:     bool) -> PagePlan:
        """Build all BlockPlans for a single page."""

        page  = PagePlan(page_number=page_num, spacing=spacing)
        cx    = CONTENT_X
        cw    = CONTENT_W
        cy    = MARGIN_V

        # ── Header ────────────────────────────────────────────────────
        if show_header:
            h_rect = full_width_rect(cy, header_h)
            page.add_block(BlockPlan(
                block_id   = "header",
                block_type = "header",
                rect       = h_rect,
                page       = page_num,
                metadata   = {"title": title, "subtitle": subtitle},
            ))
            cy += header_h + spacing.gap_after_header

        # ── Sections ──────────────────────────────────────────────────
        # Calculate available height for sections on this page
        fixed_below = (
            ((stats_h  + spacing.gap_before_stats)    if has_stats else 0)
            + ((kp_h   + spacing.gap_before_keypoint) if has_kp    else 0)
            + ((footer_h + spacing.gap_before_footer) if show_footer else 0)
        )
        available_for_secs = (
            self.canvas_h - MARGIN_V - cy - fixed_below
            - spacing.gap_between_section * max(0, len(sections) - 1)
        )
        available_for_secs = max(MIN_SECTION_HEIGHT * len(sections),
                                  available_for_secs)

        # Allocate heights
        sec_heights = allocate_heights_proportional(
            sections, available_for_secs,
            gap_size=spacing.gap_between_section
        )
        sec_heights = compress_heights_to_fit(
            sec_heights, available_for_secs,
            gap=spacing.gap_between_section
        )

        for i, (sec, sh) in enumerate(zip(sections, sec_heights)):
            abs_idx = sec_offset + i
            s_rect  = full_width_rect(cy, sh)
            page.add_block(BlockPlan(
                block_id   = f"section_{abs_idx}",
                block_type = "section",
                rect       = s_rect,
                page       = page_num,
                metadata   = {
                    "heading":         sec.get("heading", ""),
                    "icon_suggestion": sec.get("icon_suggestion", ""),
                    "bullet_count":    len(sec.get("content", [])),
                    "section_index":   abs_idx,
                },
            ))
            cy += sh
            if i < len(sections) - 1:
                cy += spacing.gap_between_section

        # ── Stats ─────────────────────────────────────────────────────
        if has_stats and stats_h > 0:
            cy += spacing.gap_before_stats
            st_rect = full_width_rect(cy, stats_h)
            page.add_block(BlockPlan(
                block_id   = "stats",
                block_type = "stats",
                rect       = st_rect,
                page       = page_num,
                metadata   = {"n_stats": len(statistics)},
            ))
            cy += stats_h

        # ── Key Points ────────────────────────────────────────────────
        if has_kp and kp_h > 0:
            cy += spacing.gap_before_keypoint
            kp_rect = full_width_rect(cy, kp_h)
            page.add_block(BlockPlan(
                block_id   = "key_points",
                block_type = "key_points",
                rect       = kp_rect,
                page       = page_num,
                metadata   = {"n_points": len(key_points)},
            ))
            cy += kp_h

        # ── Footer (pinned to bottom) ──────────────────────────────────
        if show_footer and footer_h > 0:
            foot_y  = anchor_footer_y(footer_h, self.canvas_h, MARGIN_V)
            ft_rect = full_width_rect(foot_y, footer_h)
            page.add_block(BlockPlan(
                block_id   = "footer",
                block_type = "footer",
                rect       = ft_rect,
                page       = page_num,
                metadata   = {"cta": cta, "n_hashtags": len(hashtags)},
            ))

        # ── Validation ────────────────────────────────────────────────
        rects      = [b.rect for b in page.blocks]
        validation = validate_layout(rects)
        page.overflow = not validation["valid"]

        return page


# ════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ════════════════════════════════════════════════════════════════════════════

def generate_layout_plan(content: dict,
                          verbose: bool = True) -> LayoutPlan:
    """
    One-liner: generate a complete LayoutPlan from Phase 1 content.

    Args:
        content : Phase 1 content dict
        verbose : print progress

    Returns:
        LayoutPlan

    Example:
        plan = generate_layout_plan(content_dict)
        print(plan.to_json())
    """
    engine = LayoutEngine(verbose=verbose)
    return engine.compute(content)


def layout_plan_from_file(json_path: str,
                           verbose: bool = True) -> LayoutPlan:
    """Load Phase 1 JSON file and compute layout plan."""
    import json as _json
    with open(json_path, "r", encoding="utf-8") as f:
        content = _json.load(f)
    return generate_layout_plan(content, verbose)
