"""Structured LLM outputs and the rulebook format."""

from pydantic import BaseModel, ConfigDict, Field


class Rule(BaseModel):
    id: str = ""
    title: str
    old_pattern: str
    new_pattern: str
    detection_hint: str = ""  # Python regex matched against source lines
    notes: str = ""
    source_url: str
    source_official: bool = False
    verified: bool = False
    confidence: float = 0.0
    learned_from_run: str | None = None


class Rulebook(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    package: str
    from_: str = Field(alias="from")
    to: str
    recipe_version: int = 1
    created_at: str = ""
    checked_at: str = ""
    official_pages: int = 0
    rules: list[Rule] = []


class RuleDrafts(BaseModel):
    rules: list[Rule]


class PlanFile(BaseModel):
    path: str
    rule_ids: list[str] = []
    risk: str = "low"
    notes: str = ""


class Plan(BaseModel):
    files: list[PlanFile] = []
    manual_review: list[str] = []
    summary: str = ""
