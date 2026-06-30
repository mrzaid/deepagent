"""Eval runner + scorecard.

Runs the agent on each task (headless), then scores each finished run with the
deterministic checks and the LLM judge. Prints a scorecard and writes the full
results JSON to eval/results/. Under LLM_MODE=replay the whole suite runs
offline and deterministically from recorded cassettes.

Usage:
  python -m eval run                 # all tasks, with judge
  python -m eval run --task rust-vs-go
  python -m eval run --no-judge --max-steps 12
  python -m eval list
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time

import collections

from agent import config, loop
from agent.tracer import read_trace
from . import checks as checks_mod
from . import judge as judge_mod
from .tasks import TASKS, by_id


def _metrics(trace, state) -> dict:
    """Trajectory metrics derived from the trace — the 'how it got there' signal
    that complements the pass/fail checks and the answer-quality judge."""
    obs = [e for e in trace if e["type"] == "observation"]
    errors = [e for e in obs if not e["data"].get("ok", True)]
    nudges = collections.Counter(e["data"].get("kind", "?") for e in trace if e["type"] == "nudge")
    return {
        "tool_calls": sum(1 for e in trace if e["type"] == "tool_call"),
        "tool_error_rate": round(len(errors) / len(obs), 3) if obs else 0.0,
        "replans": sum(1 for e in trace if e["type"] == "plan_revised"),
        "nudges_by_kind": dict(nudges),
        "verify_failed": sum(1 for e in trace if e["type"] == "verify_failed"),
        "verify_retries": state.verify_retries,
        "compactions": state.compactions,
        "notes_written": sum(1 for e in trace if e["type"] == "note_written"),
    }


def run_task(task, max_steps=None, do_judge=True) -> dict:
    run_id = f"eval-{task.id}"
    # always start from a clean run dir so checks see only this attempt
    shutil.rmtree(config.RUNS_DIR / run_id, ignore_errors=True)

    fault = {task.fault: True} if task.fault else None
    t0 = time.time()
    # skill tasks need the skill tools exposed; toggle SKILLS_ENABLED around the run
    # (research tasks keep it off, so their cassettes stay byte-identical).
    prev_skills = config.SKILLS_ENABLED
    config.SKILLS_ENABLED = bool(task.skill)
    try:
        state = loop.run(task.goal, run_id=run_id, fault=fault, max_steps=max_steps)
    finally:
        config.SKILLS_ENABLED = prev_skills
    elapsed = round(time.time() - t0, 1)
    trace = read_trace(run_id)

    check_results = checks_mod.run_checks(task, state, trace)
    passed = sum(1 for _, ok, _ in check_results if ok)

    result = {
        "id": task.id,
        "goal": task.goal,
        "fault": task.fault,
        "skill": task.skill,
        "done": state.done,
        "steps": state.steps,
        "findings": len(state.findings),
        "sources_fetched": len(state.fetched_urls()),
        "nudges": state.nudges,
        "elapsed_s": elapsed,
        "metrics": _metrics(trace, state),
        "checks": [{"name": n, "passed": ok, "detail": d} for n, ok, d in check_results],
        "checks_passed": passed,
        "checks_total": len(check_results),
        "judge": None,
    }
    # the judge rubric is research-oriented (grounding by cited sources); skip it for
    # skill/legal tasks, where the deterministic skill checks + critic are the measure.
    if do_judge and not task.skill:
        result["judge"] = judge_mod.judge(task.goal, state.final_report, state.findings)
    return result


def _print_scorecard(results: list[dict]) -> None:
    print("\n" + "=" * 78)
    print(f"{'TASK':<22}{'DONE':<6}{'STEPS':<6}{'FIND':<6}{'CHECKS':<9}{'JUDGE avg':<10}")
    print("-" * 78)
    for r in results:
        j = r.get("judge") or {}
        javg = j.get("avg", "-")
        print(f"{r['id']:<22}{str(r['done']):<6}{r['steps']:<6}{r['findings']:<6}"
              f"{str(r['checks_passed'])+'/'+str(r['checks_total']):<9}{str(javg):<10}")
    print("-" * 78)
    total_p = sum(r["checks_passed"] for r in results)
    total_t = sum(r["checks_total"] for r in results)
    judged = [r["judge"]["avg"] for r in results if r.get("judge") and "avg" in r["judge"]]
    overall_judge = round(sum(judged) / len(judged), 2) if judged else "-"
    print(f"DETERMINISTIC CHECKS: {total_p}/{total_t} passed   |   "
          f"MEAN JUDGE SCORE: {overall_judge}")
    print("=" * 78)
    # trajectory metrics (the "how it got there" signal)
    print("TRAJECTORY METRICS")
    print(f"{'TASK':<22}{'TOOLS':<7}{'ERR%':<7}{'REPLAN':<8}{'NUDGE':<7}{'VRETRY':<8}{'COMPACT':<8}")
    for r in results:
        m = r.get("metrics", {})
        print(f"{r['id']:<22}{m.get('tool_calls',0):<7}{m.get('tool_error_rate',0):<7}"
              f"{m.get('replans',0):<8}{sum(m.get('nudges_by_kind',{}).values()):<7}"
              f"{m.get('verify_retries',0):<8}{m.get('compactions',0):<8}")
    print("=" * 78)
    # surface any failing checks explicitly
    for r in results:
        fails = [c for c in r["checks"] if not c["passed"]]
        if fails:
            print(f"  ! {r['id']}: " + "; ".join(f"{c['name']} ({c['detail']})" for c in fails))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(prog="eval")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--task", default=None, help="run a single task by id")
    pr.add_argument("--no-judge", action="store_true", help="skip the LLM judge")
    pr.add_argument("--max-steps", type=int, default=None)
    sub.add_parser("list")
    args = p.parse_args(argv)

    if args.cmd == "list":
        for t in TASKS:
            print(f"{t.id:<22} min_sources={t.min_sources} fault={t.fault or '-'}")
            print(f"    {t.goal}")
        return 0

    tasks = [by_id(args.task)] if args.task else TASKS
    if tasks == [None]:
        print(f"unknown task: {args.task}")
        return 2

    results = []
    for t in tasks:
        print(f"\n>>> running task: {t.id}")
        results.append(run_task(t, max_steps=args.max_steps, do_judge=not args.no_judge))

    _print_scorecard(results)

    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.RESULTS_DIR / (time.strftime("%Y%m%d-%H%M%S") + ".json")
    out.write_text(json.dumps({"mode": config.LLM_MODE, "results": results}, indent=2), encoding="utf-8")
    print(f"\nWrote scorecard to {out}")

    all_pass = all(r["checks_passed"] == r["checks_total"] for r in results)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
