# openai_app (fixture)

A small summarization helper written against the openai Python SDK 0.28 (module-level `openai.ChatCompletion`,
`openai.error.*`, dict-style responses). Tests run against a local fake OpenAI-compatible server
(`tests/conftest.py`), so they need no network and no API key.
