"""finish tool: finalise the report.

Anti-fabrication is enforced in BOTH modes: any URL in the report must be one the
agent actually fetched. The *web-grounding* requirements (must have fetched
sources, must cite at least one) apply to RESEARCH runs only — a skill pipeline
(legal drafting/review) legitimately produces a document with no web citations,
so those two checks are skipped when a skill is active. The skill's own validation
checklist + the fresh-context critic enforce quality there instead."""
from __future__ import annotations

import re

_URL_RE = re.compile(r"https?://[^\s\)\]\>\"']+")


def finish(args: dict, state, tracer) -> str:
    report = (args.get("report") or "").strip()
    if not report:
        raise RuntimeError("finish requires a non-empty 'report'")

    fetched = state.fetched_urls()
    cited = {u.rstrip(".,);]") for u in _URL_RE.findall(report)}

    # anti-fabrication: never allow a cited URL that wasn't fetched (both modes)
    fabricated = [u for u in cited if u not in fetched]
    if fabricated:
        raise RuntimeError(
            "report cites URLs that were never fetched (possible fabrication): "
            + ", ".join(sorted(fabricated))
            + ". Only cite sources you fetched, or fetch them first."
        )

    # web-grounding requirements — research runs only
    if not state.active_skill:
        if not fetched:
            raise RuntimeError("cannot finish: no sources have been fetched yet.")
        if not cited:
            raise RuntimeError(
                "report contains no source URLs. Cite sources inline as [n] and "
                "list them in a '## Sources' section with their URLs."
            )

    state.final_report = report
    state.done = True
    for p in state.plan:
        if p.status in ("pending", "active"):
            p.status = "done"
    tracer.emit("finished", {"report": report,
                             "sources_cited": sorted(cited),
                             "num_findings": len(state.findings)})
    return "Report finalised."
