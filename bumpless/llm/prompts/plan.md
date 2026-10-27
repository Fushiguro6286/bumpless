You plan the migration of a Python repository from `{{package}}` {{from}} to {{to}}.

Rulebook (verified from official sources):
{{rules}}

Static scan results (file -> rule ids matched, with line numbers):
{{scan}}

Files that import {{package}}, or import modules that do: {{importers}}

Decide the order to edit files (models/definitions before their users), which rules apply to each file,
a risk level, and short notes for the editor. Under manual_review list only concrete problems you can see that cannot be migrated automatically (usually none);
do not list generic reminders or things to double-check.
Reply with JSON only:
{"summary": "one sentence", "files": [{"path": "app/models.py", "rule_ids": ["R001"], "risk": "low|medium|high",
"notes": "what to watch for"}], "manual_review": ["..."]}
