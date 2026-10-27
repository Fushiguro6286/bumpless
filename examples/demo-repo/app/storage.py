import json
from pathlib import Path
from typing import List

from app.models import User


def save_users(path: Path, users: List[User]) -> None:
    """Writes users to disk. Deliberately not covered by any test (exercises Low confidence)."""
    path.write_text(json.dumps([json.loads(u.json()) for u in users]))


def load_users(path: Path) -> List[User]:
    return [User.parse_obj(d) for d in json.loads(path.read_text())]
