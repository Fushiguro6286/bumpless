You are repairing a migration of a Python repository from `{{package}}` {{from}} to {{to}}.
The tests below fail after the migration. Find the root cause and fix it.

Rulebook (verified from official sources):
{{rules}}

Changes made so far (git diff):
```diff
{{diff}}
```

Failing tests and output:
```
{{failures}}
```

Relevant files:
{{files}}

Fix every failure you can see in one reply, not just the first one. Reply in this format:
DIAGNOSIS: <one or two sentences>
LOOKUP: <if the error is NOT explained by the rulebook, the exact error message to search the web for; else NONE>

Then edit blocks, each preceded by the file path on its own line:
path/to/file.py
<<<<<<< SEARCH RULE_ID
exact lines from the current file
=======
replacement lines
>>>>>>> REPLACE

Failures in tests/_bumpless/test_characterization.py mean observable behavior changed compared with the old
version (the test name says which observation); fix the code to restore the old behavior and never edit
tests/_bumpless. If a difference is an unavoidable, documented change of the new version, say so in DIAGNOSIS
and make no edit for it.
Replace RULE_ID with the id of the rule that block follows (each block its own rule), LEARNED if it follows
the LOOKUP result, or NONE. Never delete tests, add skip/xfail
markers, or weaken assertions. Fix the code, not the tests (tests may only change to use the new API).
