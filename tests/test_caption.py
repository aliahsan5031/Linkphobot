from linkphobot.caption import build_caption, normalize_hashtags
from linkphobot.config import CAPTION_STYLES

from .conftest import make_payload


def test_normalize_hashtags():
    tags = normalize_hashtags(["#AI", "ai", "Machine Learning", "#", "", "#Data!"])
    assert tags == ["#AI", "#MachineLearning", "#Data"]
    assert normalize_hashtags("#one two #three") == ["#one", "#two", "#three"]
    assert len(normalize_hashtags([f"t{i}" for i in range(20)], limit=5)) == 5
    assert normalize_hashtags(None) == []


def test_hashtags_are_appended_exactly_once():
    content = make_payload(linkedin_caption="Body text.\n\n#AI #Healthcare #Old")
    caption = build_caption(content)
    assert caption.startswith("Body text.")
    assert caption.count("#AI") == 1
    assert "#Old" not in caption  # model's own trailing hashtags are replaced
    assert caption.splitlines()[-1].startswith("#AI")


def test_at_most_five_hashtags_by_default():
    tags = build_caption(make_payload(hashtags=[f"tag{i}" for i in range(8)])).splitlines()[-1]
    assert len(tags.split()) == 5


def test_caption_style_actually_changes_the_post():
    """Regression: generate() accepted caption_style and ignored it."""
    content = make_payload(linkedin_caption="")
    captions = {style: build_caption(content, style) for style in CAPTION_STYLES}
    assert len(set(captions.values())) == len(CAPTION_STYLES)
    assert "1. " in captions["listicle"]
    assert captions["story"].startswith("A lesson that changed")
    assert "Do you agree?" in captions["thought_leadership"]
    assert captions["data_driven"].startswith("94%")


def test_caption_respects_the_linkedin_length_limit():
    caption = build_caption(make_payload(linkedin_caption="x" * 5000))
    assert len(caption) <= 3000
    assert caption.splitlines()[-1].startswith("#AI")  # hashtags survive the cut


def test_fallback_uses_section_bullets_when_there_are_no_key_points():
    content = make_payload(linkedin_caption="", key_points=[])
    assert "Early detection" in build_caption(content)


def test_caption_without_hashtags():
    assert build_caption(make_payload(hashtags=[], linkedin_caption="Just text")) == "Just text"
