import math
from typing import List

from app import llm


def summarize(text: str, max_words: int = 30) -> str:
    return llm.chat(f"Summarize in at most {max_words} words:\n{text}").strip()


def similarity(a: str, b: str) -> float:
    va, vb = llm.embed([a, b])
    dot = sum(x * y for x, y in zip(va, vb))
    return round(dot / (math.sqrt(sum(x * x for x in va)) * math.sqrt(sum(y * y for y in vb))), 4)


def bullet_points(items: List[str]) -> List[str]:
    out = []
    for item in items:
        try:
            out.append("- " + summarize(item, 10))
        except llm.RateLimited:
            out.append("- (skipped: rate limited)")
    return out
