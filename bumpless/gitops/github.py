"""Minimal GitHub REST helpers (httpx)."""

import re

import httpx

API = "https://api.github.com"


def parse_repo(url: str) -> tuple[str, str] | None:
    m = re.match(r"^(?:https://github\.com/|git@github\.com:)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", url)
    return (m.group(1), m.group(2)) if m else None


def _client(token: str) -> httpx.Client:
    return httpx.Client(base_url=API, timeout=30, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"})


def repo_info(token: str, owner: str, repo: str) -> dict:
    with _client(token) as c:
        r = c.get(f"/repos/{owner}/{repo}")
        r.raise_for_status()
        return r.json()


def can_push(token: str, owner: str, repo: str) -> bool:
    try:
        return bool(repo_info(token, owner, repo).get("permissions", {}).get("push"))
    except httpx.HTTPError:
        return False


def open_pr(token: str, owner: str, repo: str, head: str, base: str, title: str, body: str) -> dict:
    with _client(token) as c:
        r = c.post(f"/repos/{owner}/{repo}/pulls", json={"title": title, "head": head, "base": base, "body": body})
        r.raise_for_status()
        return r.json()


def comment(token: str, owner: str, repo: str, number: int, body: str) -> dict:
    with _client(token) as c:
        r = c.post(f"/repos/{owner}/{repo}/issues/{number}/comments", json={"body": body})
        r.raise_for_status()
        return r.json()
