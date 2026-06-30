"""Tracing = observability AND the eval input, from one artifact.

Every meaningful thing the agent does is emitted as a structured event. Events
are (a) appended to runs/<run_id>/trace.jsonl (durable, replayable, what the
eval harness reads) and (b) published to any live subscribers (the web UI's SSE
stream). Keeping these unified means the UI shows exactly what the eval scores.
"""
from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path
from typing import Optional

from . import config

# run_id -> list of subscriber queues (live SSE listeners)
_subscribers: dict[str, list[queue.Queue]] = {}
_lock = threading.Lock()


def subscribe(run_id: str) -> queue.Queue:
    q: queue.Queue = queue.Queue()
    with _lock:
        _subscribers.setdefault(run_id, []).append(q)
    return q


def unsubscribe(run_id: str, q: queue.Queue) -> None:
    with _lock:
        subs = _subscribers.get(run_id)
        if subs and q in subs:
            subs.remove(q)


def _publish(run_id: str, event: dict) -> None:
    with _lock:
        subs = list(_subscribers.get(run_id, []))
    for q in subs:
        q.put(event)


class Tracer:
    """One tracer per run. Thread-safe append + publish."""

    def __init__(self, run_id: str, run_dir: Path):
        self.run_id = run_id
        self.path = run_dir / "trace.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        self._wlock = threading.Lock()

    def emit(self, event_type: str, data: Optional[dict] = None) -> dict:
        with self._wlock:
            self._seq += 1
            event = {
                "seq": self._seq,
                "ts": time.time(),
                "type": event_type,
                "data": data or {},
            }
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        _publish(self.run_id, event)
        return event


def read_trace(run_id: str) -> list[dict]:
    """Read a run's full trace from disk (used to replay history into a late
    SSE subscriber and by the eval harness)."""
    path = config.RUNS_DIR / run_id / "trace.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events
