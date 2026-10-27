from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Notebook(Base):
    __tablename__ = "notebooks"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    notes = relationship("Note", back_populates="notebook")


class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    notebook_id = Column(Integer, ForeignKey("notebooks.id"))
    title = Column(String(100), nullable=False)
    body = Column(String, default="")
    notebook = relationship("Notebook", back_populates="notes")


def make_engine(url="sqlite://"):
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return engine


def make_session(engine):
    return sessionmaker(bind=engine)()
