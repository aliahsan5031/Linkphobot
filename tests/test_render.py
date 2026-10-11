import pytest

from linkphobot.config import PALETTES, SIZES
from linkphobot.render import (
    clean,
    contrast,
    ensure_contrast,
    hex_to_rgb,
    load_font,
    make_style,
    render_infographic,
    render_with_layout,
    wrap_text,
    WHITE,
)

from .conftest import make_payload


def assert_clean_layout(boxes, size):
    """Blocks must be ordered, non-overlapping and inside the canvas."""
    width, height = SIZES[size]
    assert boxes[0]["name"] == "header" and boxes[0]["y0"] == 0
    assert boxes[-1]["name"] == "footer" and boxes[-1]["y1"] == height
    for prev, nxt in zip(boxes, boxes[1:], strict=False):
        assert prev["y1"] <= nxt["y0"], f"{prev['name']} overlaps {nxt['name']}"
    assert all(0 <= b["y0"] < b["y1"] <= height for b in boxes)


@pytest.mark.parametrize("size", ["portrait", "square"])
def test_full_content_has_no_overlap(size):
    """Regression: stats used to print over the call-to-action (y 1196-1306 vs 1252)."""
    img, boxes = render_with_layout(make_payload(), size=size)
    assert img.size == SIZES[size]
    assert_clean_layout(boxes, size)


def test_portrait_keeps_every_block_for_typical_content():
    _, boxes = render_with_layout(make_payload(), size="portrait")
    names = [b["name"] for b in boxes]
    assert names == [
        "header", "section_row_1", "section_row_2", "key_points", "stats", "footer",
    ]


@pytest.mark.parametrize("size", ["portrait", "square"])
def test_extreme_content_still_fits(size):
    long = "An extremely long bullet that keeps going and going " * 6
    payload = make_payload(
        title="Why " + "very long titles " * 15,
        subtitle=long,
        sections=[{"heading": long, "content": [long] * 4} for _ in range(4)],
        call_to_action=long,
        key_points=[long] * 3,
        hashtags=[f"#tag{i}" for i in range(8)],
    )
    _, boxes = render_with_layout(payload, size=size, brand="B" * 200)
    assert_clean_layout(boxes, size)


def test_minimal_content_renders():
    img, boxes = render_with_layout({"title": "Just a title"}, size="portrait")
    assert_clean_layout(boxes, "portrait")
    assert img.size == (1080, 1350)


@pytest.mark.parametrize("theme", sorted(PALETTES))
def test_every_theme_renders(theme):
    img = render_infographic(make_payload(), color_theme=theme)
    assert img.size == (1080, 1350)


def test_unknown_theme_falls_back():
    img = render_infographic(make_payload(), color_theme="does_not_exist")
    assert img.size == (1080, 1350)


@pytest.mark.parametrize("theme", sorted(PALETTES))
def test_header_text_is_readable_on_every_theme(theme):
    """White header text needs 4.5:1; dev_dark's light-blue primary used to fail this."""
    assert contrast(WHITE, make_style(theme).header) >= 4.5


def test_ensure_contrast_reaches_target_or_pure_black_white():
    bg = hex_to_rgb("#FFFFFF")
    out = ensure_contrast(hex_to_rgb("#F4A261"), bg)
    assert contrast(out, bg) >= 4.5


# ----------------------------------------------------------------------- text


def test_emoji_are_stripped_instead_of_drawn_as_boxes():
    assert clean("🩺 Health 🚀") == "Health"
    assert clean("Plain text stays") == "Plain text stays"


def test_wrap_never_exceeds_the_width():
    font = load_font(21)
    text = "Early detection of disease with medical imaging models and more words here"
    lines = wrap_text(text, font, 300, 10)
    assert len(lines) > 1
    assert all(font.getlength(line) <= 300 for line in lines)
    assert " ".join(lines) == text  # nothing lost when there is room


def test_wrap_truncates_with_ellipsis_at_max_lines():
    font = load_font(21)
    lines = wrap_text("word " * 80, font, 300, 2)
    assert len(lines) == 2
    assert lines[-1].endswith("…")
    assert all(font.getlength(line) <= 300 for line in lines)


def test_wrap_splits_a_word_wider_than_the_line():
    font = load_font(21)
    lines = wrap_text("A" * 200, font, 200, 99)
    assert len(lines) > 1
    assert all(font.getlength(line) <= 200 for line in lines)


def test_default_font_is_scalable():
    assert load_font(40).getlength("Hello") > load_font(12).getlength("Hello")


def test_bundled_fonts_load_and_differ_by_weight():
    from linkphobot.render import _bundled_bytes

    for weight in ("regular", "medium", "semibold", "bold", "display"):
        assert _bundled_bytes(weight), f"{weight} font is missing or unreadable"
    regular = load_font(40, weight="regular").getlength("Linkphobot")
    bold = load_font(40, weight="bold").getlength("Linkphobot")
    assert bold > regular


def test_text_survives_greek_and_cyrillic_without_missing_glyph_boxes():
    font = load_font(40, weight="regular")
    # the .notdef box is wider than a real letter; both scripts should measure like letters
    assert font.getlength("Привет") < 6 * 40
    assert font.getlength("Γειά") < 4 * 40


def test_percent_values_get_a_ring_and_others_do_not():
    from linkphobot.render import _percent

    assert _percent("94%") == 0.94
    assert _percent("12.5 %") == 0.125
    assert _percent("$150B") is None
    assert _percent("300%") is None  # over 100 % cannot be shown as a ring


def test_rendered_image_is_downsampled_to_the_exact_canvas():
    img = render_infographic(make_payload(), size="square")
    assert img.size == SIZES["square"] and img.mode == "RGB"


def test_dense_content_output_has_no_blank_canvas():
    img = render_infographic(make_payload())
    assert len(img.getcolors(maxcolors=5_000_000)) > 500  # gradients, shadows, text
