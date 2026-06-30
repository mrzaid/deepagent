"""web_search tool: Tavily HTTP search. Registers result URLs as (unfetched)
sources so the agent knows what exists before deciding what to read."""
from __future__ import annotations

import requests

from .. import config
from ..cache import cached


def _tavily(query: str, max_results: int) -> list[dict]:
    def _produce():
        if not config.TAVILY_API_KEY:
            raise RuntimeError("TAVILY_API_KEY is not set")
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": config.TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
            timeout=config.FETCH_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    return cached("search", f"{query}|{max_results}", _produce)


def web_search(args: dict, state, tracer) -> str:
    query = (args.get("query") or "").strip()
    if not query:
        raise RuntimeError("web_search requires a non-empty 'query'")
    # eval fault-injection: simulate a topic with no usable sources, to test that
    # the agent reports the gap instead of fabricating a false-success answer.
    if state.fault.get("empty_results"):
        return f'No results for "{query}". Try a different query.'
    results = _tavily(query, config.SEARCH_RESULTS)
    if not results:
        return f'No results for "{query}". Try a different query.'

    lines = []
    for i, r in enumerate(results, 1):
        url = r.get("url", "")
        title = r.get("title", "")
        state.add_source(url, title)  # known, not yet fetched
        snippet = (r.get("content") or "").strip().replace("\n", " ")[:300]
        lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
    return f'{len(results)} results for "{query}":\n' + "\n".join(lines)
