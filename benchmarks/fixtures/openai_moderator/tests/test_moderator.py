import pytest

from mod import client
from mod.pipeline import review


def test_clean_comment_is_visible_with_reply():
    assert review("I love this park") == {"status": "visible", "reply": "Thanks for sharing about park!"}


def test_hateful_comment_hidden_with_categories():
    assert review("I hate you") == {"status": "hidden", "categories": ["hate"]}


def test_categories_multiple():
    assert client.categories("hate and kill") == ["hate", "violence"]


def test_flagged_false():
    assert client.flagged("nice weather") is False


def test_suggest_reply_strips_whitespace():
    assert client.suggest_reply("great talk") == "Thanks for sharing about talk!"


def test_bad_key_means_pending(monkeypatch):
    monkeypatch.setattr(client.openai, "api_key", "sk-wrong")
    assert review("hello") == {"status": "pending", "reason": "bad key"}


def test_offline_means_pending(monkeypatch):
    monkeypatch.setattr(client.openai, "api_base", "http://127.0.0.1:9/v1")
    with pytest.raises(client.ModerationUnavailable, match="offline"):
        client.flagged("hello")
