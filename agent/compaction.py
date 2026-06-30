"""WI-2: real context compaction.

The bounded-context claim only holds if the rebuilt prompt actually stays bounded
as findings accumulate. Beyond COMPACT_FINDINGS_AFTER findings, the older ones are
collapsed into a single text digest (`state.findings_digest`) and only the most
recent COMPACT_FINDINGS_RECENT are rendered verbatim (see context.py). The full
findings list is NEVER dropped from state — finish/_force_synthesis still see all
of them; only the *rendered prompt* is compacted.

The digest is produced by the cheap model (cassette-keyed) with a deterministic
non-LLM fallback so replay/offline stays reproducible.
"""
from __future__ import annotations

from . import config, llm

_DIGEST_SYS = (
    "You compress a research agent's older findings into a compact digest it can "
    "carry cheaply. Preserve the key facts and keep each source URL in parentheses. "
    "Output a short bulleted list, no preamble."
)


def _digest_text(goal: str, findings) -> str:
    block = "\n".join(f"- {f.claim} (source: {f.source_url})" for f in findings)
    # deterministic fallback used when no LLM/cassette is available
    fallback = "; ".join(f"{f.claim} ({f.source_url})" for f in findings)[:1500]
    try:
        resp = llm.simple(_DIGEST_SYS, f"GOAL: {goal}\n\nFINDINGS:\n{block}\n\nDigest:",
                          model=config.SUMMARY_MODEL)
        text = (resp.content or "").strip()
        return (text or fallback), resp.usage.get("total_tokens", 0)
    except Exception:  # noqa: BLE001
        return fallback, 0


def maybe_compact(state, tracer) -> bool:
    """Collapse older findings into state.findings_digest. Returns True if it ran.
    Bounded to at most once every COMPACT_EVERY steps to limit cost."""
    if len(state.findings) <= config.COMPACT_FINDINGS_AFTER:
        return False
    if config.COMPACT_EVERY > 0 and state.steps % config.COMPACT_EVERY != 0:
        return False

    older = state.findings[: -config.COMPACT_FINDINGS_RECENT] if config.COMPACT_FINDINGS_RECENT else state.findings
    if not older:
        return False

    digest, tokens = _digest_text(state.goal, older)
    state.tokens_used += tokens
    if digest and digest != state.findings_digest:
        state.findings_digest = digest
        state.compactions += 1
        tracer.emit("compaction", {"findings_digested": len(older),
                                   "digest_chars": len(digest)})
        return True
    return False
