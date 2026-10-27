from packaging.version import Version

from bumpless.radar.radar import current_version, dependencies, usage_count


def test_dependencies_and_versions(tmp_path):
    (tmp_path / "requirements.txt").write_text("pydantic==1.10.18\nrequests>=2.0,<3  # http\nflask\n")
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["openai~=0.28.1", "rich[jupyter]>=13"]\n')
    deps = dependencies(tmp_path)
    assert deps == {"pydantic": "==1.10.18", "requests": ">=2.0,<3", "openai": "~=0.28.1", "rich": ">=13"}
    assert current_version(deps["pydantic"]) == Version("1.10.18")
    assert current_version(deps["requests"]) == Version("2.0")


def test_usage_count(tmp_path):
    (tmp_path / "a.py").write_text("import openai as oa\nfrom openai import error\noa.x\noa.y\nerror.E\n")
    (tmp_path / "b.py").write_text("import json\n")
    assert usage_count(tmp_path, "openai") == (1, 3)
