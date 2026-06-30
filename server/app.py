"""Minimal web UI for live observability.

POST /run starts the agent loop in a background thread and returns a run_id.
GET /events/{run_id} is a Server-Sent Events stream: it replays the run's trace
from disk, then follows live events from the tracer's in-process pub/sub. The
React + TypeScript SPA (built into static/ from web/) renders the plan, steps,
findings, and streamed report. Same trace the eval harness reads — observability
and eval unified.
"""
from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import loop
from agent.state import _new_run_id
from agent import tracer as tracer_mod
from agent.tracer import read_trace

app = FastAPI(title="deepagent")
_STATIC = Path(__file__).parent / "static"

# Serve the built SPA's hashed JS/CSS bundle. Guarded so the server still imports
# before the first `npm run build` (the committed build makes this present).
if (_STATIC / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(_STATIC / "assets")), name="assets")


class RunRequest(BaseModel):
    goal: str
    fault: str | None = None
    max_steps: int | None = None


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (_STATIC / "index.html").read_text(encoding="utf-8")


@app.post("/run")
def start_run(req: RunRequest) -> JSONResponse:
    run_id = _new_run_id()
    fault = {req.fault: True} if req.fault else None

    def _worker():
        try:
            loop.run(req.goal, run_id=run_id, fault=fault, max_steps=req.max_steps)
        except Exception as e:  # surface crashes into the trace stream
            try:
                from agent.tracer import Tracer
                from agent import config
                Tracer(run_id, config.RUNS_DIR / run_id).emit("error", {"where": "worker", "msg": str(e)})
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()
    return JSONResponse({"run_id": run_id})


@app.get("/events/{run_id}")
def events(run_id: str) -> StreamingResponse:
    # Subscribe BEFORE replaying history so no live event slips through the gap.
    q = tracer_mod.subscribe(run_id)

    def gen():
        sent = set()
        try:
            for ev in read_trace(run_id):  # replay any history already on disk
                sent.add(ev["seq"])
                yield _sse(ev)
            while True:
                try:
                    ev = q.get(timeout=15)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue
                if ev["seq"] in sent:
                    continue
                sent.add(ev["seq"])
                yield _sse(ev)
                if ev["type"] == "run_ended":
                    break
        finally:
            tracer_mod.unsubscribe(run_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _sse(ev: dict) -> str:
    return f"data: {json.dumps(ev)}\n\n"
