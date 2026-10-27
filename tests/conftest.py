import os
import tempfile
from pathlib import Path

# Isolate the DB before bumpless.settings is imported anywhere.
os.environ["BUMPLESS_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
