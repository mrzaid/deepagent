"""Deterministic, programmatic checks on a finished run. These need no LLM and
are fully reproducible — they measure *process* and *robustness*, complementing
the LLM judge which measures answer quality.

Each check returns (name, passed: bool, detail: str).
"""
from __future__ import annotations

import re

from agent import config

_URL_RE = re.compile(r"https?://[^\s\)\]\>\"']+")


def _cited_urls(report: str) -> set[str]:
    return {u.rstrip(".,);]") for u in _URL_RE.findall(report or "")}


def run_checks(task, state, trace) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    fetched = state.fetched_urls()
    cited = _cited_urls(state.final_report)
    distinct_cited = cited & fetched
    report = state.final_report or ""

    # --- checks that apply to every task ---------------------------------
    results.append(("completed", state.done, f"done={state.done}"))
    results.append(("has_report", bool(report.strip()), f"{len(report)} chars"))
    fabricated = cited - fetched
    results.append(("no_fabricated_citations", len(fabricated) == 0,
                    "none" if not fabricated else f"fabricated: {sorted(fabricated)}"))
    results.append(("within_step_budget", state.steps <= config.STEP_BUDGET,
                    f"{state.steps}/{config.STEP_BUDGET} steps"))

    # the fresh-context critic must have accepted with no outstanding issues
    # (verifier off / no events -> not applicable). For skill tasks the critic
    # enforces the skill's validation checklist instead of web grounding.
    verify_results = [e for e in trace if e["type"] == "verify_result"]
    if verify_results:
        last_issues = verify_results[-1]["data"].get("n_issues", 0)
        results.append(("claims_verified", last_issues == 0,
                        f"critic outstanding issues={last_issues}"))

    if task.skill:
        results.extend(_skill_checks(task, state, trace, report))
    else:
        results.extend(_research_checks(task, state, trace, distinct_cited))
    return results


def _research_checks(task, state, trace, distinct_cited) -> list[tuple[str, bool, str]]:
    out = [(
        f"cited>={task.min_sources}",
        len(distinct_cited) >= task.min_sources,
        f"{len(distinct_cited)} distinct fetched sources cited",
    )]
    if task.fault == "fail_first_fetch":
        had_error = any(e["type"] == "observation" and not e["data"].get("ok", True) for e in trace)
        recovered = had_error and state.done and len(state.findings) >= 1
        out.append(("recovered_from_fault", recovered,
                    f"saw_error={had_error}, done={state.done}, findings={len(state.findings)}"))
    elif task.fault == "empty_results":
        rep = (state.final_report or "").lower()
        admits_gap = any(p in rep for p in (
            "unable", "could not", "insufficient", "no sources", "no published",
            "not find", "no results", "no verified", "no evidence"))
        no_false_success = state.done and len(distinct_cited) == 0 and admits_gap
        out.append(("no_false_success", no_false_success,
                    f"cited={len(distinct_cited)}, admits_gap={admits_gap}"))
    return out


def _skill_checks(task, state, trace, report) -> list[tuple[str, bool, str]]:
    """Legal drafting/review has no web citations; success is: the agent engaged
    the right skill pipeline, included the attorney-review disclaimer, and marked
    unknowns instead of fabricating them."""
    low = report.lower()
    used_skill = any(e["type"] == "skill_loaded" for e in trace)
    loaded_pipeline = any(e["type"] == "reference_read" for e in trace)
    disclaimer = ("attorney review" in low) or ("not constitute legal advice" in low) \
        or ("not legal advice" in low)
    marks_unknowns = any(tok in report for tok in ("[BLANK]", "[TBD]", "[CONFIRM"))
    return [
        ("used_skill", used_skill, f"skill_loaded event: {used_skill}"),
        ("loaded_pipeline", loaded_pipeline, f"reference_read event: {loaded_pipeline}"),
        ("attorney_disclaimer", disclaimer, "present" if disclaimer else "missing"),
        ("marks_unknowns", marks_unknowns,
         "marks [BLANK]/[TBD]" if marks_unknowns else "no blank markers (may have fabricated)"),
    ]
