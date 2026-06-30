"""LLM-as-judge: scores the final report 1-5 on four dimensions. Uses the same
cassette layer as the agent, so judging is deterministic under LLM_MODE=replay.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from agent import config, llm

_SYS = """You are a strict evaluator of research reports. Score the report on four
dimensions, each an integer 1-5 (5 = excellent):
- relevance: does it actually answer the goal?
- grounding: are claims supported by the cited sources, with no fabrication?
- completeness: does it cover the important aspects of the goal?
- coherence: is it clear, well-structured, and non-repetitive?
Respond with ONLY a JSON object:
{"relevance":N,"grounding":N,"completeness":N,"coherence":N,"comment":"one sentence"}"""


class JudgeVerdict(BaseModel):
    """Schema the judge must return; invalid output is retried (see llm.structured)."""
    model_config = ConfigDict(extra="ignore")
    relevance: int = Field(ge=1, le=5)
    grounding: int = Field(ge=1, le=5)
    completeness: int = Field(ge=1, le=5)
    coherence: int = Field(ge=1, le=5)
    comment: str = ""


def judge(goal: str, report: str, findings: list) -> dict:
    finding_lines = "\n".join(f"- {f.claim} (source: {f.source_url})" for f in findings) or "(none)"
    user = (f"GOAL:\n{goal}\n\nRECORDED FINDINGS:\n{finding_lines}\n\n"
            f"REPORT:\n{report}\n\nScore it now as JSON.")
    try:
        verdict, _ = llm.structured(_SYS, user, JudgeVerdict, model=config.JUDGE_MODEL)
    except Exception as e:  # judging is best-effort; never crash the harness
        return {"error": str(e)}
    data = verdict.model_dump()
    data["avg"] = round(
        (verdict.relevance + verdict.grounding + verdict.completeness + verdict.coherence) / 4, 2
    )
    return data
