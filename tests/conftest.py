"""Shared fixtures: a fake Groq client, sample content, and isolated temp/cache state."""

import json
import tempfile
from types import SimpleNamespace

import pytest

from linkphobot import content as content_module


class FakeAPIError(Exception):
    """Stands in for groq.APIStatusError (only the status code matters)."""

    def __init__(self, status_code: int, message: str = "boom"):
        super().__init__(message)
        self.status_code = status_code


class FakeClient:
    """Minimal ``client.chat.completions.create`` that plays back canned replies.

    Each reply is either a string (the model's text) or an Exception to raise.
    The last reply repeats once the list is exhausted.
    """

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
            usage=SimpleNamespace(total_tokens=123),
            model="fake-model",
        )


def make_payload(**overrides) -> dict:
    payload = {
        "title": "Artificial Intelligence in Healthcare",
        "subtitle": "How AI is reshaping diagnosis, treatment and patient care",
        "sections": [
            {
                "heading": f"Section {i} heading",
                "icon_suggestion": "🩺",
                "content": [
                    "Early detection of disease with medical imaging models",
                    "Personalised treatment plans from patient data",
                    "Third bullet that the old renderer silently dropped",
                ],
            }
            for i in range(1, 5)
        ],
        "key_points": ["AI accelerates diagnosis", "Data quality drives outcomes", "Ethics matter"],
        "statistics": [
            {"value": "94%", "label": "Imaging accuracy", "context": ""},
            {"value": "$150B", "label": "Annual savings by 2026", "context": ""},
            {"value": "30%", "label": "Faster diagnosis", "context": ""},
        ],
        "call_to_action": "Save this post and share it with your network.",
        "linkedin_caption": "AI is changing healthcare.\n\nHere is what to know.",
        "hashtags": ["#AI", "#Healthcare", "#DigitalHealth", "#MedTech", "#Innovation"],
        "color_theme": "health_blue",
        "target_audience": "Clinicians",
        "content_type": "educational",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def payload():
    return make_payload()


@pytest.fixture
def valid_reply():
    return json.dumps(make_payload())


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """No sleeping on retries, a clean cache, and generated files go to tmp_path."""
    monkeypatch.setattr(content_module, "_sleep", lambda _seconds: None)
    content_module.clear_cache()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    for name in ("GROQ_API_KEY", "Linkphobot_API", "LINKPHOBOT_BRAND"):
        monkeypatch.delenv(name, raising=False)
    yield
    content_module.clear_cache()
