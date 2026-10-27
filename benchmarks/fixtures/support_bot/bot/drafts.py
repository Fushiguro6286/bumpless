import os

import openai

from bot.models import Ticket

openai.api_key = os.environ.get("OPENAI_API_KEY", "sk-test")
openai.api_base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")


def draft_reply(t: Ticket) -> str:
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You write short, kind support replies."},
                  {"role": "user", "content": f"{t.subject}\n{t.body}"}],
    )
    return resp["choices"][0]["message"]["content"].strip()


def safe_draft(t: Ticket) -> str:
    try:
        return draft_reply(t)
    except openai.error.OpenAIError:
        return "A teammate will get back to you shortly."
