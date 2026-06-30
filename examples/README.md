# Example run

A real, unedited run of the agent (model **`gpt-5.1`**) on the fault-injection task:

> *What is the Tavily API, what are its main features, and how is it priced?*
> — with the **first `fetch_url` forced to fail** (`fault="fail_first_fetch"`).

Files in `tavily-api/`:

- **`report.md`** — the final cited report.
- **`trace.jsonl`** — every event the agent emitted (the same stream the web UI
  renders and the eval harness reads). Render it with
  `python -m agent trace eval-tavily-api` once it's under `runs/`, or skim the JSONL.
- **`state.json`** — the final structured state (plan, findings, sources).

What this run demonstrates (visible in the trace):

- **Recovery from an injected tool failure** — the first fetch raises, becomes an
  `ERROR` observation, and the agent adapts and continues to a cited report.
- Search → fetch → record cycles producing 3 grounded findings.
- **The fresh-context critic at work** — two `verify_failed` events: the independent
  reviewer rejected the first drafts, the agent revised, and only the accepted draft
  finished (`verify_retries = 2`).
- `nudge` / `plan_revised` events as it adapts.

To watch a run live: `python -m uvicorn server.app:app` → http://localhost:8000.
To replay this exact run offline & free: `LLM_MODE=replay python -m eval run --task tavily-api`.

> Note: on this harness `gpt-5.1` scores lower than `gpt-4.1-mini` did (it
> over-deliberates and under-collects) — see the README's Results section for the
> eval-driven comparison.
