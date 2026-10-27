from bumpless.pipeline.edit import apply_block, new_errors, parse_blocks
from bumpless.pipeline.intake import bump_line, find_pins


def test_pins_and_bump(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi==0.95\npydantic==1.10.18  # pinned\n# pydantic old\n")
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = [\n  "pydantic[email]>=1.8,<2",\n]\n')
    pins = find_pins(tmp_path, "pydantic")
    assert [(p.file, p.line_no) for p in pins] == [("requirements.txt", 1), ("pyproject.toml", 2)]
    assert bump_line("pydantic==1.10.18  # pinned", "pydantic", ">=2,<3") == "pydantic>=2,<3  # pinned"
    assert bump_line('  "pydantic[email]>=1.8,<2",', "pydantic", ">=2,<3") == '  "pydantic[email]>=2,<3",'
    assert bump_line("pydantic-settings==1.0", "pydantic", ">=2") == "pydantic-settings==1.0"


def test_parse_blocks_with_paths():
    reply = """DIAGNOSIS: x
app/models.py
<<<<<<< SEARCH R001
    class Config:
        orm_mode = True
=======
    model_config = ConfigDict(from_attributes=True)
>>>>>>> REPLACE
<<<<<<< SEARCH
a
=======
b
>>>>>>> REPLACE
"""
    b = parse_blocks(reply)
    assert len(b) == 2
    assert (b[0].path, b[0].rule_id) == ("app/models.py", "R001")
    assert b[0].replace == "    model_config = ConfigDict(from_attributes=True)\n"
    assert (b[1].path, b[1].rule_id, b[1].search) == (None, "UNSPECIFIED", "a\n")


def test_apply_block_exact_and_tolerant():
    src = "class A:\n    class Config:\n        orm_mode = True\n    x: int\n"
    assert apply_block(src, "        orm_mode = True\n", "        from_attributes = True\n") == \
        "class A:\n    class Config:\n        from_attributes = True\n    x: int\n"
    # model dropped the indentation: still matches, replacement re-indented
    out = apply_block(src, "class Config:\n    orm_mode = True\n", "model_config = ConfigDict(from_attributes=True)\n")
    assert out == "class A:\n    model_config = ConfigDict(from_attributes=True)\n    x: int\n"
    assert apply_block(src, "nope\n", "x") is None
    assert apply_block(src, "\n", "x") is None


def test_new_errors_only_reports_introduced_problems():
    before = "print(undefined_a)\n"
    assert new_errors("f.py", before, before) == []
    errs = new_errors("f.py", before, "print(undefined_a)\nConfigDict()\n")
    assert len(errs) == 1 and "ConfigDict" in errs[0]
    assert new_errors("f.py", before, "def (:\n")[0].startswith("SyntaxError")


def test_apply_single_line_fragment():
    src = "def f(user):\n    return json.loads(user.json())\n"
    assert apply_block(src, "    json.loads(user.json())\n", "    json.loads(user.model_dump_json())\n") == \
        "def f(user):\n    return json.loads(user.model_dump_json())\n"
    assert apply_block("a.json()\nb.json()\n", "x.json()\n", "y") is None
