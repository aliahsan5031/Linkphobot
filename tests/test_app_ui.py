"""Smoke tests for the Gradio wiring. Skipped when gradio is not installed."""

import pytest

pytest.importorskip("gradio")

import app  # noqa: E402

from .conftest import FakeClient  # noqa: E402


def test_ui_builds_with_all_tabs_and_handlers():
    demo = app.build_ui()
    assert demo is not None


def test_generate_handler_returns_six_outputs(monkeypatch, valid_reply):
    from linkphobot import pipeline

    monkeypatch.setattr(
        pipeline, "generate_content",
        lambda topic, model, key, style, client=None, use_cache=True:
            __import__("linkphobot.content", fromlist=["x"]).generate_content(
                topic, model, key, style, client=FakeClient(valid_reply), use_cache=False),
    )
    out = app.generate("AI in healthcare", "auto", "default", "educational", "portrait", "", "k")
    assert len(out) == 6
    status, image, caption, path, json_text, meta = out
    assert status.endswith("Artificial Intelligence in Healthcare"[:45])
    assert image.size == (1080, 1350)
    assert caption and path and json_text.startswith("{") and "Tokens" in meta


def test_generate_handler_shows_user_errors_without_a_traceback():
    status, image, caption, path, json_text, meta = app.generate(
        "ab", "auto", "default", "educational", "portrait", "", ""
    )
    assert "at least 3 characters" in status
    assert image is None and path is None
    assert "Traceback" not in caption


def test_unexpected_errors_name_the_exception_type(monkeypatch):
    def boom(*args, **kwargs):
        raise TypeError("internal detail that should not reach the page")

    monkeypatch.setattr(app, "run_one", boom)
    status, image, caption, *_ = app.generate(
        "A valid topic here", "auto", "default", "educational", "portrait", "", "k"
    )
    assert "TypeError" in status and "Space logs" in status
    assert "internal detail" not in status + caption
    assert image is None


def test_rerender_handler_keeps_outputs_when_json_is_broken():
    out = app.rerender_edited("{ broken", "auto", "educational", "portrait", "")
    assert "syntax error" in out[0]
    assert len(out) == 6  # the other five are gr.update() no-ops, so the page keeps its content


def test_batch_handler_reports_missing_key():
    zip_path, message = app.generate_batch("a topic", "auto", "default", "educational",
                                           "portrait", "", "")
    assert zip_path is None and "GROQ_API_KEY" in message
