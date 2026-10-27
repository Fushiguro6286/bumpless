import pytest

from app import llm
from app.summarize import bullet_points, similarity, summarize


def test_chat_returns_content():
    assert llm.chat("hello world") == "SUMMARY: hello world"


def test_usage():
    assert llm.chat_usage("one two three") == {"prompt": 3, "completion": 3}


def test_embed_shapes():
    vecs = llm.embed(["aa", "abc"])
    assert vecs == [[2.0, 2.0, 1.0], [3.0, 1.0, 1.0]]


def test_rate_limit_maps_to_rate_limited():
    with pytest.raises(llm.RateLimited):
        llm.chat("RATE_LIMIT please")


def test_other_errors_map_to_llm_error():
    with pytest.raises(llm.LLMError) as info:
        llm.chat("BOOM")
    assert not isinstance(info.value, llm.RateLimited)


def test_summarize_and_similarity():
    assert summarize("some long text").startswith("SUMMARY:")
    assert similarity("aa", "aa") == 1.0


def test_bullet_points_skip_rate_limited():
    assert bullet_points(["x", "RATE_LIMIT"]) == ["- SUMMARY: x", "- (skipped: rate limited)"]
