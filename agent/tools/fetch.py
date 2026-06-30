"""fetch_url tool: download a page, extract readable text, store the FULL text
on disk (out of context), and return only a short excerpt + an LLM summary.

This is where the context-control strategy pays off: large page bodies never
enter the rolling prompt. The model gets a summary + excerpt; the full text is
available on disk for audit but not for token spend.
"""
from __future__ import annotations

import hashlib
import re

import requests

from .. import config, llm
from ..cache import cached

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; deepagent/0.1; research assistant)"}
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = _TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract(html: str) -> tuple[str, str]:
    """Return (title, text). Prefer trafilatura, fall back to naive strip."""
    title, text = "", ""
    try:
        import trafilatura

        text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
        meta = trafilatura.extract_metadata(html)
        if meta and meta.title:
            title = meta.title
    except Exception:
        text = ""
    if not text:
        text = _strip_html(html)
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.S | re.I)
        if m:
            title = _TAG_RE.sub(" ", m.group(1)).strip()
    return title, text


def _summarise(goal: str, url: str, text: str) -> str:
    snippet = text[: config.PAGE_MAX_CHARS]
    try:
        r = llm.simple(
            system="You summarise web pages for a research agent. Be factual and concise (3-4 sentences). Focus on information relevant to the stated goal.",
            user=f"Research goal: {goal}\nURL: {url}\n\nPage text:\n{snippet}\n\nSummary:",
            model=config.SUMMARY_MODEL,
        )
        return (r.content or "").strip()
    except Exception:
        return text[:400].strip()


def _download_and_extract(url: str):
    """Download + extract readable text, cached for offline replay.
    Returns [title, text]."""
    def _produce():
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=config.FETCH_TIMEOUT)
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"failed to fetch {url}: {e}")
        title, text = _extract(resp.text)
        if not text:
            raise RuntimeError(f"could not extract readable text from {url}")
        return [title, text[: config.PAGE_MAX_CHARS]]

    return cached("fetch", url, _produce)


def fetch_url(args: dict, state, tracer) -> str:
    url = (args.get("url") or "").strip()
    if not url:
        raise RuntimeError("fetch_url requires a 'url'")

    # eval fault-injection: force the first fetch to fail to test recovery
    if state.fault.get("fail_first_fetch") and not state.fault.get("_fetch_failed_once"):
        state.fault["_fetch_failed_once"] = True
        raise RuntimeError(f"network error fetching {url} (injected fault)")

    title, text = _download_and_extract(url)

    # store full text on disk, out of context
    h = hashlib.sha256(url.encode()).hexdigest()[:12]
    page_file = f"pages/{h}.txt"
    (state.pages_dir / f"{h}.txt").write_text(text, encoding="utf-8")

    summary = _summarise(state.goal, url, text)

    src = state.add_source(url, title)
    src.fetched = True
    src.summary = summary
    src.page_file = page_file

    excerpt = text[: config.PAGE_EXCERPT_CHARS]
    return (
        f"Fetched: {url}\nTitle: {title or '(none)'}\n"
        f"Summary: {summary}\n\nExcerpt:\n{excerpt}"
    )
