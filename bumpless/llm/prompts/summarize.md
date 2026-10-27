You read documentation for upgrading the Python package `{{package}}` from {{from}} to {{to}}.

List every breaking change or API rename/removal described in the page below that a developer must act on.
For each one write one line:
- OLD: <old usage, exact code> | NEW: <new usage, exact code> | NOTE: <what else changes>

Be precise about details a code migration gets wrong: required new arguments (e.g. a mode= keyword), changed
function signatures (what the function receives and must return), changed defaults (e.g. a field that used to be
optional becoming required), and renamed config keys. Put those details in NEW and NOTE.

Use only what the page says. Copy API names exactly. If the page describes no breaking changes, reply exactly: NONE

Page ({{url}}):
{{text}}
