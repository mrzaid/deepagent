"""The agent control loop: plan -> act -> observe -> adapt.

This is the core deliverable. A single explicit loop where, each turn, the model
sees the reconstructed (and compacted) state and freely chooses ONE next tool.
Robustness is designed in:

- step + token + wall-clock budgets bound every run (WI-3);
- tool failures become observations the model reacts to (never crash);
- stall / search-without-fetch / windowed-repeat nudges break loops (WI-9);
- context compaction keeps the rebuilt prompt bounded as findings grow (WI-2);
- a fresh-context critic must pass the draft before the run may complete (WI-1);
- operator controls (AGENT_STOP / STEER.md / SIGINT) allow kill + steer (WI-8);
- a reorientation turn fights amnesia on resume (WI-6);
- a force-synthesis fallback guarantees a grounded report if the budget runs out.
"""
from __future__ import annotations

import json
import signal
import time
from collections import deque
from typing import Optional

from . import config, llm
from .compaction import maybe_compact
from .context import build_context
from .prompts import REORIENT, SYNTHESIS
from .state import ResearchState, Turn
from .tools import dispatch, schemas_for
from .tracer import Tracer
from .verifier import verify

# set by a SIGINT handler (Ctrl-C) when running in the main thread; the AGENT_STOP
# file is the cross-thread equivalent used by the web server.
_ABORT = {"flag": False}


def _install_sigint() -> None:
    try:
        signal.signal(signal.SIGINT, lambda *_: _ABORT.__setitem__("flag", True))
    except (ValueError, RuntimeError):
        pass  # not in the main thread (e.g. web server) -> rely on AGENT_STOP file


def run(
    goal: str,
    run_id: Optional[str] = None,
    fault: Optional[dict] = None,
    resume: bool = False,
    max_steps: Optional[int] = None,
) -> ResearchState:
    _ABORT["flag"] = False
    _install_sigint()

    if resume and run_id:
        state = ResearchState.load(run_id)
        state.run_dir.mkdir(parents=True, exist_ok=True)
        state.pages_dir.mkdir(parents=True, exist_ok=True)
    else:
        state = ResearchState.new(goal, run_id=run_id, fault=fault)

    tracer = Tracer(state.run_id, state.run_dir)
    tool_schemas = schemas_for(config.SKILLS_ENABLED)
    step_budget = max_steps or config.STEP_BUDGET
    # wall-clock deadline is recomputed each run() (NOT persisted) so a resumed run
    # gets a fresh window rather than inheriting a stale absolute time.
    deadline = time.monotonic() + config.WALL_CLOCK_BUDGET if config.WALL_CLOCK_BUDGET > 0 else None

    if state.steps == 0:
        tracer.emit("run_started", {"goal": goal, "run_id": state.run_id, "step_budget": step_budget})

    # WI-6: on resume, reorient before taking any new action.
    pending_note = None
    if resume and state.steps > 0 and not state.done:
        pending_note = _reorient(state, tracer)

    recent_sigs: deque[str] = deque(maxlen=8)
    end_reason = None

    while not state.done:
        # ---- termination guards (WI-3) ---------------------------------
        if state.steps >= step_budget:
            end_reason = "step_budget"; break
        if state.tokens_used >= config.TOKEN_BUDGET:
            end_reason = "token_budget"; break
        if deadline is not None and time.monotonic() >= deadline:
            end_reason = "wall_clock"; break
        # ---- operator kill switch (WI-8) -------------------------------
        if _ABORT["flag"] or (state.run_dir / "AGENT_STOP").exists():
            return _abort(state, tracer)

        # ---- keep the rebuilt prompt bounded (WI-2) --------------------
        maybe_compact(state, tracer)

        # ---- choose this turn's steering note --------------------------
        note = pending_note
        pending_note = None
        steer = _read_steer(state, tracer)
        if steer:
            note = (note + "\n\n" if note else "") + f"OPERATOR STEER: {steer}"
        if note is None:
            note = _nudge(state, tracer)

        state.steps += 1
        tracer.emit("step_started", {"step": state.steps})
        messages = build_context(state, note=note, step_budget=step_budget)

        # ---- ask the model for the next action -------------------------
        try:
            resp = llm.chat(messages, tools=tool_schemas, tool_choice="required",
                            on_report_delta=lambda t: tracer.emit("report_delta", {"text": t}))
        except Exception as e:  # noqa: BLE001
            tracer.emit("error", {"where": "llm", "msg": str(e)})
            break
        state.tokens_used += resp.usage.get("total_tokens", 0)

        if not resp.tool_calls:
            state.stall_counter += 1
            tracer.emit("observation", {"step": state.steps, "tool": None, "ok": False,
                                        "observation": "model returned no tool call"})
            state.persist()
            continue

        tc = resp.tool_calls[0]  # one action per step keeps the trace clean
        sig = f"{tc.name}:{json.dumps(tc.args, sort_keys=True)}"
        tracer.emit("tool_call", {"step": state.steps, "tool": tc.name, "args": tc.args})

        pre_findings = len(state.findings)
        pre_fetched = len(state.fetched_urls())
        try:
            obs = dispatch(tc.name, tc.args, state, tracer)
            ok = True
        except Exception as e:  # noqa: BLE001 - failures are data
            obs = f"ERROR: {e}"
            ok = False

        tracer.emit("observation", {"step": state.steps, "tool": tc.name, "ok": ok,
                                    "observation": obs[:1500]})
        state.push_turn(Turn(step=state.steps, tool=tc.name, args=tc.args, observation=obs[:800]))

        # ---- fresh-context critic gates completion (WI-1) --------------
        if ok and tc.name == "finish" and state.done:
            issues = verify(state, tracer)
            if issues and state.verify_retries < config.MAX_VERIFY_RETRIES:
                state.verify_retries += 1
                state.done = False
                crit = "; ".join(i.get("problem", "") for i in issues)[:500]
                pending_note = ("A fresh-context reviewer REJECTED your draft report. Fix these "
                                f"issues and then call finish again: {crit}")
                tracer.emit("verify_failed", {"retry": state.verify_retries, "n_issues": len(issues)})
                state.persist()
                continue
            if issues:  # retries exhausted — accept but record that it was unverified
                tracer.emit("verify_exhausted", {"n_issues": len(issues)})

        # ---- stall / repeat accounting (WI-9) --------------------------
        progressed = ok and (
            len(state.findings) > pre_findings
            or len(state.fetched_urls()) > pre_fetched
            or tc.name in ("update_plan", "finish")
        )
        recent_sigs.append(sig)
        windowed_repeats = recent_sigs.count(sig)
        if sig == state.last_action_sig or not progressed or windowed_repeats >= config.REPEAT_LIMIT:
            state.stall_counter += 1
        else:
            state.stall_counter = 0
        state.last_action_sig = sig

        if ok and tc.name == "web_search":
            state.searches_since_fetch += 1
        elif ok and tc.name == "fetch_url":
            state.searches_since_fetch = 0

        state.persist()

    # ---- fallback: never end a run without a grounded report -----------
    if not state.done:
        if end_reason:
            tracer.emit("budget_event", {"kind": end_reason, "steps": state.steps,
                                         "tokens_used": state.tokens_used})
        _force_synthesis(state, tracer)

    state.persist()
    tracer.emit("run_ended", {"status": "completed", "done": state.done, "steps": state.steps,
                              "findings": len(state.findings),
                              "sources_fetched": len(state.fetched_urls()),
                              "nudges": state.nudges, "verify_retries": state.verify_retries,
                              "compactions": state.compactions})
    return state


# --- steering / control helpers -----------------------------------------
def _abort(state: ResearchState, tracer: Tracer) -> ResearchState:
    """Halt cleanly on AGENT_STOP / SIGINT: persist and emit an aborted run_ended.
    The run can be continued later with `agent resume`."""
    stop_file = state.run_dir / "AGENT_STOP"
    if stop_file.exists():
        try:
            stop_file.unlink()
        except OSError:
            pass
    state.persist()
    tracer.emit("run_ended", {"status": "aborted", "done": state.done, "steps": state.steps,
                              "findings": len(state.findings),
                              "sources_fetched": len(state.fetched_urls())})
    return state


def _read_steer(state: ResearchState, tracer: Tracer) -> Optional[str]:
    """One-time operator steering: if runs/<id>/STEER.md exists, inject it once."""
    steer_file = state.run_dir / "STEER.md"
    if not steer_file.exists():
        return None
    try:
        content = steer_file.read_text(encoding="utf-8").strip()
        steer_file.unlink()
    except OSError:
        return None
    if not content:
        return None
    tracer.emit("steer_injected", {"chars": len(content)})
    return content


def _nudge(state: ResearchState, tracer: Tracer) -> Optional[str]:
    """Most-specific nudge first: over-searching, then a general stall."""
    if state.searches_since_fetch >= config.SEARCH_WITHOUT_FETCH_LIMIT:
        state.searches_since_fetch = 0
        state.nudges += 1
        tracer.emit("nudge", {"step": state.steps + 1, "kind": "search_without_fetch"})
        return (f"You have run {config.SEARCH_WITHOUT_FETCH_LIMIT}+ searches in a row without "
                "reading a source. Stop searching and fetch_url the most promising result now — "
                "snippets are not evidence.")
    if state.stall_counter >= config.STALL_LIMIT:
        state.stall_counter = 0
        state.nudges += 1
        tracer.emit("nudge", {"step": state.steps + 1, "kind": "stall"})
        return ("You appear to be stuck (repeating actions or not gathering new evidence). "
                "Change approach: try a different query, fetch a different source, or call "
                "finish if you have enough findings.")
    return None


def _reorient(state: ResearchState, tracer: Tracer) -> str:
    """WI-6: a short orientation turn after resume so the model re-grounds in the
    current state instead of acting amnesiacally."""
    plan = "\n".join(f"- [{p.status}] {p.text}" for p in state.plan) or "(no plan)"
    view = (f"GOAL: {state.goal}\nPLAN:\n{plan}\n"
            f"FINDINGS SO FAR: {len(state.findings)}\n"
            f"SOURCES FETCHED: {len(state.fetched_urls())}\n"
            f"STEP: {state.steps}")
    try:
        resp = llm.simple(REORIENT, view, model=config.SUMMARY_MODEL)
        state.tokens_used += resp.usage.get("total_tokens", 0)
        text = (resp.content or "").strip()
    except Exception:  # noqa: BLE001
        text = (f"Resuming at step {state.steps} with {len(state.findings)} findings and "
                f"{len(state.fetched_urls())} sources. Continue the plan from the first "
                "unfinished step.")
    tracer.emit("reoriented", {"text": text})
    return f"You are resuming an interrupted run. Orientation: {text}"


def _force_synthesis(state: ResearchState, tracer: Tracer) -> None:
    """Compose a final report directly from recorded findings when the budget
    runs out. Findings are grounded by construction (their URLs were fetched),
    so the resulting report is grounded too. The critic still runs once (no retry)."""
    tracer.emit("force_synthesis", {"reason": "budget_exhausted",
                                     "findings": len(state.findings)})

    if not state.findings:
        state.final_report = (
            f"# {state.goal}\n\n"
            "The agent was unable to gather sufficient grounded evidence within its "
            "budget to answer this question. No verified findings were recorded."
        )
        state.done = True
        tracer.emit("finished", {"report": state.final_report, "sources_cited": [],
                                 "num_findings": 0})
        return

    findings_block = "\n".join(
        f"- {f.claim} | source: {f.source_url}" + (f' | quote: "{f.quote}"' if f.quote else "")
        for f in state.findings
    )
    user = f"GOAL: {state.goal}\n\nFINDINGS (use only these):\n{findings_block}"
    try:
        resp = llm.simple(SYNTHESIS, user, model=config.AGENT_MODEL,
                          on_report_delta=lambda t: tracer.emit("report_delta", {"text": t}))
        report = (resp.content or "").strip()
        state.tokens_used += resp.usage.get("total_tokens", 0)
    except Exception:  # noqa: BLE001
        srcs = sorted({f.source_url for f in state.findings})
        body = "\n".join(f"- {f.claim} [{srcs.index(f.source_url) + 1}]" for f in state.findings)
        sources = "\n".join(f"[{i + 1}] {u}" for i, u in enumerate(srcs))
        report = f"# {state.goal}\n\n{body}\n\n## Sources\n{sources}"

    state.final_report = report
    state.done = True
    # critic runs once on the forced report too (no retry — budget is already spent)
    verify(state, tracer)
    cited = sorted({f.source_url for f in state.findings})
    tracer.emit("finished", {"report": report, "sources_cited": cited,
                             "num_findings": len(state.findings)})
