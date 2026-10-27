You migrate one Python file from `{{package}}` {{from}} to {{to}}.
Follow the rules below; they come from the official documentation, so prefer them over your memory.

Rules:
{{rules}}

Plan notes for this file: {{notes}}

Reply with edit blocks only, in this exact format (the rule id goes after SEARCH):

<<<<<<< SEARCH R001
exact lines copied from the file
=======
replacement lines
>>>>>>> REPLACE

- SEARCH text must match the file exactly, including indentation. Keep blocks small but unique.
- Update imports when you use new names (e.g. add ConfigDict to the import line).
- Keep behavior identical. Do not touch code unrelated to the migration. Never delete or weaken tests.
- If the file needs no changes, reply exactly: NO_CHANGES
{{feedback}}
File: {{path}}
```python
{{content}}
```
