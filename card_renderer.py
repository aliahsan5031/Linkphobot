"""
card_renderer.py
================
Linkphobot - Phase 3: Fixed Template Renderer
Card-Level Rendering System

Renders complete content cards:
  - render_header_card()      : title + subtitle dark card
  - render_section_card()     : content section with icon + bullets
  - render_stats_card()       : horizontal stat row
  - render_keypoints_card()   : key takeaways card
  - render_footer_card()      : CTA + hashtags card
  - render_divider_block()    : spacing divider

Each function takes (img, x, y, w, content_data, template)
and returns the height consumed.
"""

from PIL import Image, ImageDraw
from font_loader import get_font, wrap_text, measure_text, text_block_height
from templates import InfographicTemplate, hex_to_rgb
from renderer import (
    draw_card, draw_gradient_rect, draw_title, draw_text_block,
    draw_icon, draw_bullet_dot, draw_accent_bar, draw_divider,
    draw_stat_card, draw_badge, draw_rounded_rect,
)


# ════════════════════════════════════════════════════════════════════════════
# HEADER CARD
# ════════════════════════════════════════════════════════════════════════════

def render_header_card(img: Image.Image,
                       x: int, y: int, w: int,
                       title: str, subtitle: str,
                       content_type: str,
                       tmpl: InfographicTemplate) -> int:
    """
    Render the header card with title, subtitle, content-type badge.

    Returns:
        height used in pixels
    """
    draw     = ImageDraw.Draw(img)
    pad_h    = tmpl.header_pad_h
    pad_v    = tmpl.header_pad_v
    inner_w  = w - pad_h * 2

    # ── Pre-measure content to compute card height ────────────────────
    title_font = get_font(tmpl.weight_title, tmpl.font_title)
    sub_font   = get_font(tmpl.weight_subtitle, tmpl.font_subtitle)

    title_lines = wrap_text(title, title_font, inner_w)
    sub_lines   = wrap_text(subtitle, sub_font, inner_w)

    _, tlh = measure_text("Ag", title_font)
    _, slh = measure_text("Ag", sub_font)

    title_h = len(title_lines) * (tlh + 8)
    sub_h   = len(sub_lines)   * (slh + 6)
    badge_h = 36

    card_h = (pad_v
              + badge_h + 14
              + title_h + 16
              + sub_h
              + pad_v)

    # ── Draw card ─────────────────────────────────────────────────────
    if tmpl.header_gradient:
        draw_card(img, x, y, w, card_h,
                  fill_color=tmpl.header_gradient_start,
                  radius=tmpl.header_radius,
                  gradient=True,
                  gradient_end=tmpl.header_gradient_end,
                  gradient_dir="diagonal",
                  shadow=True)
    else:
        draw_card(img, x, y, w, card_h,
                  fill_color=tmpl.primary,
                  radius=tmpl.header_radius,
                  shadow=True)

    # Top accent bar
    if tmpl.header_bar_h > 0:
        draw_accent_bar(draw, x, y, w, tmpl.header_bar_h, tmpl.accent, radius=3)

    cy = y + pad_v

    # ── Content-type badge ────────────────────────────────────────────
    badge_text = content_type.upper()
    b_font     = get_font("semibold", tmpl.font_label)
    bw, bh     = measure_text(badge_text, b_font)
    badge_x    = x + (w - bw - 24) // 2
    draw_rounded_rect(draw, badge_x, cy, bw+24, bh+10, 20,
                      fill=hex_to_rgb(tmpl.accent))
    draw.text((badge_x+12, cy+5), badge_text, font=b_font,
              fill=hex_to_rgb(tmpl.text_on_dark))
    cy += bh + 10 + 14

    # ── Title ─────────────────────────────────────────────────────────
    title_col = tmpl.text_on_dark
    cy += draw_title(draw, title, x+pad_h, cy, inner_w,
                     tmpl.font_title, title_col,
                     weight=tmpl.weight_title,
                     align="center", line_spacing=8)
    cy += 16

    # ── Subtitle ──────────────────────────────────────────────────────
    sub_col = tmpl.text_on_dark_sub
    cy += draw_text_block(draw, subtitle, x+pad_h, cy, inner_w,
                          tmpl.font_subtitle, sub_col,
                          weight=tmpl.weight_subtitle,
                          align="center", line_spacing=6)
    cy += pad_v

    return card_h


# ════════════════════════════════════════════════════════════════════════════
# SECTION CARD
# ════════════════════════════════════════════════════════════════════════════

def render_section_card(img: Image.Image,
                        x: int, y: int, w: int,
                        heading: str,
                        icon_emoji: str,
                        bullets: list,
                        section_index: int,
                        tmpl: InfographicTemplate) -> int:
    """
    Render a content section card with heading, icon, and bullet points.

    Returns:
        height used in pixels
    """
    draw    = ImageDraw.Draw(img)
    pad_h   = tmpl.section_pad_h
    pad_v   = tmpl.section_pad_v
    acc_w   = tmpl.accent_bar_w
    icon_sz = 32

    # ── Pre-measure to compute height ─────────────────────────────────
    head_font = get_font(tmpl.weight_section, tmpl.font_section_head)
    bull_font = get_font(tmpl.weight_bullet,  tmpl.font_bullet)

    _, hlh = measure_text("Ag", head_font)
    _, blh = measure_text("Ag", bull_font)

    inner_w = w - pad_h*2 - acc_w - 8
    bull_x  = pad_h + acc_w + 8 + 14 + 8   # after acc_bar + dot + gap

    total_bull_h = 0
    for b in bullets:
        blines = wrap_text(b, bull_font, inner_w - 14 - 8)
        total_bull_h += len(blines) * (blh + 6) + tmpl.bullet_gap
    if bullets:
        total_bull_h -= tmpl.bullet_gap

    card_h = (pad_v
              + max(hlh, icon_sz) + 12
              + total_bull_h
              + pad_v)

    # ── Card background ───────────────────────────────────────────────
    bg_col = tmpl.card_bg_alt if (section_index % 2 == 1) else tmpl.card_bg
    draw_card(img, x, y, w, card_h,
              fill_color=bg_col,
              radius=tmpl.card_radius,
              border_color=tmpl.border_color,
              border_width=1,
              shadow=tmpl.card_shadow)

    # Left accent bar
    draw_accent_bar(draw,
                    x, y+10, acc_w, card_h-20,
                    tmpl.accent, radius=3)

    cy      = y + pad_v
    text_x  = x + pad_h + acc_w + 8

    # ── Icon + Heading row ────────────────────────────────────────────
    if tmpl.show_icons and icon_emoji:
        draw_icon(draw, icon_emoji, text_x, cy, size=icon_sz-2)
        head_x = text_x + icon_sz + 10
        head_w = w - head_x + x - pad_h
    else:
        head_x = text_x
        head_w = inner_w

    head_col = tmpl.text_primary
    draw.text((head_x, cy), heading,
              font=head_font, fill=hex_to_rgb(head_col))
    cy += max(hlh, icon_sz) + 12

    # ── Bullet points ─────────────────────────────────────────────────
    bull_w = inner_w - 14 - 8
    for bullet in bullets:
        blines = wrap_text(bullet, bull_font, bull_w)
        _, blh2 = measure_text("Ag", bull_font)

        # Dot
        if tmpl.show_dots:
            dot_cx = text_x + 4
            dot_cy = cy + blh2 // 2 + 2
            draw_bullet_dot(draw, dot_cx, dot_cy, radius=4, color=tmpl.dot_color)

        bx = text_x + 14 + 4
        for bi, bline in enumerate(blines):
            draw.text((bx, cy), bline, font=bull_font,
                      fill=hex_to_rgb(tmpl.text_secondary))
            cy += blh2 + 6
        cy += tmpl.bullet_gap

    return card_h


# ════════════════════════════════════════════════════════════════════════════
# STATS CARD
# ════════════════════════════════════════════════════════════════════════════

def render_stats_card(img: Image.Image,
                      x: int, y: int, w: int,
                      statistics: list,
                      tmpl: InfographicTemplate) -> int:
    """
    Render a horizontal row of stat cards.

    Returns:
        height used in pixels
    """
    if not statistics:
        return 0

    draw      = ImageDraw.Draw(img)
    pad_h     = tmpl.stats_pad_h
    pad_v     = tmpl.stats_pad_v
    item_gap  = 12
    head_h    = tmpl.font_section_head + 16

    n         = min(len(statistics), 3)
    inner_w   = w - pad_h*2
    item_w    = (inner_w - item_gap*(n-1)) // n
    item_h    = 110
    card_h    = pad_v + head_h + item_h + pad_v

    # ── Outer card ────────────────────────────────────────────────────
    draw_card(img, x, y, w, card_h,
              fill_color=tmpl.card_bg,
              radius=tmpl.card_radius,
              border_color=tmpl.border_color,
              border_width=1,
              shadow=tmpl.card_shadow)

    cy = y + pad_v

    # ── Section heading ───────────────────────────────────────────────
    hfont = get_font(tmpl.weight_section, tmpl.font_section_head)
    lbl   = "Key Statistics"
    lw, _ = measure_text(lbl, hfont)
    draw.text((x + (w-lw)//2, cy), lbl, font=hfont,
              fill=hex_to_rgb(tmpl.text_primary))
    cy += tmpl.font_section_head + 16

    # ── Stat items ────────────────────────────────────────────────────
    ix = x + pad_h
    for i, stat in enumerate(statistics[:n]):
        draw_stat_card(img, ix, cy, item_w, item_h,
                       stat.get("value",""), stat.get("label",""), tmpl)
        ix += item_w + item_gap

    return card_h


# ════════════════════════════════════════════════════════════════════════════
# KEY POINTS CARD
# ════════════════════════════════════════════════════════════════════════════

def render_keypoints_card(img: Image.Image,
                          x: int, y: int, w: int,
                          key_points: list,
                          tmpl: InfographicTemplate) -> int:
    """
    Render a key takeaways card with gradient background.

    Returns:
        height used in pixels
    """
    if not key_points:
        return 0

    draw     = ImageDraw.Draw(img)
    pad_h    = tmpl.section_pad_h
    pad_v    = tmpl.section_pad_v
    inner_w  = w - pad_h*2

    kp_font  = get_font(tmpl.weight_kp, tmpl.font_kp_item)
    hd_font  = get_font(tmpl.weight_section, tmpl.font_section_head)
    _, kph   = measure_text("Ag", kp_font)
    _, hdh   = measure_text("Ag", hd_font)

    total_kp_h = 0
    for kp in key_points:
        klines = wrap_text(kp, kp_font, inner_w - 20)
        total_kp_h += len(klines) * (kph + 6) + tmpl.bullet_gap
    if key_points:
        total_kp_h -= tmpl.bullet_gap

    card_h = pad_v + hdh + 16 + total_kp_h + pad_v

    # ── Gradient card ─────────────────────────────────────────────────
    draw_card(img, x, y, w, card_h,
              fill_color=tmpl.header_gradient_start,
              radius=tmpl.card_radius,
              gradient=True,
              gradient_end=tmpl.header_gradient_end,
              gradient_dir="horizontal",
              shadow=True)

    cy = y + pad_v

    # ── Heading ───────────────────────────────────────────────────────
    head_txt = "Key Takeaways"
    draw.text((x + pad_h, cy), head_txt, font=hd_font,
              fill=hex_to_rgb(tmpl.text_on_dark))
    cy += hdh + 16

    # ── Points ────────────────────────────────────────────────────────
    for kp in key_points:
        klines = wrap_text(kp, kp_font, inner_w - 20)
        _, kph2 = measure_text("Ag", kp_font)

        # Dot
        draw_bullet_dot(draw, x+pad_h+4, cy+kph2//2+2,
                        radius=4, color=tmpl.accent)

        kp_x = x + pad_h + 14 + 4
        for kline in klines:
            draw.text((kp_x, cy), kline, font=kp_font,
                      fill=hex_to_rgb(tmpl.text_on_dark))
            cy += kph2 + 6
        cy += tmpl.bullet_gap

    return card_h


# ════════════════════════════════════════════════════════════════════════════
# FOOTER CARD
# ════════════════════════════════════════════════════════════════════════════

def render_footer_card(img: Image.Image,
                       x: int, y: int, w: int,
                       cta: str,
                       hashtags: list,
                       tmpl: InfographicTemplate) -> int:
    """
    Render the footer card with CTA text, divider, and hashtags.

    Returns:
        height used in pixels
    """
    draw    = ImageDraw.Draw(img)
    pad_h   = tmpl.footer_pad_h
    pad_v   = tmpl.footer_pad_v
    inner_w = w - pad_h*2

    cta_font  = get_font(tmpl.weight_cta, tmpl.font_cta)
    hash_font = get_font(tmpl.weight_hashtag, tmpl.font_hashtag)

    cta_lines  = wrap_text(cta, cta_font, inner_w)
    hash_str   = "  ".join(hashtags[:6])
    hash_lines = wrap_text(hash_str, hash_font, inner_w)

    _, clh = measure_text("Ag", cta_font)
    _, hlh = measure_text("Ag", hash_font)

    cta_h  = len(cta_lines)  * (clh + 6)
    hash_h = len(hash_lines) * (hlh + 6)

    card_h = pad_v + cta_h + 20 + 2 + 20 + hash_h + pad_v

    # ── Card ──────────────────────────────────────────────────────────
    draw_card(img, x, y, w, card_h,
              fill_color=tmpl.card_bg,
              radius=tmpl.card_radius,
              border_color=tmpl.border_color,
              border_width=1,
              shadow=tmpl.card_shadow)

    cy = y + pad_v

    # ── CTA ───────────────────────────────────────────────────────────
    for cline in cta_lines:
        cw2, _ = measure_text(cline, cta_font)
        draw.text((x + (w-cw2)//2, cy), cline, font=cta_font,
                  fill=hex_to_rgb(tmpl.text_primary))
        cy += clh + 6
    cy += 14

    # ── Divider ───────────────────────────────────────────────────────
    draw_divider(draw, x+pad_h*2, cy, w-pad_h*4, tmpl.border_color)
    cy += 2 + 14

    # ── Hashtags ──────────────────────────────────────────────────────
    for hline in hash_lines:
        hw2, _ = measure_text(hline, hash_font)
        draw.text((x + (w-hw2)//2, cy), hline, font=hash_font,
                  fill=hex_to_rgb(tmpl.secondary))
        cy += hlh + 6

    return card_h
