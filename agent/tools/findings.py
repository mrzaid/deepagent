"""record_finding tool: append a grounded claim. Enforces grounding at write
time — you can only record a finding citing a URL the agent has actually
fetched. This is the first line of defence against fabricated evidence."""
from __future__ import annotations

from dataclasses import asdict

from ..state import Finding


def record_finding(args: dict, state, tracer) -> str:
    claim = (args.get("claim") or "").strip()
    source_url = (args.get("source_url") or "").strip()
    quote = (args.get("quote") or "").strip()

    if not claim or not source_url:
        raise RuntimeError("record_finding requires 'claim' and 'source_url'")
    if source_url not in state.fetched_urls():
        raise RuntimeError(
            f"cannot cite {source_url}: it has not been fetched. "
            f"Use fetch_url on it first, then record the finding."
        )

    # WI-9: dedup identical (claim, source_url) so re-recording doesn't inflate the ledger
    norm = claim.strip().lower()
    if any(existing.source_url == source_url and existing.claim.strip().lower() == norm
           for existing in state.findings):
        return f"Already recorded that finding (citing {source_url}); skipped duplicate."

    f = Finding(claim=claim, source_url=source_url, quote=quote, step=state.steps)
    state.findings.append(f)
    tracer.emit("finding_recorded", asdict(f) | {"index": len(state.findings)})
    return f"Recorded finding [{len(state.findings)}] citing {source_url}."
