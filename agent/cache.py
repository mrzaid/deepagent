"""Cassette cache for the agent's *network* side-effects (web_search, fetch_url).

The LLM client has its own cassette layer; this is the matching piece for the
tool calls. Together they make a full eval run reproducible offline: under
LLM_MODE=replay, no HTTP and no API calls happen at all, so the suite is
deterministic and free. Keyed by the call's inputs.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable

from . import config


def _path(kind: str, key: str):
    config.CASSETTES_DIR.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return config.CASSETTES_DIR / f"{kind}-{h}.json"


def cached(kind: str, key: str, producer: Callable[[], object]) -> object:
    """Return producer()'s value, recording/replaying it per LLM_MODE.

    live   -> call producer, return value
    record -> call producer, save value, return it
    replay -> return saved value (raise if missing); producer is never called
    """
    p = _path(kind, key)
    # record + replay both read an existing cassette first; record is WRITE-ONCE
    # so a repeated identical call returns the same value instead of clobbering it.
    if config.LLM_MODE in ("replay", "record") and p.exists():
        rec = json.loads(p.read_text(encoding="utf-8"))
        if "error" in rec:  # faithfully replay a recorded failure
            raise RuntimeError(rec["error"])
        return rec["value"]
    if config.LLM_MODE == "replay":
        raise RuntimeError(f"no {kind} cassette for this input (LLM_MODE=replay); record first")

    try:
        value = producer()
    except Exception as e:  # record failures too, so replay sees the same observation
        if config.LLM_MODE == "record":
            p.write_text(json.dumps({"kind": kind, "key": key, "error": str(e)}, indent=2),
                         encoding="utf-8")
        raise
    if config.LLM_MODE == "record":
        p.write_text(json.dumps({"kind": kind, "key": key, "value": value}, indent=2),
                     encoding="utf-8")
    return value
