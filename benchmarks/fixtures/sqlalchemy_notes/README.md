# sqlalchemy_notes (fixture)

A small notes store written against SQLAlchemy 1.4 using APIs that 2.0 removed: `engine.execute()`, raw SQL
strings, `select([...])`, string keys on rows, and library-level autocommit (2.0 silently rolls back an
uncommitted `connect()` block). Used as the zero-shot generalization test: Bumpless has no recipe for it.
