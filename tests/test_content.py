import json

import pytest

from linkphobot.content import (
    ContentError,
    clean_topic,
    extract_json,
    generate_content,
    repair_json,
    validate,
)

from .conftest import FakeAPIError, FakeClient, make_payload

# ------------------------------------------------------------------ JSON repair


def test_extract_json_ignores_fences_and_chatter():
    raw = 'Sure! Here you go:\n```json\n{"a": 1}\n```\nHope that helps.'
    assert json.loads(extract_json(raw)) == {"a": 1}


def test_braces_inside_strings_do_not_confuse_extraction():
    raw = '{"text": "use {curly} and }brackets{", "n": 2}'
    assert repair_json(raw) == {"text": "use {curly} and }brackets{", "n": 2}


def test_trailing_commas_are_repaired():
    assert repair_json('{"a": [1, 2,], "b": 3,}') == {"a": [1, 2], "b": 3}


def test_truncated_output_is_recovered():
    full = json.dumps(make_payload())
    cut = full[: full.index('"statistics"') + 40]  # cut off mid-way through statistics
    data = repair_json(cut)
    assert data["title"] == "Artificial Intelligence in Healthcare"
    assert len(data["sections"]) == 4


def test_no_json_raises():
    with pytest.raises(ValueError):
        repair_json("I cannot help with that.")


# -------------------------------------------------------------------- validation


def test_validate_enforces_limits_and_shape():
    data = make_payload(
        sections=make_payload()["sections"] + [{"heading": "Fifth", "content": ["x"]}],
        statistics=[{"value": str(i), "label": "l"} for i in range(6)],
        hashtags=["ai", "#AI", "Machine Learning", "#data"] + [f"t{i}" for i in range(10)],
        color_theme="not_a_theme",
    )
    out = validate(data, "topic")
    assert len(out["sections"]) == 4
    assert len(out["statistics"]) == 3
    assert out["color_theme"] == "professional"
    assert len(out["hashtags"]) <= 8
    assert out["hashtags"][0] == "#ai"
    assert "#AI" not in out["hashtags"]  # case-insensitive duplicate removed
    assert "#MachineLearning" in out["hashtags"]


def test_validate_does_not_invent_filler_key_points():
    out = validate({"title": "T", "sections": [{"heading": "H", "content": ["a"]}]}, "T")
    assert out["key_points"] == []
    assert out["statistics"] == []


def test_validate_survives_garbage_types():
    out = validate(
        {"sections": ["nope", {"heading": 5, "content": "single string"}], "statistics": "x",
         "key_points": None, "hashtags": 7},
        "My Topic Here",
    )
    assert out["sections"][0]["content"] == ["single string"]
    assert out["statistics"] == []
    assert out["key_points"] == []
    assert out["hashtags"] == ["#Topic", "#Here"]  # derived from the topic's longer words


def test_validate_clips_long_text_on_a_word_boundary():
    out = validate({"title": "word " * 60, "sections": []}, "t")
    assert len(out["title"]) <= 81
    assert out["title"].endswith("…")


def test_validate_rejects_non_objects():
    with pytest.raises(ValueError):
        validate([], "t")


# ------------------------------------------------------------------------ topics


def test_clean_topic_normalises_and_limits():
    assert clean_topic("  hello \n\t world  ") == "hello world"
    with pytest.raises(ContentError):
        clean_topic("ab")
    with pytest.raises(ContentError):
        clean_topic("x" * 201)
    with pytest.raises(ContentError):
        clean_topic(None)


# -------------------------------------------------------------------- generation


def test_generate_returns_validated_content(valid_reply):
    client = FakeClient(valid_reply)
    data = generate_content("AI in healthcare", client=client)
    assert data["title"] == "Artificial Intelligence in Healthcare"
    assert data["_tokens"] == 123
    assert data["_model"] == "fake-model"
    assert data["_cached"] is False


def test_identical_requests_are_served_from_cache(valid_reply):
    client = FakeClient(valid_reply)
    generate_content("AI in healthcare", client=client)
    again = generate_content("  ai IN healthcare ", client=client)  # same after normalising
    assert client.calls == 1
    assert again["_cached"] is True


def test_cache_key_includes_model_and_style(valid_reply):
    client = FakeClient(valid_reply)
    generate_content("topic here", model="default", caption_style="story", client=client)
    generate_content("topic here", model="fast", caption_style="story", client=client)
    generate_content("topic here", model="fast", caption_style="listicle", client=client)
    assert client.calls == 3


def test_use_cache_false_always_calls(valid_reply):
    client = FakeClient(valid_reply)
    generate_content("topic here", client=client, use_cache=False)
    generate_content("topic here", client=client, use_cache=False)
    assert client.calls == 2


def test_cached_copy_cannot_be_mutated_through_the_cache(valid_reply):
    client = FakeClient(valid_reply)
    first = generate_content("topic here", client=client)
    first["title"] = "MUTATED"
    assert generate_content("topic here", client=client)["title"] != "MUTATED"


def test_rate_limit_is_retried_then_succeeds(valid_reply):
    client = FakeClient(FakeAPIError(429), FakeAPIError(503), valid_reply)
    data = generate_content("topic here", client=client)
    assert client.calls == 3
    assert data["title"]


def test_retries_give_up_with_a_friendly_message():
    client = FakeClient(FakeAPIError(429))
    with pytest.raises(ContentError, match="rate limit"):
        generate_content("topic here", client=client)
    assert client.calls == 3


def test_bad_api_key_is_not_retried():
    client = FakeClient(FakeAPIError(401))
    with pytest.raises(ContentError, match="API key"):
        generate_content("topic here", client=client)
    assert client.calls == 1


def test_malformed_model_output_becomes_a_clean_error():
    with pytest.raises(ContentError, match="malformed"):
        generate_content("topic here", client=FakeClient("sorry, no JSON today"))


def test_missing_api_key_is_explained():
    with pytest.raises(ContentError, match="GROQ_API_KEY"):
        generate_content("topic here")


def test_retired_model_falls_back_to_the_next_one(valid_reply):
    client = FakeClient(FakeAPIError(404, "model does not exist"), valid_reply)
    data = generate_content("topic here", client=client, use_cache=False)
    assert data["title"]
    assert client.models == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


def test_all_models_unavailable_gives_a_clean_error():
    client = FakeClient(FakeAPIError(404, "model does not exist"))
    with pytest.raises(ContentError, match="rejected the request"):
        generate_content("topic here", client=client, use_cache=False)
    assert client.calls == 3  # each distinct model tried once, no retry loop on 404


def test_reasoning_models_get_low_effort_and_room_for_the_answer(valid_reply):
    client = FakeClient(valid_reply)
    generate_content("topic here", client=client, use_cache=False)
    assert client.kwargs[0]["extra_body"] == {"reasoning_effort": "low"}
    assert client.kwargs[0]["max_tokens"] >= 4000
