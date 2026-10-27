import os
from typing import Dict, List

import openai

openai.api_key = os.environ.get("OPENAI_API_KEY", "sk-test")
openai.api_base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")

MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"


class LLMError(Exception):
    pass


class RateLimited(LLMError):
    pass


def chat(prompt: str, system: str = "You are a helpful assistant.", temperature: float = 0.0) -> str:
    try:
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            temperature=temperature,
        )
    except openai.error.RateLimitError as e:
        raise RateLimited(str(e)) from e
    except openai.error.OpenAIError as e:
        raise LLMError(str(e)) from e
    return resp["choices"][0]["message"]["content"]


def chat_usage(prompt: str) -> Dict[str, int]:
    resp = openai.ChatCompletion.create(model=MODEL, messages=[{"role": "user", "content": prompt}])
    return {"prompt": resp["usage"]["prompt_tokens"], "completion": resp["usage"]["completion_tokens"]}


def embed(texts: List[str]) -> List[List[float]]:
    resp = openai.Embedding.create(model=EMBED_MODEL, input=texts)
    return [item["embedding"] for item in resp["data"]]
