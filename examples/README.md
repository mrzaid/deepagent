# Example runs

Two real, unedited runs are committed here — the **headline** is a drafted legal NDA
(produced by the `paralegal` skill); a research run is included as a second domain.

## 1. `legal-nda-draft/` — the headline example  ·  `paralegal` skill, Pipeline A

> *Draft a mutual non-disclosure agreement between Acme Corp and Beta LLC, governed by
> Washington law, for evaluating a potential partnership. Use only the facts given; mark
> every unknown field as `[BLANK]`. Include the attorney-review disclaimer.*

Files: `report.md` (the drafted NDA), the attorney-review `*.docx` (`export_docx`),
`trace.jsonl` (every event), `state.json` (final structured state).

What it demonstrates (visible in the trace):
- `skill_loaded` → `reference_read` — the agent routed to the `paralegal` skill and
  pulled in the **contract-draft** pipeline just-in-time (progressive disclosure).
- The draft uses the **given party names** (Acme Corp, Beta LLC, Washington law) while
  marking every unknown field **`[BLANK]`** rather than inventing it — the
  no-hallucination guarantee, in legal form.
- Mandatory clauses present (governing law, confidentiality, term, IP) and the
  **attorney-review disclaimer**.
- `docx_exported` — a real attorney-review `.docx` artifact is written.
- The **fresh-context critic** enforcing the skill's *validation checklist*
  (`verify_failed → revise → verify_result`).
- No web sources are cited — by design: `finish` is mode-aware for skills, so
  anti-fabrication still holds while the skill checklist + critic stand in for web
  grounding.

Replay offline & free: `LLM_MODE=replay python -m eval run --task legal-nda-draft`
then `python -m agent trace eval-legal-nda-draft`.

## 2. `tavily-api/` — research example (fault injection)

> *What is the Tavily API, what are its main features, and how is it priced?*
> — with the **first `fetch_url` forced to fail** (`fault="fail_first_fetch"`).

Demonstrates recovery from an injected tool failure (the first fetch raises, becomes
an `ERROR` observation, the agent re-searches and continues to a cited report),
search → fetch → record cycles, and the critic firing twice (`verify_retries = 2`).
Replay: `LLM_MODE=replay python -m eval run --task tavily-api`.

---

To watch a run live: `python -m uvicorn server.app:app` → http://localhost:8000.

> Note: on this harness `gpt-5.1` scores lower than `gpt-4.1-mini` did (it
> over-deliberates and under-collects) — see the README's Results section for the
> eval-driven comparison.
