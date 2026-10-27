from types import SimpleNamespace

from bumpless.llm.schemas import Rule
from bumpless.research.verify_sources import excerpt, mentioned, verify_rules


class FakeLLM:
    def __init__(self, supported: bool, quote: str = "", required: bool = True):
        self.supported, self.calls, self.quote, self.required = supported, 0, quote, required

    async def chat(self, task, messages, step="", schema=None, **kw):
        self.calls += 1
        return schema(supported=self.supported, quote=self.quote, required=self.required)


def ctx_with(pages: dict, llm) -> SimpleNamespace:
    return SimpleNamespace(package="pydantic", llm=llm, sources=SimpleNamespace(pages=pages),
                           tavily=None, progress=lambda *a, **k: None)


PAGE = "https://docs.pydantic.dev/latest/migration"
TEXT = "In Pydantic V2, orm_mode has been renamed to from_attributes in model_config (ConfigDict)."


def rule(**kw) -> Rule:
    base = dict(id="R001", title="orm_mode renamed", old_pattern="orm_mode = True",
                new_pattern="model_config = ConfigDict(from_attributes=True)", source_url=PAGE, source_official=True)
    return Rule(**(base | kw))


async def test_injected_fake_rule_is_unverified_without_an_llm_call():
    fake = rule(id="R999", title="frobnicate renamed", old_pattern="Model.frobnicate()",
                new_pattern="Model.defrobnicate()")
    llm = FakeLLM(supported=True)  # even a model that says "yes" cannot verify it
    await verify_rules(ctx_with({PAGE: TEXT}, llm), [fake])
    assert fake.verified is False and fake.confidence == 0.0
    assert llm.calls == 0


async def test_supported_rule_verified_and_rejected_when_model_says_no():
    good, bad = rule(), rule(id="R002")
    await verify_rules(ctx_with({PAGE: TEXT}, FakeLLM(True)), [good])
    await verify_rules(ctx_with({PAGE: TEXT}, FakeLLM(False)), [bad])
    assert good.verified and good.confidence == 1.0
    assert not bad.verified


def test_mentioned_and_excerpt():
    assert mentioned(rule(), TEXT) == ["orm_mode", "model_config", "ConfigDict", "from_attributes"]
    big = "x " * 50_000 + TEXT + " y" * 50_000
    ex = excerpt(big, ["orm_mode"])
    assert "orm_mode" in ex and len(ex) < 12_001


async def test_evidence_kept_only_when_the_quote_is_on_the_page():
    real, made_up = rule(), rule(id="R002")
    await verify_rules(ctx_with({PAGE: TEXT}, FakeLLM(True, "orm_mode has been  renamed to from_attributes")), [real])
    await verify_rules(ctx_with({PAGE: TEXT}, FakeLLM(True, "use from_attributes=True everywhere")), [made_up])
    assert real.evidence == "orm_mode has been  renamed to from_attributes"
    assert made_up.verified and made_up.evidence == ""


async def test_optional_new_style_is_not_applied():
    optional = rule(id="R009", title="filter_by() to where()")
    await verify_rules(ctx_with({PAGE: TEXT}, FakeLLM(True, required=False)), [optional])
    assert not optional.verified and "optional new style" in optional.notes
