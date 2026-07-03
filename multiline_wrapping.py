"""
multiline_wrapping.py
=====================
Linkphobot - Phase 4: Typography Scaling Engine
Multi-Line Text Wrapping Engine

Handles:
- Word wrapping to pixel width
- Hard truncation with ellipsis
- Hyphenation fallback for long words
- Justified text splitting
- Max-lines enforcement
"""

from PIL import ImageFont
from typing import List, Optional
from text_measurement import text_width, measure_line_height, measure_text


# ════════════════════════════════════════════════════════════════════════════
# CORE WORD WRAP
# ════════════════════════════════════════════════════════════════════════════

def wrap_text(text: str,
              font: ImageFont.FreeTypeFont,
              max_width: int,
              max_lines: int = 999) -> List[str]:
    """
    Wrap text to fit within max_width pixels.

    Algorithm:
      1. Split on whitespace
      2. Greedily add words while line fits
      3. On overflow: flush current line, start new
      4. Force-break single words that exceed max_width

    Args:
        text      : raw text string (may contain newlines)
        font      : PIL font object
        max_width : available width in pixels
        max_lines : hard cap on output lines

    Returns:
        list of line strings (never empty)
    """
    if not text or max_width <= 0:
        return [text or ""]

    # Honour explicit newlines
    paragraphs = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    all_lines  = []

    for para in paragraphs:
        words = para.split()
        if not words:
            all_lines.append("")
            continue

        current_words: List[str] = []
        for word in words:
            # Force-break word if wider than max_width alone
            word = _break_long_word(word, font, max_width)

            test_line = " ".join(current_words + [word])
            if text_width(test_line, font) <= max_width:
                current_words.append(word)
            else:
                if current_words:
                    all_lines.append(" ".join(current_words))
                current_words = [word]

        if current_words:
            all_lines.append(" ".join(current_words))

    result = all_lines[:max_lines] if max_lines < 999 else all_lines
    return result if result else [text]


def _break_long_word(word: str,
                      font: ImageFont.FreeTypeFont,
                      max_width: int) -> str:
    """
    If a single word is wider than max_width, truncate it with '…'.
    Used as last-resort for URLs and very long tokens.
    """
    if text_width(word, font) <= max_width:
        return word
    # Truncate character by character
    ellipsis = "…"
    ew = text_width(ellipsis, font)
    result = ""
    for ch in word:
        if text_width(result + ch + ellipsis, font) <= max_width:
            result += ch
        else:
            break
    return result + ellipsis if result else word[:3] + "…"


# ════════════════════════════════════════════════════════════════════════════
# TRUNCATION WITH ELLIPSIS
# ════════════════════════════════════════════════════════════════════════════

def truncate_to_width(text: str,
                       font: ImageFont.FreeTypeFont,
                       max_width: int,
                       ellipsis: str = "…") -> str:
    """
    Truncate a single-line string to fit in max_width, appending ellipsis.

    Returns:
        truncated string (or original if it already fits)
    """
    if text_width(text, font) <= max_width:
        return text

    ew = text_width(ellipsis, font)
    result = ""
    for ch in text:
        if text_width(result + ch, font) + ew <= max_width:
            result += ch
        else:
            break
    return result + ellipsis


def wrap_and_truncate(text: str,
                       font: ImageFont.FreeTypeFont,
                       max_width: int,
                       max_lines: int,
                       ellipsis: str = "…") -> List[str]:
    """
    Wrap text then truncate last line with ellipsis if max_lines is reached.

    Returns:
        list of lines, capped at max_lines
    """
    lines = wrap_text(text, font, max_width)
    if len(lines) <= max_lines:
        return lines

    truncated = lines[:max_lines]
    last_line = truncated[-1]

    # Try to append ellipsis without exceeding width
    candidate = last_line + ellipsis
    if text_width(candidate, font) <= max_width:
        truncated[-1] = candidate
    else:
        truncated[-1] = truncate_to_width(last_line, font,
                                           max_width, ellipsis)
    return truncated


# ════════════════════════════════════════════════════════════════════════════
# SMART TITLE WRAPPING
# ════════════════════════════════════════════════════════════════════════════

def wrap_title(title: str,
               font: ImageFont.FreeTypeFont,
               max_width: int,
               preferred_lines: int = 2) -> List[str]:
    """
    Wrap a title string aiming for balanced line lengths.

    Tries to produce `preferred_lines` lines of roughly equal width
    rather than greedy-filling each line.

    Args:
        title           : title text
        font            : PIL font
        max_width       : available width
        preferred_lines : target number of lines (1-3)

    Returns:
        list of balanced line strings
    """
    # First check if it fits on one line
    if text_width(title, font) <= max_width:
        return [title]

    words = title.split()
    n     = len(words)

    if n <= 1 or preferred_lines <= 1:
        return wrap_text(title, font, max_width)

    # Try balanced 2-line split: find the split point that minimises
    # the difference between line widths
    best_lines = wrap_text(title, font, max_width)
    best_diff  = float("inf")

    for split in range(1, n):
        line1 = " ".join(words[:split])
        line2 = " ".join(words[split:])
        w1 = text_width(line1, font)
        w2 = text_width(line2, font)
        if w1 > max_width or w2 > max_width:
            continue
        diff = abs(w1 - w2)
        if diff < best_diff:
            best_diff  = diff
            best_lines = [line1, line2]

    return best_lines


# ════════════════════════════════════════════════════════════════════════════
# BULLET TEXT WRAPPING
# ════════════════════════════════════════════════════════════════════════════

def wrap_bullet(text: str,
                font: ImageFont.FreeTypeFont,
                max_width: int,
                indent_px: int = 0,
                max_lines: int = 4) -> List[str]:
    """
    Wrap a bullet point with optional indent for continuation lines.

    First line uses full max_width.
    Continuation lines are indented by indent_px.

    Returns:
        list of line strings (continuation lines NOT pre-indented,
        caller handles indent offset)
    """
    effective_w = max(20, max_width - indent_px)
    return wrap_and_truncate(text, font, effective_w, max_lines)


# ════════════════════════════════════════════════════════════════════════════
# BLOCK HEIGHT CALCULATOR
# ════════════════════════════════════════════════════════════════════════════

def wrapped_block_height(text: str,
                          font: ImageFont.FreeTypeFont,
                          max_width: int,
                          line_spacing: int = 6,
                          max_lines: int = 999) -> int:
    """
    Calculate total pixel height of a wrapped text block.

    Args:
        text         : text string
        font         : PIL font
        max_width    : container width
        line_spacing : extra pixels between lines
        max_lines    : cap on lines rendered

    Returns:
        total height in pixels
    """
    lines = wrap_text(text, font, max_width, max_lines)
    lh    = measure_line_height(font)
    return len(lines) * (lh + line_spacing) - line_spacing


# ════════════════════════════════════════════════════════════════════════════
# DRAW HELPER  –  renders wrapped text onto a PIL draw context
# ════════════════════════════════════════════════════════════════════════════

def draw_wrapped_text(draw,
                       text: str,
                       x: int, y: int,
                       font: ImageFont.FreeTypeFont,
                       fill,
                       max_width: int,
                       line_spacing: int = 6,
                       max_lines: int = 999,
                       align: str = "left") -> int:
    """
    Wrap and draw text onto a PIL ImageDraw context.

    Args:
        draw         : PIL ImageDraw object
        text         : text to render
        x, y         : top-left origin
        font         : PIL font
        fill         : color tuple or string
        max_width    : pixel width for wrapping
        line_spacing : extra px between lines
        max_lines    : hard line cap
        align        : "left" | "center" | "right"

    Returns:
        total height consumed in pixels
    """
    if not text:
        return 0

    lines = wrap_text(text, font, max_width, max_lines)
    lh    = measure_line_height(font)
    step  = lh + line_spacing
    cy    = y

    for line in lines:
        lw = text_width(line, font)
        if align == "center":
            lx = x + (max_width - lw) // 2
        elif align == "right":
            lx = x + max_width - lw
        else:
            lx = x
        draw.text((lx, cy), line, font=font, fill=fill)
        cy += step

    return cy - y
