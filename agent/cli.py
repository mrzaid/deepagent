"""Headless CLI:
  python -m agent run "<goal>"      # run a task (also used by the eval harness)
  python -m agent resume <run_id>   # continue an interrupted run
  python -m agent trace <run_id>    # render a run's trace as a readable timeline
"""
from __future__ import annotations

import argparse
import sys

from . import config
from .loop import run
from .tracer import read_trace


def _print_summary(state) -> None:
    print("\n" + "=" * 70)
    print(f"RUN {state.run_id}  |  done={state.done}  steps={state.steps}  "
          f"findings={len(state.findings)}  sources={len(state.fetched_urls())}")
    print("=" * 70)
    print(state.final_report or "(no report)")
    print("-" * 70)
    print(f"Artifacts: {state.run_dir}")
    print(f"  trace : {state.run_dir / 'trace.jsonl'}")
    print(f"  state : {state.run_dir / 'state.json'}")


def _render_trace(run_id: str, verbose: bool = False) -> int:
    """WI-7: render trace.jsonl as a readable step -> action -> observation timeline."""
    events = read_trace(run_id)
    if not events:
        print(f"no trace for run '{run_id}'")
        return 1
    print(f"=== trace for {run_id} ({len(events)} events) ===")
    for e in events:
        t, d = e["type"], e.get("data", {})
        if t == "run_started":
            print(f"\nGOAL: {d.get('goal','')}  (budget {d.get('step_budget')} steps)")
        elif t == "plan_created" or t == "plan_revised":
            print(f"  · plan {'set' if t=='plan_created' else 'revised'} "
                  f"({len(d.get('plan', []))} steps)")
        elif t == "step_started":
            print(f"\n[step {d.get('step')}]")
        elif t == "tool_call":
            args = ", ".join(f"{k}={str(v)[:60]}" for k, v in (d.get("args") or {}).items())
            print(f"  -> {d.get('tool')}({args})")
        elif t == "observation":
            mark = "ok" if d.get("ok") else "ERR"
            obs = (d.get("observation") or "").replace("\n", " ")
            print(f"     [{mark}] {obs[: (600 if verbose else 140)]}")
        elif t == "finding_recorded":
            print(f"  ✓ finding [{d.get('index')}] <- {d.get('source_url','')}")
        elif t == "note_written":
            print(f"  📝 note '{d.get('name')}' ({d.get('chars')} chars)")
        elif t == "nudge":
            print(f"  ↻ nudge ({d.get('kind')})")
        elif t == "compaction":
            print(f"  ⊟ compaction (digested {d.get('findings_digested')} findings)")
        elif t in ("verify_started", "verify_result", "verify_failed", "verify_exhausted"):
            print(f"  ⚖ {t} {d if verbose else {k: d[k] for k in ('n_issues','retry') if k in d}}")
        elif t == "steer_injected":
            print(f"  ⇄ operator steer injected ({d.get('chars')} chars)")
        elif t == "budget_event":
            print(f"  ⏱ budget hit: {d.get('kind')}")
        elif t == "force_synthesis":
            print(f"  ⚙ force-synthesis ({d.get('findings')} findings)")
        elif t == "finished":
            print(f"  ★ finished ({d.get('num_findings')} findings, "
                  f"{len(d.get('sources_cited', []))} sources cited)")
        elif t == "run_ended":
            print(f"\n=== run_ended: status={d.get('status')} done={d.get('done')} "
                  f"steps={d.get('steps')} findings={d.get('findings')} "
                  f"nudges={d.get('nudges')} verify_retries={d.get('verify_retries')} "
                  f"compactions={d.get('compactions')} ===")
        elif t == "error":
            print(f"  ✗ error: {d}")
    return 0


def main(argv=None) -> int:
    # Windows consoles default to cp1252; our trace/report output is UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="agent", description="deepagent research assistant")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run a new research task")
    p_run.add_argument("goal", help="the research question / goal")
    p_run.add_argument("--run-id", default=None, help="fixed run id (optional)")
    p_run.add_argument("--max-steps", type=int, default=None, help="override step budget")
    p_run.add_argument("--fault", default=None,
                       help="inject a fault, e.g. 'fail_first_fetch' (for eval/testing)")

    p_res = sub.add_parser("resume", help="resume an interrupted run")
    p_res.add_argument("run_id", help="the run id to resume")
    p_res.add_argument("--max-steps", type=int, default=None)

    p_tr = sub.add_parser("trace", help="render a run's trace as a readable timeline")
    p_tr.add_argument("run_id", help="the run id to render")
    p_tr.add_argument("--verbose", action="store_true", help="show full observations")

    args = parser.parse_args(argv)

    if args.cmd == "trace":
        return _render_trace(args.run_id, verbose=args.verbose)
    if args.cmd == "run":
        fault = {args.fault: True} if args.fault else None
        state = run(args.goal, run_id=args.run_id, fault=fault, max_steps=args.max_steps)
    else:  # resume
        state = run(goal="", run_id=args.run_id, resume=True, max_steps=args.max_steps)

    _print_summary(state)
    return 0 if state.done else 1


if __name__ == "__main__":
    raise SystemExit(main())
