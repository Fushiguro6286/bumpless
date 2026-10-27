from types import SimpleNamespace

from bumpless.llm.schemas import Rule, Rulebook
from bumpless.recipes import store
from bumpless.research import freshness


def rb(**kw) -> Rulebook:
    rules = [Rule(id="R001", title="a", old_pattern="x.dict()", new_pattern="x.model_dump()", source_url="u",
                  verified=True)]
    return Rulebook(**({"package": "pydantic", "from": "1", "to": "2", "rules": rules,
                        "checked_at": "2026-10-27T00:00:00+00:00"} | kw))


def test_save_load_and_merge_learned(tmp_path):
    store.save(rb(), "run1", tmp_path)
    assert store.load("pydantic", "1", "2", tmp_path).recipe_version == 1
    second = rb()
    second.rules.append(Rule(title="b", old_pattern="parse_obj", new_pattern="model_validate", source_url="u",
                             verified=True, learned_from_run="run2"))
    second.rules.append(Rule(title="dup", old_pattern="x.dict()", new_pattern="x.model_dump()", source_url="u",
                             learned_from_run="run2"))
    recipe, changed = store.save(second, "run2", tmp_path)
    assert changed and recipe.recipe_version == 2
    assert [r.id for r in recipe.rules] == ["R001", "R002"]  # duplicate pattern not re-added
    recipe, changed = store.save(rb(), "run3", tmp_path)
    assert not changed and recipe.recipe_version == 2


async def _get(monkeypatch, tmp_path, checked_at):
    store.save(rb(checked_at=checked_at), "seed", tmp_path)
    monkeypatch.setattr(store, "RECIPES_DIR", tmp_path)
    calls = []

    async def fake_official(ctx):
        return SimpleNamespace(pages={})

    async def fake_refresh(ctx, recipe, usage):
        calls.append(recipe.checked_at)
        return 0

    monkeypatch.setattr(freshness, "official", fake_official)
    monkeypatch.setattr(freshness, "refresh", fake_refresh)
    ctx = SimpleNamespace(package="pydantic", from_major="1", to_major="2", emit=lambda *a, **k: None,
                          progress=lambda *a, **k: None)
    recipe, reused = await freshness.get_rulebook(ctx, [])
    return reused, calls


async def test_fresh_recipe_is_reused_without_freshness_check(monkeypatch, tmp_path):
    from datetime import UTC, datetime
    reused, calls = await _get(monkeypatch, tmp_path, datetime.now(UTC).isoformat())
    assert reused and calls == []


async def test_backdated_recipe_triggers_freshness_check(monkeypatch, tmp_path):
    reused, calls = await _get(monkeypatch, tmp_path, "2025-01-01T00:00:00+00:00")
    assert reused and calls == ["2025-01-01T00:00:00+00:00"]
