import pytest

from bumpless.bench import aggregate, load, summarize


def _result(status, after_failing, coverage=80.0):
    return {
        "status": status, "old_version": "1.10.18", "new_version": "2.9.0",
        "tests": {"old": {"passed": 3},
                  "new_before": {"passed": 1, "repo_passed": 1, "failing": ["tests.test_a::t1", "tests.test_a::t2"]},
                  "after": {"passed": 13 - len(after_failing), "repo_passed": 3 - sum(not x.startswith("tests._bumpless")
                                                                                     for x in after_failing),
                            "failing": after_failing}},
        "characterization": {"observations": 10},
        "coverage": {"measured": True, "percent": coverage},
        "duration_s": 100.0, "cost": {"total_usd": 0.1, "by_tier": {"nano": 0.1}},
        "escalations": [{}], "recipe_reused": False, "manual_review": [],
    }


def test_summarize_counts_only_repo_tests_as_fixed():
    s = summarize(_result("partial", ["tests.test_a::t2", "tests._bumpless.test_c::x"]))
    assert (s["tests_failing_before_fix"], s["tests_fixed"]) == (2, 1)
    assert s["characterization_pass_rate"] == 0.9
    assert s["escalations"] == 1


def test_aggregate_medians_and_rates():
    rows = [summarize(_result("green", [], 100.0)), summarize(_result("failed", ["tests.test_a::t1"], 50.0)),
            summarize(_result("green", [], 90.0))]
    a = aggregate(rows)
    assert (a["green"], a["failed"], a["success_rate"]) == (2, 1, 0.667)
    assert a["median_coverage_percent"] == 90.0
    assert a["total_cost_usd"] == pytest.approx(0.3)


def test_real_repos_must_pin_a_sha(tmp_path):
    f = tmp_path / "repos.yaml"
    f.write_text("repos:\n  - {name: x, kind: real, source: 'https://github.com/a/b', package: p, to: '>=2'}\n")
    with pytest.raises(ValueError, match="pin a commit SHA"):
        load(f)
