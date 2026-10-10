import json
import os
import zipfile

import pytest

from linkphobot.config import MAX_BATCH, get_api_key, get_brand
from linkphobot.content import ContentError
from linkphobot.export import cleanup_old_files, output_dir, save_png, slugify
from linkphobot.pipeline import parse_topics, rerender, run_batch, run_one

from .conftest import FakeClient

# --------------------------------------------------------------------- run_one


def test_run_one_produces_image_caption_and_files(valid_reply):
    result = run_one("AI in healthcare", client=FakeClient(valid_reply), style="listicle")
    assert result.image.size == (1080, 1350)
    assert os.path.isfile(result.png_path)
    assert result.caption.splitlines()[-1].startswith("#AI")
    assert json.loads(result.json_text)["title"] == result.title
    assert "_tokens" not in result.json_text  # internal fields stay out of the editable JSON
    assert "Tokens:   123" in result.meta


def test_run_one_square_and_theme_override(valid_reply):
    result = run_one("AI in healthcare", theme="cyber_dark", size="square",
                     client=FakeClient(valid_reply))
    assert result.image.size == (1080, 1080)
    assert json.loads(result.json_text)["color_theme"] == "cyber_dark"


def test_second_identical_run_is_free(valid_reply):
    client = FakeClient(valid_reply)
    run_one("AI in healthcare", client=client)
    again = run_one("AI in healthcare", client=client)
    assert client.calls == 1
    assert "from cache" in again.meta


# -------------------------------------------------------------------- rerender


def test_rerender_applies_edits_without_any_api_call(valid_reply):
    first = run_one("AI in healthcare", client=FakeClient(valid_reply))
    edited = json.loads(first.json_text)
    edited["title"] = "A Corrected Title"
    result = rerender(json.dumps(edited), size="portrait")
    assert result.title == "A Corrected Title"
    assert os.path.isfile(result.png_path)


def test_rerender_reports_json_syntax_errors_with_the_line_number():
    with pytest.raises(ContentError, match="line 2"):
        rerender('{\n  "title": oops\n}')


def test_rerender_rejects_non_objects():
    with pytest.raises(ContentError, match="object"):
        rerender("[1, 2, 3]")
    with pytest.raises(ContentError):
        rerender("")


# ----------------------------------------------------------------------- batch


def test_parse_topics_drops_blanks_and_duplicates():
    assert parse_topics("  A topic \n\nA TOPIC\nSecond   one\n") == ["A topic", "Second one"]
    assert parse_topics("") == []


def test_batch_zips_successes_and_reports_failures(valid_reply):
    client = FakeClient(valid_reply, "not json at all", valid_reply)
    zip_path, summary = run_batch("first topic\nsecond topic\nthird topic",
                                  client=client, api_key="x")
    assert "2 of 3 generated" in summary
    assert "second topic" in summary
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
    assert sum(n.endswith(".png") for n in names) == 2
    assert sum(n.endswith(".txt") for n in names) == 3  # 2 captions + errors.txt
    assert "errors.txt" in names


def test_batch_is_capped(valid_reply):
    topics = "\n".join(f"topic number {i}" for i in range(MAX_BATCH + 3))
    _, summary = run_batch(topics, client=FakeClient(valid_reply), api_key="x")
    assert f"{MAX_BATCH} of {MAX_BATCH} generated" in summary
    assert "3 extra topic(s) skipped" in summary


def test_batch_needs_topics_and_a_key():
    with pytest.raises(ContentError, match="at least one topic"):
        run_batch("  \n ", api_key="x")
    with pytest.raises(ContentError, match="GROQ_API_KEY"):
        run_batch("a topic")


def test_batch_reports_progress(valid_reply):
    seen = []
    run_batch("topic one\ntopic two", client=FakeClient(valid_reply), api_key="x",
              progress=lambda fraction, desc: seen.append((fraction, desc)))
    assert [f for f, _ in seen] == [0.0, 0.5]


# ---------------------------------------------------------------------- config


def test_api_key_precedence(monkeypatch):
    assert get_api_key() == ""
    monkeypatch.setenv("Linkphobot_API", "legacy")
    assert get_api_key() == "legacy"
    monkeypatch.setenv("GROQ_API_KEY", "from-env")
    assert get_api_key() == "from-env"
    assert get_api_key("  typed-in-ui  ") == "typed-in-ui"
    assert get_api_key("   ") == "from-env"


def test_brand_precedence(monkeypatch):
    assert "Linkphobot" in get_brand()
    monkeypatch.setenv("LINKPHOBOT_BRAND", "From Env")
    assert get_brand() == "From Env"
    assert get_brand("  Typed   brand ") == "Typed brand"
    assert len(get_brand("x" * 200)) == 60


# ---------------------------------------------------------------------- export


def test_slugify():
    assert slugify("AI & Healthcare: 2026!") == "ai-healthcare-2026"
    assert slugify("!!!") == "infographic"
    assert len(slugify("a" * 100)) <= 40


def test_save_png_uses_unique_names(valid_reply):
    result = run_one("AI in healthcare", client=FakeClient(valid_reply))
    a = save_png(result.image, "same name")
    b = save_png(result.image, "same name")
    assert a != b and os.path.isfile(a) and os.path.isfile(b)


def test_old_files_are_cleaned_up_but_new_ones_stay(valid_reply):
    result = run_one("AI in healthcare", client=FakeClient(valid_reply))
    old = save_png(result.image, "old")
    fresh = save_png(result.image, "fresh")
    long_ago = os.path.getmtime(old) - 7200
    os.utime(old, (long_ago, long_ago))
    assert cleanup_old_files() >= 1
    assert not os.path.exists(old)
    assert os.path.exists(fresh)
    assert output_dir().is_dir()
