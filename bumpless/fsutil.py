"""Read/write repo files byte-faithfully (no newline translation, which Windows would otherwise apply)."""

from pathlib import Path


def read(path: Path) -> str:
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
