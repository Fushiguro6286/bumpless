Does the documentation page below support this migration rule for `{{package}}`?

Rule: {{title}}
Old API: {{old_pattern}}
New API: {{new_pattern}}

First decide whether the page is about the `{{package}}` library itself (not a different product that shares
the name, e.g. a framework, plugin or SDK built on top of it). Then decide whether it explicitly describes this
change (mentions the old and/or the new API in this context). Finally decide whether the change is required:
true if the page says the old usage is removed, raises, behaves differently or is deprecated in version {{to}};
false if the new API is only an optional or recommended alternative and the old usage keeps working (for example
"legacy, still supported" or "new style, the old style remains available"). Reply with JSON only:
{"about_package": true or false, "supported": true or false, "required": true or false, "quote": "an exact quote from the page that shows it, preferably including the new code; or empty"}

Page ({{url}}):
{{text}}
