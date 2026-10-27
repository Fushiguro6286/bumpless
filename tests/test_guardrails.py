from bumpless.pipeline.review import guardrail_violations, is_test_file

BEFORE = """import pytest

def test_a():
    assert f() == 1

def test_b():
    with pytest.raises(ValueError):
        g()
"""


def test_api_migration_in_tests_is_allowed():
    after = BEFORE.replace("f()", "f_new()")
    assert guardrail_violations("tests/test_x.py", BEFORE, after) == []


def test_deleting_an_assert_is_rejected():
    after = BEFORE.replace("    assert f() == 1\n", "    f()\n")
    assert any("removes assertions" in v for v in guardrail_violations("tests/test_x.py", BEFORE, after))


def test_adding_skip_is_rejected():
    after = BEFORE.replace("def test_a", "@pytest.mark.skip(reason='v2')\ndef test_a")
    assert any("skip" in v for v in guardrail_violations("tests/test_x.py", BEFORE, after))


def test_xfail_and_trivial_assert_and_deleted_test_rejected():
    xfail = BEFORE.replace("def test_b", "@pytest.mark.xfail\ndef test_b")
    assert guardrail_violations("tests/test_x.py", BEFORE, xfail)
    assert guardrail_violations("tests/test_x.py", BEFORE, BEFORE.replace("assert f() == 1", "assert True"))
    assert guardrail_violations("tests/test_x.py", BEFORE, BEFORE.split("def test_b")[0])


def test_ci_and_secrets_rejected():
    assert guardrail_violations(".github/workflows/ci.yml", "a", "b")
    assert guardrail_violations("app/x.py", "", 'API_KEY = "abcdefghijklmnopqrstuvwxyz"\n')


def test_is_test_file():
    assert is_test_file("tests/test_a.py") and is_test_file("pkg/a_test.py") and is_test_file("conftest.py")
    assert not is_test_file("app/models.py")
