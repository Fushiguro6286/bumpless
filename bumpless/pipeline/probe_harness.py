# Bumpless characterization harness. Copied verbatim into the target repo as tests/_bumpless/_harness.py.
# It records what code *does* (data returned, raised vs not raised, exception category), never message text,
# and serializes values generically so the observation is identical across library versions.
import builtins
import dataclasses
import datetime
import decimal
import enum
import json
import pathlib
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_BUILTIN_EXC = tuple(v for v in vars(builtins).values() if isinstance(v, type) and issubclass(v, BaseException))


def category(exc: BaseException) -> str:
    """The first built-in exception class in the MRO (e.g. ValueError), stable across library versions."""
    for cls in type(exc).__mro__:
        if cls in _BUILTIN_EXC:
            return cls.__name__
    return "Exception"


def norm(v, depth=0):
    if depth > 8:
        return "<deep>"
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        try:  # JSON text is compared by meaning, not formatting
            parsed = json.loads(v)
            if isinstance(parsed, (dict, list)):
                return {"__json__": norm(parsed, depth + 1)}
        except ValueError:
            pass
        return v
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return v.isoformat()
    if isinstance(v, (decimal.Decimal, uuid.UUID, pathlib.PurePath)):
        return str(v)
    if isinstance(v, enum.Enum):
        return norm(v.value, depth + 1)
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if isinstance(v, dict):
        return {str(k): norm(x, depth + 1) for k, x in sorted(v.items(), key=lambda kv: str(kv[0]))}
    if isinstance(v, (list, tuple)):
        return [norm(x, depth + 1) for x in v]
    if isinstance(v, (set, frozenset)):
        return sorted((norm(x, depth + 1) for x in v), key=repr)
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return {"__type__": type(v).__name__, **norm(dataclasses.asdict(v), depth + 1)}
    if isinstance(v, type):
        return {"__class__": v.__name__}
    if hasattr(v, "__dict__"):
        public = {k: x for k, x in vars(v).items() if not k.startswith("_")}
        return {"__type__": type(v).__name__, **norm(public, depth + 1)}
    return {"__type__": type(v).__name__}


OBS: dict = {}


def observe(name: str, fn) -> None:
    try:
        OBS[name] = {"raised": False, "value": norm(fn())}
    except Exception as e:  # recording the category is the point
        OBS[name] = {"raised": True, "category": category(e)}


def dump() -> str:
    return json.dumps(OBS, sort_keys=True, indent=1)
