"""Tests against the real ``groq`` package, not the fake client.

The fake client cannot catch dependency problems: groq 0.11.0 with httpx 0.28
raised ``TypeError: ... unexpected keyword argument 'proxies'`` on construction,
which broke every generation on a fresh install.
"""

import httpx
import pytest

groq = pytest.importorskip("groq")

from linkphobot import content  # noqa: E402

from .conftest import FakeClient, make_payload  # noqa: E402


def test_installed_groq_client_can_be_constructed():
    content._client_for.cache_clear()
    client = content._client_for("gsk_not_a_real_key")
    assert hasattr(client.chat.completions, "create")


def _real_error(cls, status):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return cls("boom", response=httpx.Response(status, request=request), body=None)


def test_real_rate_limit_errors_are_retried():
    import json

    error = _real_error(groq.RateLimitError, 429)
    client = FakeClient(error, error, json.dumps(make_payload()))
    assert content.generate_content("topic here", client=client)["title"]
    assert client.calls == 3


def test_real_auth_errors_are_not_retried():
    client = FakeClient(_real_error(groq.AuthenticationError, 401))
    with pytest.raises(content.ContentError, match="API key"):
        content.generate_content("topic here", client=client)
    assert client.calls == 1


def test_real_connection_errors_are_retried_then_reported():
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    client = FakeClient(groq.APIConnectionError(request=request))
    with pytest.raises(content.ContentError, match="Could not reach Groq"):
        content.generate_content("topic here", client=client)
    assert client.calls == 3
