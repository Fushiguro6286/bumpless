You build a migration rulebook for upgrading the Python package `{{package}}` from {{from}} to {{to}}.

Below are notes extracted from documentation pages. Each block starts with its SOURCE URL.
Write up to {{max_rules}} rules covering the breaking changes a typical codebase hits. Prioritize changes
touching these names, which the target codebase uses: {{usage}}

Reply with JSON only:
{"rules": [{
  "title": "short title",
  "old_pattern": "old code, e.g. class Config: orm_mode = True",
  "new_pattern": "new code, e.g. model_config = ConfigDict(from_attributes=True)",
  "detection_hint": "a Python regex that finds old usages in source lines, e.g. \borm_mode\s*=",
  "notes": "one or two sentences: behavior differences, gotchas",
  "source_url": "the SOURCE URL this rule came from, copied exactly"
}]}

Every rule must come from the notes and cite the SOURCE URL it came from. Do not invent rules. When several sources
describe the same change, cite the official migration guide or documentation rather than discussions or blogs.
Ignore notes about other products that merely share the name (plugins, frameworks or SDKs built on the package).

{{notes}}
