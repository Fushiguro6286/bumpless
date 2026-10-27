import os

import openai

openai.api_key = os.environ.get("OPENAI_API_KEY", "sk-test")
openai.api_base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")


class ModerationUnavailable(Exception):
    pass


def flagged(text: str) -> bool:
    try:
        resp = openai.Moderation.create(input=text)
    except openai.error.AuthenticationError as e:
        raise ModerationUnavailable("bad key") from e
    except openai.error.APIConnectionError as e:
        raise ModerationUnavailable("offline") from e
    return resp["results"][0]["flagged"]


def categories(text: str) -> list:
    resp = openai.Moderation.create(input=text)
    cats = resp["results"][0]["categories"]
    return sorted(k for k, v in cats.items() if v)


def suggest_reply(comment: str, max_tokens: int = 20) -> str:
    resp = openai.Completion.create(model="gpt-3.5-turbo-instruct", prompt=f"Reply politely to: {comment}",
                                    max_tokens=max_tokens, temperature=0, request_timeout=5)
    return resp["choices"][0]["text"].strip()
