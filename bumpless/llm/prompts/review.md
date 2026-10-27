You are the final reviewer of an automated migration of a Python repository from `{{package}}` {{from}} to {{to}}.

Rulebook used (each rule verified against its source):
{{rules}}

Full diff:
```diff
{{diff}}
```

Check: does every change follow a rule or fix a real incompatibility? Is behavior preserved? Were any tests weakened,
deleted or skipped? Were unrelated files or lines touched? Anything risky a human should look at?
Reply with JSON only:
{"approve": true or false, "summary": "one sentence", "concerns": [{"path": "file.py", "issue": "..."}]}
Only list real concerns; an empty list is fine.
