"""
infographic_structure_generator.py
====================================
Linkphobot - Phase 2: JSON Structure Generator
Main Orchestration Module

Converts InfographicContent JSON (Phase 1 output) into
a complete InfographicLayout JSON (Phase 2 output).

Pipeline:
  1. Load content JSON
  2. Resolve color theme
  3. Estimate all block heights
  4. Run vertical flow engine
  5. Build every block with full element coordinates
  6. Return / save InfographicLayout JSON
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Optional, Union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from layout_schema import (
    CANVAS_WIDTH, CANVAS_HEIGHT, MARGIN_LEFT, MARGIN_RIGHT,
    MARGIN_TOP, MARGIN_BOTTOM, CONTENT_WIDTH,
    Rect, Padding,
    TextElement, ShapeElement, IconElement,
    HeaderBlock, SectionBlock, BulletItem,
    StatsBlock, StatItem, KeyPointsBlock,
    FooterBlock, InfographicLayout,
    COLOR_THEMES,
)
from spacing_rules import (
    HEADER_PADDING_TOP, HEADER_PADDING_BOTTOM, HEADER_PADDING_H,
    HEADER_ACCENT_BAR_H, HEADER_TITLE_FONT, HEADER_SUBTITLE_FONT,
    HEADER_TITLE_LINE_H, HEADER_GAP_TITLE_SUB,
    SECTION_PADDING_TOP, SECTION_PADDING_BOTTOM, SECTION_PADDING_H,
    SECTION_CORNER_RADIUS, SECTION_ACCENT_BAR_W,
    SECTION_HEADING_FONT, SECTION_GAP_HEAD_BULL,
    SECTION_BULLET_FONT, SECTION_BULLET_LINE_H, SECTION_BULLET_GAP,
    SECTION_DOT_SIZE, SECTION_ICON_SIZE, SECTION_ICON_GAP,
    STATS_PADDING_TOP, STATS_PADDING_BOTTOM, STATS_PADDING_H,
    STATS_CORNER_RADIUS, STATS_HEADING_FONT, STATS_HEADING_GAP,
    STATS_ITEM_CORNER, STATS_ITEM_PADDING_V, STATS_ITEM_PADDING_H,
    STATS_VALUE_FONT, STATS_LABEL_FONT, STATS_ITEM_GAP,
    STATS_MIN_ITEM_HEIGHT,
    KP_PADDING_TOP, KP_PADDING_BOTTOM, KP_PADDING_H,
    KP_CORNER_RADIUS, KP_HEADING_FONT, KP_HEADING_GAP,
    KP_ITEM_FONT, KP_ITEM_LINE_H, KP_ITEM_GAP,
    KP_BULLET_SIZE, KP_BULLET_GAP,
    FOOTER_PADDING_TOP, FOOTER_PADDING_BOTTOM, FOOTER_PADDING_H,
    FOOTER_CORNER_RADIUS, FOOTER_CTA_FONT, FOOTER_HASHTAG_FONT,
    FOOTER_DIVIDER_H, FOOTER_DIVIDER_GAP,
    GAP_AFTER_HEADER, GAP_BETWEEN_SECTIONS,
    GAP_BEFORE_STATS, GAP_BEFORE_KEYPOINTS, GAP_BEFORE_FOOTER,
    estimate_header_height, estimate_section_height,
    estimate_stats_height, estimate_keypoints_height,
    estimate_footer_height,
    BlockHeights, compute_vertical_flow, compress_sections_to_fit,
    compute_stat_card_rects,
)
from hierarchy_engine import (
    ZIndex, get_typography, get_alignment,
    get_color, get_theme_colors,
    should_include_stats, should_include_keypoints,
    get_section_card_style,
    scale_title_font, scale_section_heading_font,
)


# ════════════════════════════════════════════════════════════════════════════
# BLOCK BUILDERS
# ════════════════════════════════════════════════════════════════════════════

class LayoutBlockBuilder:
    """
    Builds individual layout blocks given content data and position info.
    All methods return fully populated block objects with pixel coordinates.
    """

    def __init__(self, theme: str, section_count: int = 4, bullet_count: int = 4):
        self.theme         = theme
        self.colors        = get_theme_colors(theme)
        self.section_count = section_count
        self.bullet_count  = bullet_count

    def _typo(self, element_type: str) -> object:
        return get_typography(element_type, self.theme,
                              self.section_count, self.bullet_count)

    def _color(self, key: str) -> str:
        return self.colors.get(key, "#333333")

    # ── Canvas Background ─────────────────────────────────────────────────

    def build_canvas_bg(self) -> ShapeElement:
        return ShapeElement(
            element_id="canvas_bg",
            element_type="rect",
            rect=Rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT),
            color_key="background",
            color_override=self._color("background"),
            z_index=ZIndex.CANVAS_BG,
        )

    # ── Header Block ──────────────────────────────────────────────────────

    def build_header(self, title: str, subtitle: str,
                     y: int, height: int) -> HeaderBlock:
        x = MARGIN_LEFT
        w = CONTENT_WIDTH

        # Background card
        bg = ShapeElement(
            element_id="header_bg",
            element_type="rect",
            rect=Rect(x, y, w, height),
            color_key="primary",
            color_override=self._color("primary"),
            corner_radius=20,
            gradient=True,
            gradient_direction="diagonal",
            z_index=ZIndex.BLOCK_BG,
        )

        # Top accent bar
        accent = ShapeElement(
            element_id="header_accent",
            element_type="accent_bar",
            rect=Rect(x, y, w, HEADER_ACCENT_BAR_H),
            color_key="accent",
            color_override=self._color("accent"),
            corner_radius=3,
            z_index=ZIndex.ACCENT_BAR,
        )

        # Title
        title_font = scale_title_font(title, HEADER_TITLE_FONT)
        title_typo = self._typo("title")
        title_typo.font_size = title_font

        title_y = y + HEADER_ACCENT_BAR_H + HEADER_PADDING_TOP
        title_el = TextElement(
            element_id="header_title",
            element_type="title",
            text=title,
            rect=Rect(x + HEADER_PADDING_H, title_y,
                      w - HEADER_PADDING_H * 2,
                      int(title_font * HEADER_TITLE_LINE_H * 3)),
            typography=title_typo,
            align="center",
            z_index=ZIndex.TEXT,
            color_override=self._color("text_primary"),
        )

        # Subtitle
        sub_typo = self._typo("subtitle")
        subtitle_y = title_y + int(title_font * HEADER_TITLE_LINE_H * 2) + HEADER_GAP_TITLE_SUB
        sub_el = TextElement(
            element_id="header_subtitle",
            element_type="subtitle",
            text=subtitle,
            rect=Rect(x + HEADER_PADDING_H, subtitle_y,
                      w - HEADER_PADDING_H * 2,
                      int(HEADER_SUBTITLE_FONT * 1.35 * 3)),
            typography=sub_typo,
            align="center",
            z_index=ZIndex.TEXT,
            color_override=self._color("text_secondary"),
        )

        return HeaderBlock(
            rect=Rect(x, y, w, height),
            background=bg,
            accent_bar=accent,
            title_element=title_el,
            subtitle_element=sub_el,
        )

    # ── Section Block ─────────────────────────────────────────────────────

    def build_section(self, section_data: dict, section_index: int,
                      y: int, height: int) -> SectionBlock:
        heading  = section_data.get("heading", "")
        emoji    = section_data.get("icon_suggestion", "📌")
        bullets  = section_data.get("content", [])

        x = MARGIN_LEFT
        w = CONTENT_WIDTH
        card_style = get_section_card_style(section_index, self.theme)

        # Card background
        bg = ShapeElement(
            element_id=f"section_{section_index}_bg",
            element_type="rect",
            rect=Rect(x, y, w, height),
            color_key=card_style["bg_color_key"],
            color_override=self._color(card_style["bg_color_key"]),
            corner_radius=SECTION_CORNER_RADIUS,
            border_width=card_style["border_width"],
            border_color_key="border",
            border_color_override=self._color("border"),
            z_index=ZIndex.BLOCK_BG,
        )

        # Left accent bar
        accent = ShapeElement(
            element_id=f"section_{section_index}_accent",
            element_type="accent_bar",
            rect=Rect(x, y + 12, SECTION_ACCENT_BAR_W, height - 24),
            color_key="accent",
            color_override=self._color("accent"),
            corner_radius=3,
            z_index=ZIndex.ACCENT_BAR,
        )

        inner_x = x + SECTION_PADDING_H + SECTION_ACCENT_BAR_W + 8
        inner_w = w - SECTION_PADDING_H * 2 - SECTION_ACCENT_BAR_W - 8
        cursor_y = y + SECTION_PADDING_TOP

        # Icon
        icon_el = IconElement(
            element_id=f"section_{section_index}_icon",
            emoji=emoji,
            rect=Rect(inner_x, cursor_y, SECTION_ICON_SIZE, SECTION_ICON_SIZE),
            font_size=SECTION_ICON_SIZE - 4,
            z_index=ZIndex.ICON,
            color_key="accent",
        )

        # Heading
        head_font = scale_section_heading_font(heading, SECTION_HEADING_FONT)
        head_typo = self._typo("section_heading")
        head_typo.font_size = head_font

        heading_x = inner_x + SECTION_ICON_SIZE + SECTION_ICON_GAP
        heading_w = inner_w - SECTION_ICON_SIZE - SECTION_ICON_GAP
        head_el = TextElement(
            element_id=f"section_{section_index}_heading",
            element_type="section_heading",
            text=heading,
            rect=Rect(heading_x, cursor_y,
                      heading_w,
                      int(head_font * 1.2 * 2)),
            typography=head_typo,
            align="left",
            z_index=ZIndex.TEXT,
            color_override=self._color("text_primary"),
        )

        cursor_y += max(SECTION_ICON_SIZE, int(head_font * 1.2)) + SECTION_GAP_HEAD_BULL

        # Bullet items
        bullet_items = []
        for bi, bullet_text in enumerate(bullets):
            bh = int(SECTION_BULLET_FONT * SECTION_BULLET_LINE_H * 2)

            # Dot
            dot = ShapeElement(
                element_id=f"s{section_index}_b{bi}_dot",
                element_type="circle",
                rect=Rect(inner_x + 2,
                          cursor_y + int(SECTION_BULLET_FONT * SECTION_BULLET_LINE_H / 2) - SECTION_DOT_SIZE // 2,
                          SECTION_DOT_SIZE, SECTION_DOT_SIZE),
                color_key="accent",
                color_override=self._color("accent"),
                corner_radius=SECTION_DOT_SIZE // 2,
                z_index=ZIndex.ACCENT_BAR,
            )

            # Bullet text
            bullet_x = inner_x + SECTION_DOT_SIZE + 14
            bullet_w = inner_w - SECTION_DOT_SIZE - 14
            b_typo   = self._typo("bullet")
            b_el = TextElement(
                element_id=f"s{section_index}_b{bi}_text",
                element_type="bullet",
                text=bullet_text,
                rect=Rect(bullet_x, cursor_y, bullet_w, bh),
                typography=b_typo,
                align="left",
                z_index=ZIndex.TEXT,
                color_override=self._color("text_secondary"),
            )

            item = BulletItem(
                item_id=f"s{section_index}_bullet_{bi}",
                text=bullet_text,
                rect=Rect(inner_x, cursor_y, inner_w, bh),
                text_element=b_el,
                dot_element=dot,
            )
            bullet_items.append(item)
            cursor_y += bh + SECTION_BULLET_GAP

        return SectionBlock(
            block_id=f"section_{section_index}",
            section_index=section_index,
            heading=heading,
            icon_emoji=emoji,
            rect=Rect(x, y, w, height),
            background=bg,
            accent_bar=accent,
            heading_element=head_el,
            icon_element=icon_el,
            bullet_items=bullet_items,
        )

    # ── Stats Block ───────────────────────────────────────────────────────

    def build_stats(self, statistics: list, y: int, height: int) -> StatsBlock:
        x = MARGIN_LEFT
        w = CONTENT_WIDTH

        bg = ShapeElement(
            element_id="stats_bg",
            element_type="rect",
            rect=Rect(x, y, w, height),
            color_key="surface",
            color_override=self._color("surface"),
            corner_radius=STATS_CORNER_RADIUS,
            border_width=1,
            border_color_key="border",
            border_color_override=self._color("border"),
            z_index=ZIndex.BLOCK_BG,
        )

        cursor_y = y + STATS_PADDING_TOP

        # Heading
        h_typo = self._typo("stat_heading")
        heading_el = TextElement(
            element_id="stats_heading",
            element_type="stat_heading",
            text="Key Statistics",
            rect=Rect(x + STATS_PADDING_H, cursor_y,
                      w - STATS_PADDING_H * 2, STATS_HEADING_FONT + 8),
            typography=h_typo,
            align="center",
            z_index=ZIndex.TEXT,
            color_override=self._color("text_primary"),
        )
        cursor_y += STATS_HEADING_FONT + STATS_HEADING_GAP

        # Stat card layout
        item_height = max(STATS_MIN_ITEM_HEIGHT,
                          height - STATS_PADDING_TOP - STATS_PADDING_BOTTOM
                          - STATS_HEADING_FONT - STATS_HEADING_GAP)
        card_rects  = compute_stat_card_rects(
            len(statistics), x, w, item_height,
            STATS_PADDING_H, STATS_ITEM_GAP
        )

        stat_items = []
        for si, stat in enumerate(statistics):
            if si >= len(card_rects):
                break
            cx, cw = card_rects[si]

            card_bg = ShapeElement(
                element_id=f"stat_{si}_bg",
                element_type="rect",
                rect=Rect(cx, cursor_y, cw, item_height),
                color_key="stat_bg",
                color_override=self._color("stat_bg"),
                corner_radius=STATS_ITEM_CORNER,
                z_index=ZIndex.BLOCK_BG + 1,
            )

            val_typo = self._typo("stat_value")
            val_el = TextElement(
                element_id=f"stat_{si}_value",
                element_type="stat_value",
                text=stat.get("value", ""),
                rect=Rect(cx + STATS_ITEM_PADDING_H,
                          cursor_y + STATS_ITEM_PADDING_V,
                          cw - STATS_ITEM_PADDING_H * 2,
                          int(STATS_VALUE_FONT * 1.1)),
                typography=val_typo,
                align="center",
                z_index=ZIndex.STAT_VALUE,
                color_override=self._color("accent"),
            )

            lbl_typo = self._typo("stat_label")
            lbl_el = TextElement(
                element_id=f"stat_{si}_label",
                element_type="stat_label",
                text=stat.get("label", ""),
                rect=Rect(cx + STATS_ITEM_PADDING_H,
                          cursor_y + STATS_ITEM_PADDING_V + int(STATS_VALUE_FONT * 1.1) + 8,
                          cw - STATS_ITEM_PADDING_H * 2,
                          int(STATS_LABEL_FONT * 1.3 * 3)),
                typography=lbl_typo,
                align="center",
                z_index=ZIndex.TEXT,
                color_override=self._color("text_secondary"),
            )

            stat_items.append(StatItem(
                item_id=f"stat_{si}",
                value=stat.get("value", ""),
                label=stat.get("label", ""),
                context=stat.get("context", ""),
                rect=Rect(cx, cursor_y, cw, item_height),
                background=card_bg,
                value_element=val_el,
                label_element=lbl_el,
            ))

        return StatsBlock(
            rect=Rect(x, y, w, height),
            background=bg,
            heading=heading_el,
            stat_items=stat_items,
        )

    # ── Key Points Block ──────────────────────────────────────────────────

    def build_key_points(self, key_points: list, y: int, height: int) -> KeyPointsBlock:
        x = MARGIN_LEFT
        w = CONTENT_WIDTH

        bg = ShapeElement(
            element_id="kp_bg",
            element_type="rect",
            rect=Rect(x, y, w, height),
            color_key="primary",
            color_override=self._color("primary"),
            corner_radius=KP_CORNER_RADIUS,
            gradient=True,
            gradient_direction="horizontal",
            z_index=ZIndex.BLOCK_BG,
        )

        cursor_y = y + KP_PADDING_TOP

        h_typo = self._typo("kp_heading")
        heading_el = TextElement(
            element_id="kp_heading",
            element_type="kp_heading",
            text="Key Takeaways",
            rect=Rect(x + KP_PADDING_H, cursor_y,
                      w - KP_PADDING_H * 2, KP_HEADING_FONT + 8),
            typography=h_typo,
            align="left",
            z_index=ZIndex.TEXT,
            color_override=self._color("text_primary"),
        )
        cursor_y += KP_HEADING_FONT + KP_HEADING_GAP

        point_items = []
        for pi, pt_text in enumerate(key_points):
            ph = int(KP_ITEM_FONT * KP_ITEM_LINE_H * 2)

            dot = ShapeElement(
                element_id=f"kp_{pi}_dot",
                element_type="circle",
                rect=Rect(x + KP_PADDING_H,
                          cursor_y + int(KP_ITEM_FONT * KP_ITEM_LINE_H / 2) - KP_BULLET_SIZE // 2,
                          KP_BULLET_SIZE, KP_BULLET_SIZE),
                color_key="accent",
                color_override=self._color("accent"),
                corner_radius=KP_BULLET_SIZE // 2,
                z_index=ZIndex.ACCENT_BAR,
            )

            pt_x = x + KP_PADDING_H + KP_BULLET_SIZE + KP_BULLET_GAP
            pt_w = w - KP_PADDING_H * 2 - KP_BULLET_SIZE - KP_BULLET_GAP
            pt_typo = self._typo("kp_item")
            pt_el = TextElement(
                element_id=f"kp_{pi}_text",
                element_type="kp_item",
                text=pt_text,
                rect=Rect(pt_x, cursor_y, pt_w, ph),
                typography=pt_typo,
                align="left",
                z_index=ZIndex.TEXT,
                color_override=self._color("text_primary"),
            )

            point_items.append(BulletItem(
                item_id=f"kp_{pi}",
                text=pt_text,
                rect=Rect(x + KP_PADDING_H, cursor_y,
                          w - KP_PADDING_H * 2, ph),
                text_element=pt_el,
                dot_element=dot,
            ))
            cursor_y += ph + KP_ITEM_GAP

        return KeyPointsBlock(
            rect=Rect(x, y, w, height),
            background=bg,
            heading=heading_el,
            point_items=point_items,
        )

    # ── Footer Block ──────────────────────────────────────────────────────

    def build_footer(self, cta: str, hashtags: list,
                     y: int, height: int) -> FooterBlock:
        x = MARGIN_LEFT
        w = CONTENT_WIDTH

        bg = ShapeElement(
            element_id="footer_bg",
            element_type="rect",
            rect=Rect(x, y, w, height),
            color_key="surface",
            color_override=self._color("surface"),
            corner_radius=FOOTER_CORNER_RADIUS,
            border_width=1,
            border_color_key="border",
            border_color_override=self._color("border"),
            z_index=ZIndex.BLOCK_BG,
        )

        cursor_y = y + FOOTER_PADDING_TOP

        cta_typo = self._typo("cta")
        cta_el = TextElement(
            element_id="footer_cta",
            element_type="cta",
            text=cta,
            rect=Rect(x + FOOTER_PADDING_H, cursor_y,
                      w - FOOTER_PADDING_H * 2,
                      int(FOOTER_CTA_FONT * 1.35 * 2)),
            typography=cta_typo,
            align="center",
            z_index=ZIndex.TEXT,
            color_override=self._color("text_primary"),
        )
        cursor_y += int(FOOTER_CTA_FONT * 1.35 * 2) + FOOTER_DIVIDER_GAP

        divider = ShapeElement(
            element_id="footer_divider",
            element_type="divider",
            rect=Rect(x + FOOTER_PADDING_H * 2, cursor_y,
                      w - FOOTER_PADDING_H * 4, FOOTER_DIVIDER_H),
            color_key="border",
            color_override=self._color("border"),
            z_index=ZIndex.ACCENT_BAR,
        )
        cursor_y += FOOTER_DIVIDER_H + FOOTER_DIVIDER_GAP

        tag_str  = "  ".join(hashtags[:6])
        tag_typo = self._typo("hashtag")
        tag_el = TextElement(
            element_id="footer_hashtags",
            element_type="hashtag",
            text=tag_str,
            rect=Rect(x + FOOTER_PADDING_H, cursor_y,
                      w - FOOTER_PADDING_H * 2,
                      int(FOOTER_HASHTAG_FONT * 1.4 * 2)),
            typography=tag_typo,
            align="center",
            z_index=ZIndex.TEXT,
            color_override=self._color("secondary"),
        )

        return FooterBlock(
            rect=Rect(x, y, w, height),
            background=bg,
            cta_element=cta_el,
            hashtag_element=tag_el,
            divider=divider,
        )


# ════════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR CLASS
# ════════════════════════════════════════════════════════════════════════════

class InfographicStructureGenerator:
    """
    Phase 2 main generator.

    Usage:
        gen    = InfographicStructureGenerator()
        layout = gen.generate(content_dict)
        gen.save(layout, "output_layout.json")
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def generate(self, content: Union[dict, str]) -> InfographicLayout:
        """
        Generate layout JSON from Phase 1 content.

        Args:
            content: dict (Phase 1 output) or JSON string or file path

        Returns:
            InfographicLayout with full pixel coordinates
        """
        # ── Load content ──────────────────────────────────────────────
        if isinstance(content, str):
            if os.path.isfile(content):
                with open(content, "r", encoding="utf-8") as f:
                    content = json.load(f)
            else:
                content = json.loads(content)

        self._log("\nLinkphobot Phase 2 - Generating layout structure...")
        self._log("  Topic: " + content.get("title", "Unknown"))

        # ── Extract content fields ────────────────────────────────────
        title        = content.get("title", "")
        subtitle     = content.get("subtitle", "")
        sections     = content.get("sections", [])
        statistics   = content.get("statistics", [])
        key_points   = content.get("key_points", [])
        cta          = content.get("call_to_action", "Save and share this post.")
        hashtags     = content.get("hashtags", [])
        color_theme  = content.get("color_theme", "professional")
        content_type = content.get("content_type", "educational")
        topic        = content.get("topic", title)

        # Validate theme
        if color_theme not in COLOR_THEMES:
            color_theme = "professional"

        # ── Flags ─────────────────────────────────────────────────────
        inc_stats = should_include_stats(statistics)
        inc_kp    = should_include_keypoints(key_points)

        # ── Estimate heights ──────────────────────────────────────────
        self._log("  Estimating block heights...")
        header_h  = estimate_header_height(title, subtitle)
        section_hs = [estimate_section_height(s.get("heading",""), s.get("content",[]))
                      for s in sections]
        stats_h   = estimate_stats_height(len(statistics)) if inc_stats else 0
        kp_h      = estimate_keypoints_height(key_points) if inc_kp else 0
        footer_h  = estimate_footer_height(cta, hashtags)

        # ── Available space for sections ──────────────────────────────
        used_by_others = (
            MARGIN_TOP + header_h + GAP_AFTER_HEADER
            + (GAP_BEFORE_STATS   + stats_h  if inc_stats else 0)
            + (GAP_BEFORE_KEYPOINTS + kp_h   if inc_kp    else 0)
            + GAP_BEFORE_FOOTER + footer_h + MARGIN_BOTTOM
            + GAP_BETWEEN_SECTIONS * max(0, len(sections) - 1)
        )
        available_for_sections = max(200, CANVAS_HEIGHT - used_by_others)
        section_hs = compress_sections_to_fit(section_hs, available_for_sections)

        # ── Vertical flow ─────────────────────────────────────────────
        heights = BlockHeights(
            header=header_h,
            sections=section_hs,
            stats=stats_h,
            key_points=kp_h,
            footer=footer_h,
        )
        flow = compute_vertical_flow(heights, inc_stats, inc_kp)
        self._log("  Overflow: " + str(flow["overflow"]))

        # ── Build layout ──────────────────────────────────────────────
        max_bullets   = max((len(s.get("content", [])) for s in sections), default=4)
        builder       = LayoutBlockBuilder(color_theme, len(sections), max_bullets)
        colors        = get_theme_colors(color_theme)

        canvas_bg     = builder.build_canvas_bg()
        header_block  = builder.build_header(title, subtitle,
                                              flow["header_y"], header_h)

        section_blocks = []
        for i, (sec, sh, sy) in enumerate(zip(sections, section_hs, flow["section_y"])):
            section_blocks.append(builder.build_section(sec, i, sy, sh))

        stats_block = None
        if inc_stats and flow["stats_y"] is not None:
            stats_block = builder.build_stats(statistics, flow["stats_y"], stats_h)

        kp_block = None
        if inc_kp and flow["key_points_y"] is not None:
            kp_block = builder.build_key_points(key_points,
                                                 flow["key_points_y"], kp_h)

        footer_block = builder.build_footer(cta, hashtags,
                                             flow["footer_y"], footer_h)

        # ── Count elements ────────────────────────────────────────────
        total_blocks   = 1 + len(section_blocks)
        total_elements = 3  # canvas bg + header title + header subtitle
        for sb in section_blocks:
            total_elements += 2 + len(sb.bullet_items) * 2
        if stats_block:
            total_blocks   += 1
            total_elements += 1 + len(stats_block.stat_items) * 2
        if kp_block:
            total_blocks   += 1
            total_elements += 1 + len(kp_block.point_items) * 2
        total_blocks   += 1  # footer
        total_elements += 3  # footer cta + hashtags + divider

        # ── Assemble ──────────────────────────────────────────────────
        layout_id = re.sub(r"[^\w]", "_", topic)[:32] + "_" + datetime.now().strftime("%H%M%S")

        layout = InfographicLayout(
            layout_id=layout_id,
            canvas_width=CANVAS_WIDTH,
            canvas_height=CANVAS_HEIGHT,
            color_theme=color_theme,
            colors=colors,
            topic=topic,
            title=title,
            content_type=content_type,
            generated_at=datetime.now().isoformat(),
            canvas_background=canvas_bg,
            header_block=header_block,
            section_blocks=section_blocks,
            stats_block=stats_block,
            key_points_block=kp_block,
            footer_block=footer_block,
            total_blocks=total_blocks,
            total_elements=total_elements,
            layout_height_used=flow["total_height"],
            overflow=flow["overflow"],
        )

        self._log("  Blocks built: " + str(total_blocks))
        self._log("  Elements:     " + str(total_elements))
        self._log("  Height used:  " + str(flow["total_height"]) + "px / " + str(CANVAS_HEIGHT) + "px")
        self._log("  Done!")
        return layout

    def save(self, layout: InfographicLayout,
             filepath: Optional[str] = None,
             output_dir: str = "outputs") -> str:
        if filepath is None:
            os.makedirs(output_dir, exist_ok=True)
            safe = re.sub(r"[^\w]", "_", layout.topic)[:36]
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(output_dir, safe + "_layout_" + ts + ".json")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(layout.to_json())
        self._log("Saved layout: " + filepath)
        return filepath


# ════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ════════════════════════════════════════════════════════════════════════════

def generate_layout(content: Union[dict, str],
                    save: bool = True,
                    output_dir: str = "outputs",
                    verbose: bool = True) -> InfographicLayout:
    """
    One-line layout generation from Phase 1 content.

    Args:
        content   : Phase 1 content dict, JSON string, or file path
        save      : save JSON to disk
        output_dir: directory to save in
        verbose   : print progress

    Returns:
        InfographicLayout object

    Example:
        layout = generate_layout("ai_healthcare_content.json")
    """
    gen    = InfographicStructureGenerator(verbose=verbose)
    layout = gen.generate(content)
    if save:
        gen.save(layout, output_dir=output_dir)
    return layout


# ════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    input_path = sys.argv[1] if len(sys.argv) > 1 else "example_output.json"
    layout     = generate_layout(input_path)
    print(layout.to_json()[:800] + "\n...(truncated)")
