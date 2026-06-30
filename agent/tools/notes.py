"""Scratchpad notes — a right-sized version of the deepagents filesystem pillar.

The agent uses notes as external working memory: draft an outline, accumulate a
per-subtopic summary, or stash a comparison table — then pull it back at synthesis
time. Crucially, note *bodies* never sit in the rolling context (only their names
+ sizes do, see context.py), so this lets the agent hold more working state than
the prompt could otherwise carry.

Notes are scratch, NOT evidence: grounded claims still go through record_finding
(which enforces citation to a fetched URL). The system prompt makes that explicit.
"""
from __future__ import annotations

MAX_NOTE_CHARS = 8000


def write_note(args: dict, state, tracer) -> str:
    name = (args.get("name") or "").strip()
    content = args.get("content") or ""
    if not name:
        raise RuntimeError("write_note requires a 'name'")
    if len(content) > MAX_NOTE_CHARS:
        content = content[:MAX_NOTE_CHARS]
    existed = name in state.notes
    state.write_note(name, content)
    tracer.emit("note_written", {"name": name, "chars": len(content), "overwrote": existed})
    return f"{'Updated' if existed else 'Wrote'} note '{name}' ({len(content)} chars)."


def read_note(args: dict, state, tracer) -> str:
    name = (args.get("name") or "").strip()
    if name not in state.notes:
        have = ", ".join(state.notes) or "(none)"
        raise RuntimeError(f"no note named '{name}'. Notes you have: {have}")
    return f"Note '{name}':\n{state.notes[name]}"
