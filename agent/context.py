"""Bounded context construction — the core prompt/context-engineering piece.

Instead of an ever-growing transcript, we rebuild a compact prompt from the
structured state every turn: goal, budget, plan, findings, a source index, and
only the last K raw tool turns. Older raw tool output is dropped because its
value was already distilled into findings and source summaries. This keeps the
prompt roughly constant in size no matter how long the run goes.
"""
from __future__ import annotations

from . import config
from .prompts import SYSTEM, SKILLS_ADDENDUM
from .state import ResearchState

_STATUS_MARK = {"done": "[x]", "active": "[>]", "dropped": "[-]", "pending": "[ ]"}


def _render_plan(state: ResearchState) -> str:
    if not state.plan:
        return "(no plan yet — call update_plan first)"
    return "\n".join(f"{_STATUS_MARK.get(p.status, '[ ]')} {p.id}. {p.text}" for p in state.plan)


def _source_index(state: ResearchState) -> dict[str, int]:
    """Stable numbering for fetched sources, for [n]-style citation guidance."""
    idx = {}
    n = 0
    for url, src in state.sources.items():
        if src.fetched:
            n += 1
            idx[url] = n
    return idx


def _render_sources(state: ResearchState, idx: dict[str, int]) -> str:
    # Keep this bounded too: every fetched source keeps its stable "[n] title — url"
    # line (short), but summaries (the bulky part) are shown only for the most recent
    # COMPACT_SOURCES_AFTER fetched sources — older summaries already live in findings.
    fetched_n = len(idx)
    summary_cutoff = fetched_n - config.COMPACT_SOURCES_AFTER  # show summary when n > cutoff
    lines = []
    for url, src in state.sources.items():
        if src.fetched:
            n = idx[url]
            lines.append(f"[{n}] {src.title or '(untitled)'} — {url}")
            if src.summary and n > summary_cutoff:
                lines.append(f"      summary: {src.summary}")
        else:
            lines.append(f"( - ) {src.title or '(untitled)'} — {url}  (not fetched)")
    return "\n".join(lines) if lines else "(none yet)"


def _one_finding(i: int, f, idx: dict[str, int]) -> str:
    si = idx.get(f.source_url)
    tag = f"source [{si}]" if si else f.source_url
    quote = f' "{f.quote[:160]}"' if f.quote else ""
    return f"{i}. {f.claim} ({tag}){quote}"


def _render_findings(state: ResearchState, idx: dict[str, int]) -> str:
    if not state.findings:
        return "(none yet)"
    n = len(state.findings)
    # Below the threshold: render everything verbatim (the common case).
    if n <= config.COMPACT_FINDINGS_AFTER or not state.findings_digest:
        return "\n".join(_one_finding(i, f, idx) for i, f in enumerate(state.findings, 1))
    # Compacted: a digest of the older findings + the most recent ones verbatim.
    # Indices stay aligned with the full list so [n] references remain stable.
    recent = config.COMPACT_FINDINGS_RECENT
    start = n - recent
    lines = [f"[digest of earlier findings 1-{start}]", state.findings_digest,
             f"[most recent {recent} findings]"]
    for i in range(start, n):
        lines.append(_one_finding(i + 1, state.findings[i], idx))
    return "\n".join(lines)


def _render_recent(state: ResearchState) -> str:
    if not state.short_term:
        return "(none yet)"
    lines = []
    for t in state.short_term:
        args = ", ".join(f"{k}={str(v)[:60]}" for k, v in t.args.items())
        obs = t.observation.replace("\n", " ")[:240]
        lines.append(f"- step {t.step}: {t.tool}({args}) -> {obs}")
    return "\n".join(lines)


def _render_notes(state: ResearchState) -> str:
    if not state.notes:
        return "(none yet)"
    # names + sizes only — bodies are pulled in on demand via read_note
    return "\n".join(f"- {name} ({len(body)} chars)" for name, body in state.notes.items())


def build_context(state: ResearchState, note: str | None = None,
                  step_budget: int | None = None) -> list[dict]:
    step_budget = step_budget or config.STEP_BUDGET
    idx = _source_index(state)
    remaining = step_budget - state.steps

    pressure = ""
    if remaining <= 3:
        pressure = ("\n!! Budget almost exhausted — stop searching and call finish "
                    "now with the findings you have.")

    skill_line = f"\n\n## ACTIVE SKILL\n{state.active_skill}" if state.active_skill else ""

    header = f"""## GOAL
{state.goal}{skill_line}

## BUDGET
Step {state.steps} of {step_budget} (≈{remaining} left). Tokens used ~{state.tokens_used}/{config.TOKEN_BUDGET}.{pressure}

## PLAN
{_render_plan(state)}

## FINDINGS ({len(state.findings)})
{_render_findings(state, idx)}

## SOURCES
{_render_sources(state, idx)}

## NOTES (scratchpad — read_note to view a body)
{_render_notes(state)}

## RECENT ACTIONS (last {config.MAX_SHORT_TERM})
{_render_recent(state)}

## NEXT
Decide the single most useful next action and call exactly one tool."""

    if note:
        header += f"\n\nNOTE: {note}"

    system = SYSTEM + (SKILLS_ADDENDUM if config.SKILLS_ENABLED else "")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": header},
    ]
