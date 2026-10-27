You write a characterization probe for a Python repository that is about to be migrated from `{{package}}` {{from}}
to {{to}}. The probe records what the code does today so we can prove behavior is unchanged after the migration.

Write a function `probe()` that imports the repository's own modules and calls their public functions, classes and
methods with representative inputs, wrapping each call in `observe("unique_name", lambda: <expression>)`.
`observe` records the returned value (serialized generically) or, if it raises, only that it raised and the
exception category. Cover: valid inputs, invalid inputs that should be rejected, serialization/parsing helpers,
defaults, optional fields, nested objects, and round trips. Aim for 15-40 observations.

Rules:
- Call ONLY the repository's own code. Never call methods or functions of `{{package}}` directly in the probe
  (e.g. no .dict(), .model_dump(), .json(), parse_obj); call the repository functions that do that instead.
  Reading attributes (obj.name) and constructing the repository's classes is fine.
- Never patch, mock, monkeypatch or assign attributes of `{{package}}` (that ties the recording to the old API).
- The repository's conftest.py files (shown below if present) are executed before probe() runs, so their
  module-level setup applies (e.g. a local fake server or environment variables); pytest fixtures are not available.
  Skip functions that cannot run offline with that setup.
- Use fixed inputs only: no randomness, no current time (use fixed datetimes), no internet, no files.
- Every observe name must be unique and descriptive.
- Output only a Python code block containing the imports and `def probe():`. Do not define observe.

Example:
```python
from datetime import datetime
from app.models import Item
from app.service import to_payload

def probe():
    observe("item_valid", lambda: Item(id=1, name="a", created=datetime(2024, 1, 1)))
    observe("item_bad_id", lambda: Item(id="x", name="a", created=datetime(2024, 1, 1)))
    observe("payload", lambda: to_payload(Item(id=1, name="a", created=datetime(2024, 1, 1))))
```
{{feedback}}
Repository files that use {{package}}:
{{files}}
