"""PyPI JSON API helpers."""

from urllib.parse import urlparse

import httpx


async def project_info(package: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"https://pypi.org/pypi/{package}/json")
        r.raise_for_status()
        return r.json()["info"]


def official_sources(info: dict) -> tuple[set[str], list[str]]:
    """(docs domains, github repo URL prefixes) declared by the package itself."""
    urls = [*(info.get("project_urls") or {}).values(), info.get("home_page") or ""]
    domains, repos = set(), []
    for u in urls:
        p = urlparse(u)
        if not p.netloc:
            continue
        if p.netloc == "github.com":
            parts = p.path.strip("/").split("/")
            if len(parts) >= 2:
                repos.append(f"https://github.com/{parts[0]}/{parts[1]}".lower())
        else:
            domains.add(p.netloc.lower())
    return domains, sorted(set(repos))


def is_official(url: str, domains: set[str], repos: list[str]) -> bool:
    p = urlparse(url)
    return p.netloc.lower() in domains or any(url.lower().startswith(r) for r in repos)
