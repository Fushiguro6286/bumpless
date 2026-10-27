import pytest

from bot.drafts import draft_reply, safe_draft
from bot.models import Ticket, parse_ticket, to_record


def test_parse_and_strip():
    t = parse_ticket('{"id": 1, "subject": "  Login broken ", "body": "help", "tags": "auth, urgent"}')
    assert t.subject == "Login broken" and t.tags == ["auth", "urgent"]


def test_subject_too_short():
    with pytest.raises(ValueError):
        Ticket(id=1, subject="hi", body="x")


def test_record_drops_none():
    assert to_record(Ticket(id=2, subject="Refund", body="pls")) == {"id": 2, "subject": "Refund", "body": "pls", "tags": []}


def test_draft_reply():
    assert draft_reply(Ticket(id=3, subject="Refund", body="pls")) == "Thanks! About: Refund"


def test_safe_draft_falls_back():
    assert safe_draft(Ticket(id=4, subject="BOOM", body="x")) == "A teammate will get back to you shortly."
