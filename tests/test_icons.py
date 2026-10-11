import pytest
from PIL import Image, ImageDraw

from linkphobot.icons import FALLBACK_ORDER, ICONS, KEYWORDS, draw_icon, pick_icons


@pytest.mark.parametrize("name", sorted(ICONS))
def test_every_icon_draws_something_inside_its_box(name):
    img = Image.new("RGB", (200, 200), (0, 0, 0))
    draw_icon(ImageDraw.Draw(img), name, 100, 100, 100, (255, 255, 255))
    box = img.getbbox()
    assert box is not None, f"{name} drew nothing"
    assert 30 <= box[0] and box[2] <= 170 and 30 <= box[1] and box[3] <= 170


def test_keyword_icons_all_exist():
    assert set(KEYWORDS) <= set(ICONS) and set(FALLBACK_ORDER) <= set(ICONS)


def test_icons_follow_the_meaning_of_the_section():
    icons = pick_icons([
        {"heading": "Patient care", "content": ["Better health outcomes"]},
        {"heading": "Cost savings", "content": ["Lower budget"]},
        {"heading": "Data privacy", "content": ["Security and trust"]},
    ])
    assert icons == ["heart", "dollar", "shield"]


def test_icons_are_distinct_and_deterministic():
    sections = [{"heading": f"Plain heading {i}", "content": ["nothing special"]} for i in range(6)]
    first = pick_icons(sections)
    assert len(set(first)) == len(first)
    assert pick_icons(sections) == first


def test_short_keywords_match_whole_words_only():
    # "ai" must not fire inside "maintain" or "said"
    icons = pick_icons([{"heading": "We maintain what was said", "content": []}])
    assert icons != ["network"]
    assert pick_icons([{"heading": "AI in practice", "content": []}]) == ["network"]
