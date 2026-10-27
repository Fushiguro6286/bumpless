from types import SimpleNamespace

from bumpless.pipeline.context import TestRun as Run
from bumpless.pipeline.run import CHAR, final_status

REPO = [f"tests.test_m::t{i}" for i in range(7)]


def ctx(after: Run) -> SimpleNamespace:
    return SimpleNamespace(review={}, tests={
        "old": Run(passed=7, repo_passed=7),
        "new_before": Run(passed=0, repo_passed=0, failed=7, failing=REPO),
        "after": after})


def test_passing_characterization_tests_alone_are_not_progress():
    # openai_moderator, benchmark 20261027-234520: 0/7 repo tests fixed, 1 generated behavior test passing
    after = Run(passed=1, repo_passed=0, failed=35, failing=REPO + [f"{CHAR}.test_characterization::b{i}" for i in range(28)])
    assert final_status(ctx(after)) == "failed"


def test_fixing_some_repo_tests_is_partial():
    after = Run(passed=4, repo_passed=4, failed=3, failing=REPO[:3])
    assert final_status(ctx(after)) == "partial"
