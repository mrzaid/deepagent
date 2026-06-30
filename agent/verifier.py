"""WI-1: fresh-context critic.

After the worker produces a draft report, an INDEPENDENT reviewer with a clean
context (it never saw the plan, the reasoning, or the tool log — only the goal,
the evidence ledger, and the draft) checks that every claim is actually supported
by a cited, fetched source and that the goal is covered. This is the single
highest-signal guard against false success / hallucinated citations: the worker is
anchored on its own process, the critic is not.

Determinism rule (see implementation_final.md §5): the LLM call goes through
llm.simple so it is cassette-keyed, and there is a deterministic non-LLM fallback
(flag any finding missing a supporting quote) so offline tests stay meaningful
without a cassette.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from . import config, llm
from .prompts import CRITIC


class CriticIssue(BaseModel):
    model_config = ConfigDict(extra="ignore")
    problem: str
    fix: str = ""


class CriticVerdict(BaseModel):
    """Schema the critic must return. Malformed output is retried (see llm.structured)."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    passed: bool = Field(alias="pass")
    issues: list[CriticIssue] = Field(default_factory=list)


def _fallback_issues(state) -> list[dict]:
    """No LLM available: flag findings that lack a supporting quote — the only
    grounding signal we can check deterministically."""
    return [
        {"problem": f"finding lacks a supporting quote: {f.claim[:80]}",
         "fix": "add a direct quote from the source or drop the claim"}
        for f in state.findings if not (f.quote or "").strip()
    ]


def verify(state, tracer) -> list[dict]:
    """Return a list of issue dicts ({"problem","fix"}). Empty list == pass.
    Mutates state.tokens_used for accounting."""
    if not config.VERIFY_ENABLED:
        return []

    tracer.emit("verify_started", {"findings": len(state.findings),
                                   "skill": state.active_skill or None})
    ledger = "\n".join(
        f"- claim: {f.claim}\n  quote: {f.quote or '(none)'}\n  source: {f.source_url}"
        for f in state.findings
    ) or "(no findings recorded)"

    # When a skill is active, its validation checklist is an additional, mandatory
    # gate the critic must enforce (e.g. blanks marked, disclaimer present,
    # jurisdiction checked). No-op for plain research runs.
    checklist_block = ""
    if state.skill_checklist:
        checklist_block = (
            "\n\nNOTE: this is a SKILL-pipeline document (legal drafting/review), NOT web "
            "research — judge it against the checklist below, not against web sources. "
            "SKILL VALIDATION CHECKLIST — every item must be satisfied by the draft; flag "
            f"any that is not as an issue:\n{state.skill_checklist}")

    user = (f"GOAL:\n{state.goal}\n\nEVIDENCE LEDGER:\n{ledger}\n\n"
            f"DRAFT REPORT:\n{state.final_report}{checklist_block}\n\nReview now and respond as JSON.")

    try:
        verdict, usage = llm.structured(
            CRITIC, user, CriticVerdict, model=config.SUMMARY_MODEL,
            on_retry=lambda n, e: tracer.emit("verify_retry", {"attempt": n}),
        )
        state.tokens_used += usage.get("total_tokens", 0)
        issues = [] if verdict.passed else [i.model_dump() for i in verdict.issues]
    except Exception:  # noqa: BLE001 - critic is best-effort: degrade to the deterministic check
        issues = _fallback_issues(state)

    tracer.emit("verify_result", {"n_issues": len(issues), "issues": issues[:10]})
    return issues
