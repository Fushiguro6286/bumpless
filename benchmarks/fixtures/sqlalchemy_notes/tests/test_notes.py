import pytest

from notes.db import make_engine, make_session
from notes.queries import (add_note, bulk_insert, count_by_notebook, get_note, rename_notebook, search, titles,
                           total_notes)


@pytest.fixture
def engine(tmp_path):
    return make_engine(f"sqlite:///{tmp_path / 'notes.db'}")


@pytest.fixture
def session(engine):
    s = make_session(engine)
    yield s
    s.close()


def test_add_and_get(session):
    note_id = add_note(session, "work", "Plan", "q4 goals")
    note = get_note(session, note_id)
    assert note.title == "Plan" and note.body == "q4 goals" and note.notebook.name == "work"


def test_search(session):
    add_note(session, "work", "Weekly plan")
    add_note(session, "home", "Groceries")
    assert [n.title for n in search(session, "PLAN")] == ["Weekly plan"]


def test_titles_in_order(engine, session):
    add_note(session, "work", "A")
    add_note(session, "home", "B")
    add_note(session, "work", "C")
    assert titles(engine, "work") == ["A", "C"]


def test_count_by_notebook(engine, session):
    add_note(session, "work", "A")
    add_note(session, "work", "B")
    add_note(session, "home", "C")
    assert count_by_notebook(engine) == {"home": 1, "work": 2}


def test_rename_notebook(engine, session):
    add_note(session, "work", "A")
    rename_notebook(engine, "work", "job")
    assert titles(engine, "job") == ["A"]


def test_bulk_insert_persists(engine, session):
    add_note(session, "work", "A")
    bulk_insert(engine, [{"notebook_id": 1, "title": "X"}, {"notebook_id": 1, "title": "Y"}])
    assert total_notes(engine) == 3
