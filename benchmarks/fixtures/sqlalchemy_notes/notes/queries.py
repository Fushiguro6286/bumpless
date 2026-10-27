from sqlalchemy import func, select

from notes.db import Note, Notebook


def add_note(session, notebook_name, title, body=""):
    notebook = session.query(Notebook).filter_by(name=notebook_name).first()
    if notebook is None:
        notebook = Notebook(name=notebook_name)
        session.add(notebook)
    note = Note(title=title, body=body, notebook=notebook)
    session.add(note)
    session.commit()
    return note.id


def get_note(session, note_id):
    return session.query(Note).get(note_id)


def search(session, term):
    return session.query(Note).filter(Note.title.ilike(f"%{term}%")).order_by(Note.id).all()


def titles(engine, notebook_name):
    stmt = (select([Note.title]).select_from(Note.__table__.join(Notebook.__table__))
            .where(Notebook.name == notebook_name).order_by(Note.id))
    with engine.connect() as conn:
        return [row["title"] for row in conn.execute(stmt)]


def count_by_notebook(engine):
    stmt = (select([Notebook.name, func.count(Note.id).label("n")])
            .select_from(Notebook.__table__.outerjoin(Note.__table__))
            .group_by(Notebook.name).order_by(Notebook.name))
    with engine.connect() as conn:
        return {row["name"]: row["n"] for row in conn.execute(stmt)}


def rename_notebook(engine, old, new):
    engine.execute("UPDATE notebooks SET name = ? WHERE name = ?", new, old)


def bulk_insert(engine, rows):
    with engine.connect() as conn:
        conn.execute(Note.__table__.insert(), rows)


def total_notes(engine):
    return engine.execute("SELECT COUNT(*) FROM notes").scalar()
