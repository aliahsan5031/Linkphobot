"""
infographic_renderer.py
=======================
Linkphobot - Phase 3: Fixed Template Renderer
Main Orchestrator - render_infographic()

Pipeline:
  1. Accept content dict (Phase 1 output) or layout dict (Phase 2 output)
  2. Select template from color_theme or explicit name
  3. Load + warmup fonts
  4. Create 1080x1350 canvas
  5. Render background
  6. Stack all blocks top-to-bottom with overflow → carousel split
  7. Export PNG(s) to output directory

Public API:
  render_infographic(content, template_name, output_dir) -> list[str]
  render_from_file(json_path, template_name, output_dir)  -> list[str]
"""

import os
import sys
import json
import re
from datetime import datetime
from typing import Union, List, Optional

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from font_loader import get_font, warmup_fonts, measure_text
from templates import get_template, InfographicTemplate, hex_to_rgb
from renderer import draw_card, draw_gradient_rect, draw_rounded_rect
from card_renderer import (
    render_header_card,
    render_section_card,
    render_stats_card,
    render_keypoints_card,
    render_footer_card,
)
from icon_renderer import draw_brand_strip


# ════════════════════════════════════════════════════════════════════════════
# CANVAS CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

CANVAS_W  = 1080
CANVAS_H  = 1350
MARGIN    = 54


# ════════════════════════════════════════════════════════════════════════════
# BACKGROUND RENDERER
# ════════════════════════════════════════════════════════════════════════════

def _render_background(img: Image.Image, tmpl: InfographicTemplate) -> None:
    """Fill canvas with background color and optional subtle grid texture."""
    draw = ImageDraw.Draw(img)
    rgb  = hex_to_rgb(tmpl.bg_color)
    draw.rectangle([0, 0, CANVAS_W, CANVAS_H], fill=rgb)

    # Subtle decorative top-right corner accent blob (large circle)
    accent_r, accent_g, accent_b = hex_to_rgb(tmpl.primary)
    blob_color = (accent_r, accent_g, accent_b, 12)
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([CANVAS_W-300, -150, CANVAS_W+200, 350],
               fill=blob_color)
    od.ellipse([-200, CANVAS_H-200, 300, CANVAS_H+300],
               fill=blob_color)
    img.paste(overlay, (0,0), overlay)


# ════════════════════════════════════════════════════════════════════════════
# CONTENT EXTRACTOR  –  normalize Phase 1 or Phase 2 dict
# ════════════════════════════════════════════════════════════════════════════

def _extract_content(data: dict) -> dict:
    """
    Accept either Phase 1 content dict or Phase 2 layout dict.
    Returns a normalized content dict.
    """
    # Phase 2 layout wraps content inside layout metadata
    if "header_block" in data or "section_blocks" in data:
        # It's a Phase 2 layout – reconstruct content from layout
        sections = []
        for sb in data.get("section_blocks", []):
            sections.append({
                "heading":          sb.get("heading", ""),
                "icon_suggestion":  sb.get("icon_emoji", "📌"),
                "content": [bi.get("text","") for bi in sb.get("bullet_items",[])]
            })
        stats = []
        if data.get("stats_block"):
            for si in data["stats_block"].get("stat_items",[]):
                stats.append({
                    "value":   si.get("value",""),
                    "label":   si.get("label",""),
                    "context": si.get("context",""),
                })
        kps = []
        if data.get("key_points_block"):
            for pi in data["key_points_block"].get("point_items",[]):
                kps.append(pi.get("text",""))
        return {
            "title":          data.get("title",""),
            "subtitle":       "",
            "sections":       sections,
            "statistics":     stats,
            "key_points":     kps,
            "call_to_action": "",
            "hashtags":       [],
            "color_theme":    data.get("color_theme","professional"),
            "content_type":   data.get("content_type","educational"),
            "topic":          data.get("topic",""),
        }
    # Phase 1 content dict
    return data


# ════════════════════════════════════════════════════════════════════════════
# PAGE SPLITTER  –  split sections into carousel pages
# ════════════════════════════════════════════════════════════════════════════

def _split_into_pages(sections: list,
                      max_sections_per_page: int = 3) -> list:
    """
    Split a list of sections into pages for carousel output.
    First page: always 2 sections (header takes space).
    Subsequent pages: up to max_sections_per_page.
    """
    if not sections:
        return [[]]
    pages  = []
    # Page 1: header + 2 sections
    pages.append(sections[:2])
    rest = sections[2:]
    while rest:
        pages.append(rest[:max_sections_per_page])
        rest = rest[max_sections_per_page:]
    return pages


# ════════════════════════════════════════════════════════════════════════════
# SINGLE PAGE RENDERER
# ════════════════════════════════════════════════════════════════════════════

def _render_page(content: dict,
                 sections_for_page: list,
                 page_num: int,
                 total_pages: int,
                 tmpl: InfographicTemplate,
                 show_header: bool = True,
                 show_stats: bool = False,
                 show_keypoints: bool = False,
                 show_footer: bool = True,
                 section_index_offset: int = 0) -> Image.Image:
    """
    Render a single infographic page (1080x1350) and return a PIL Image.
    """
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (255,255,255,255))
    _render_background(img, tmpl)

    draw = ImageDraw.Draw(img)
    x    = MARGIN
    w    = CANVAS_W - MARGIN * 2
    cy   = MARGIN
    gap  = tmpl.block_gap

    # ── Header ────────────────────────────────────────────────────────
    if show_header:
        title    = content.get("title","")
        subtitle = content.get("subtitle","")
        ctype    = content.get("content_type","educational")
        h = render_header_card(img, x, cy, w, title, subtitle, ctype, tmpl)
        cy += h + gap

    # ── Page number indicator (if multi-page) ─────────────────────────
    if total_pages > 1:
        pg_font = get_font("semibold", 16)
        pg_txt  = f"{page_num} / {total_pages}"
        pw, ph  = measure_text(pg_txt, pg_font)
        draw.text((CANVAS_W - MARGIN - pw, MARGIN + 8), pg_txt,
                  font=pg_font, fill=hex_to_rgb(tmpl.text_muted))

    # ── Sections ──────────────────────────────────────────────────────
    for i, section in enumerate(sections_for_page):
        heading = section.get("heading","")
        emoji   = section.get("icon_suggestion","📌")
        bullets = section.get("content",[])
        abs_idx = section_index_offset + i
        h = render_section_card(img, x, cy, w, heading, emoji, bullets,
                                 abs_idx, tmpl)
        cy += h + gap

    # ── Stats ─────────────────────────────────────────────────────────
    if show_stats:
        stats = content.get("statistics",[])
        if stats:
            h = render_stats_card(img, x, cy, w, stats, tmpl)
            cy += h + gap

    # ── Key Points ────────────────────────────────────────────────────
    if show_keypoints:
        kps = content.get("key_points",[])
        if kps:
            h = render_keypoints_card(img, x, cy, w, kps, tmpl)
            cy += h + gap

    # ── Footer ────────────────────────────────────────────────────────
    if show_footer:
        cta      = content.get("call_to_action","Save this post and share it.")
        hashtags = content.get("hashtags",[])
        # Position footer at bottom of canvas
        footer_y = CANVAS_H - MARGIN - 120
        render_footer_card(img, x, footer_y, w, cta, hashtags, tmpl)

    # ── Brand strip ───────────────────────────────────────────────────
    draw_brand_strip(draw, x, CANVAS_H - 22, w, "Linkphobot", tmpl)

    return img.convert("RGB")


# ════════════════════════════════════════════════════════════════════════════
# MAIN PUBLIC FUNCTION
# ════════════════════════════════════════════════════════════════════════════

def render_infographic(content: Union[dict, str],
                       template_name: Optional[str] = None,
                       output_dir: str = "output",
                       filename_prefix: Optional[str] = None,
                       verbose: bool = True) -> List[str]:
    """
    Render a complete LinkedIn infographic from content data.

    Automatically splits into carousel pages if content overflows.

    Args:
        content       : Phase 1 content dict, JSON string, or .json filepath
        template_name : "business" | "educational" | "technical" | None (auto)
        output_dir    : directory to save PNG files
        filename_prefix: prefix for output filenames
        verbose       : print progress

    Returns:
        list of absolute file paths to generated PNG(s)

    Example:
        paths = render_infographic("content.json", "business")
        # -> ["output/ai_healthcare_p1.png", "output/ai_healthcare_p2.png"]
    """
    def log(msg):
        if verbose:
            print(msg)

    # ── Load content ──────────────────────────────────────────────────
    if isinstance(content, str):
        if os.path.isfile(content):
            with open(content, "r", encoding="utf-8") as f:
                content = json.load(f)
        else:
            content = json.loads(content)

    content = _extract_content(content)

    # ── Select template ───────────────────────────────────────────────
    if template_name:
        tmpl = get_template(template_name)
    else:
        color_theme = content.get("color_theme","professional")
        tmpl = get_template(color_theme)

    log(f"\n[Linkphobot Phase 3] Rendering infographic...")
    log(f"  Title:    {content.get('title','')[:60]}")
    log(f"  Template: {tmpl.name}")
    log(f"  Theme:    {content.get('color_theme','')}")

    # ── Warmup fonts ──────────────────────────────────────────────────
    log("  Loading fonts...")
    warmup_fonts()

    # ── Split sections into pages ─────────────────────────────────────
    sections    = content.get("sections",[])
    statistics  = content.get("statistics",[])
    key_points  = content.get("key_points",[])
    pages       = _split_into_pages(sections, max_sections_per_page=3)
    total_pages = len(pages)
    log(f"  Sections: {len(sections)} -> {total_pages} page(s)")

    # ── Setup output directory ────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)

    # ── Build filename prefix ─────────────────────────────────────────
    if not filename_prefix:
        raw = content.get("topic") or content.get("title","infographic")
        filename_prefix = re.sub(r"[^\w]","_",raw)[:36].strip("_").lower()

    # ── Render each page ──────────────────────────────────────────────
    output_paths = []
    sec_offset   = 0

    for page_idx, page_sections in enumerate(pages):
        is_first = (page_idx == 0)
        is_last  = (page_idx == total_pages - 1)

        log(f"  Rendering page {page_idx+1}/{total_pages} "
            f"({len(page_sections)} sections)...")

        img = _render_page(
            content             = content,
            sections_for_page   = page_sections,
            page_num            = page_idx + 1,
            total_pages         = total_pages,
            tmpl                = tmpl,
            show_header         = is_first,
            show_stats          = is_last and bool(statistics),
            show_keypoints      = is_last and bool(key_points),
            show_footer         = is_last,
            section_index_offset= sec_offset,
        )

        # Save
        if total_pages == 1:
            fname = f"{filename_prefix}.png"
        else:
            fname = f"{filename_prefix}_p{page_idx+1}.png"

        fpath = os.path.join(output_dir, fname)
        img.save(fpath, "PNG", optimize=True)
        output_paths.append(os.path.abspath(fpath))
        log(f"  Saved: {fpath}")

        sec_offset += len(page_sections)

    log(f"  Done! {len(output_paths)} PNG(s) exported.")
    return output_paths


# ════════════════════════════════════════════════════════════════════════════
# CONVENIENCE WRAPPERS
# ════════════════════════════════════════════════════════════════════════════

def render_from_file(json_path: str,
                     template_name: Optional[str] = None,
                     output_dir: str = "output",
                     verbose: bool = True) -> List[str]:
    """Render infographic directly from a JSON file path."""
    return render_infographic(json_path, template_name, output_dir,
                              verbose=verbose)


def render_all_templates(content: Union[dict, str],
                          output_dir: str = "output",
                          verbose: bool = True) -> dict:
    """
    Render the same content with all 3 templates.
    Useful for A/B comparison.

    Returns:
        dict mapping template_name -> list of PNG paths
    """
    results = {}
    for t_name in ["business","educational","technical"]:
        paths = render_infographic(content, t_name, output_dir, verbose=verbose)
        results[t_name] = paths
    return results


# ════════════════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    input_path    = sys.argv[1] if len(sys.argv) > 1 else "example_output.json"
    template_name = sys.argv[2] if len(sys.argv) > 2 else None
    output_dir    = sys.argv[3] if len(sys.argv) > 3 else "output"
    paths = render_from_file(input_path, template_name, output_dir)
    print("Generated:", paths)
