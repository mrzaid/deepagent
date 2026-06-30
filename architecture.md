# deepagent — Architecture

`deepagent` is a small, self-contained deep-research agent. Given a research goal, it works in an explicit plan → act → observe → adapt loop: it plans sub-questions, searches the web, reads sources, records grounded findings, and synthesises a cited markdown report. The same run can be watched live in a browser or scored offline by an eval harness, both reading one shared trace.

This document describes how the system is put together: the major components, the data that flows between them, and the design decisions that hold it together.

## Guiding ideas

Three ideas explain most of the code.

**Structured state, reconstructed context.** The agent never accumulates an ever-growing chat transcript. Instead it keeps one compact, structured `ResearchState` object and rebuilds a bounded prompt from it on every turn. Large artifacts (full page text) live on disk, out of the prompt. This keeps token cost roughly flat no matter how long a run goes.

**Failures are data.** Tool calls raise exceptions on failure; the loop catches them and feeds the error back to the model as an observation it can react to. A run is bounded by step and token budgets, and it never ends without producing a grounded report (a force-synthesis fallback guarantees output even if the budget runs out).

**Grounding is enforced, not requested.** A claim can only be recorded against a URL the agent actually fetched, and the final report is rejected if it cites a URL that was never fetched. Grounding is checked at write time and again at finish time, rather than relying on the model to behave.

## Top-level layout

```
agent/        the research agent: loop, state, context, LLM client, tools
  tools/      one file per tool (search, fetch, plan, findings, notes, finish)
server/       FastAPI app + single static page for live observability (SSE)
eval/         offline eval harness: task set, deterministic checks, LLM judge
runs/         per-run artifacts (state.json, trace.jsonl, fetched pages, notes)
examples/     a sample completed run for reference
tests/        offline tests
```

The dependency direction is one-way: `server/` and `eval/` both import `agent/`, and nothing in `agent/` imports back out. `agent/` itself fans out from `loop.py`.

## The agent

### Control loop (`agent/loop.py`)

`run(goal, ...)` is the entry point. It creates (or resumes) a `ResearchState`, then iterates until one of three things happens: the model calls `finish`, the step budget is hit, or the token budget is hit.

Each iteration does the following:

1. **Nudge check.** Before asking the model, the loop inspects cheap progress counters and may inject a one-off corrective note. Two nudges exist, most-specific first: searching repeatedly without ever reading a source, and a general stall (repeating actions or gathering no new evidence).
2. **Build context.** `build_context` renders the current state into a fresh two-message prompt (see below).
3. **Ask for one action.** `llm.chat(..., tool_choice="required")` forces the model to return exactly one tool call. Token usage is accumulated onto the state.
4. **Dispatch.** The chosen tool runs via `dispatch`. Any exception becomes an `ERROR: ...` observation string rather than crashing the run.
5. **Record and account.** The observation is emitted to the trace and pushed onto short-term memory. Stall and search-without-fetch counters are updated based on whether the step made progress (new finding, new fetched source, or a plan/finish call).
6. **Persist.** State is written to `state.json` after every step, so a run is crash-safe and resumable.

Deliberately, the loop executes **one tool per step**. This keeps the trace linear and makes stall detection and adaptation simple to reason about.

When the loop exits without the model having finished, `_force_synthesis` composes a report directly from the recorded findings (which are grounded by construction). If even the synthesis LLM call fails, a deterministic report is assembled from findings and their source URLs, so a run *always* yields something cited.

### State (`agent/state.py`)

`ResearchState` is the agent's long-term memory and the single source of truth. Key fields:

- `goal`, `run_id`, `steps`, `tokens_used`, `done`, `final_report` — run identity and progress.
- `plan: list[PlanStep]` — the current plan, each step `pending | active | done | dropped`.
- `findings: list[Finding]` — grounded claims, each tied to a fetched `source_url` and a supporting quote.
- `sources: dict[url, Source]` — every URL the agent has seen, flagged `fetched` or not, with a title and summary once read.
- `short_term: list[Turn]` — the last *K* raw tool calls + observations (`MAX_SHORT_TERM`, default 4), for tactical continuity.
- `notes: dict[name, body]` — a scratchpad (see notes tool). Only names and sizes ever enter the prompt.
- Bookkeeping: `stall_counter`, `last_action_sig`, `nudges`, `searches_since_fetch`, and an eval `fault` dict.

State serialises to `runs/<run_id>/state.json` via an atomic-ish temp-file-then-replace write. Loading it back reconstructs every field, which is what makes `resume` faithful. Full page text is intentionally **not** stored here — it lives in `runs/<run_id>/pages/<hash>.txt` so it never bloats the rolling context.

### Context construction (`agent/context.py`)

This is the core context-engineering piece. `build_context` rebuilds a compact prompt every turn rather than appending to a transcript. The prompt is just two messages: the system prompt, and a single rendered "state header" containing the goal, the remaining budget (with an explicit pressure note when ≤3 steps remain), the plan, the numbered findings, the source index, the note names, and the last *K* raw actions. Older raw tool output is dropped because its value has already been distilled into findings and source summaries. The result stays roughly constant in size regardless of run length.

Sources get stable `[n]` numbering so the model can be guided toward consistent inline citations.

### LLM client (`agent/llm.py`)

A thin wrapper over the OpenAI chat-completions API that adds three things:

- **Normalisation** into simple `LLMResponse` / `ToolCall` dataclasses.
- **Token accounting** and **transient-error retry** with exponential backoff (rate limits, timeouts, 5xx).
- **A cassette layer** for deterministic offline replay. Each request is keyed by a SHA-256 hash of its full payload. In `record` mode the response is saved to `eval/cassettes/`; in `replay` mode it is served from disk with no network call. Recording is write-once, so repeated identical prompts in a run return the same value (important because the model is not perfectly deterministic even at temperature 0).

Critically, each LLM call is effectively **stateless** — the loop hands over a freshly reconstructed prompt every time. That is what allows many steps without unbounded context growth.

### Tools (`agent/tools/`)

Every tool is a plain function with the signature `(args, state, tracer) -> observation_str` and raises on failure. `tools/__init__.py` holds the OpenAI function schemas (`TOOL_SCHEMAS`) and the name→callable `dispatch`. The seven tools:

| Tool | Purpose | Grounding / notes |
|------|---------|-------------------|
| `update_plan` | Set or replace the ordered plan | Planning is an explicit, observable tool call (not hidden reasoning) |
| `web_search` | Tavily search for a sub-question | Registers result URLs as *unfetched* sources |
| `fetch_url` | Download a page, extract text | Stores full text on disk; returns only a summary + short excerpt |
| `record_finding` | Save a claim + source URL + quote | **Rejected** unless the URL was already fetched |
| `write_note` / `read_note` | Scratchpad working memory | Bodies stay out of the prompt; notes are scratch, *not* evidence |
| `finish` | Finalise the markdown report | **Rejected** if it cites any un-fetched URL |

`fetch_url` is where the context strategy pays off: page bodies are capped (`PAGE_MAX_CHARS`) and written to `pages/<hash>.txt`; the model only ever sees an LLM-generated summary plus a short excerpt (`PAGE_EXCERPT_CHARS`). Text extraction prefers `trafilatura` and falls back to a naive HTML strip.

`web_search` and `fetch_url` both run their network side-effects through the `cache.py` cassette, the tool-side counterpart to the LLM cassette — together they make a full run reproducible offline.

### Cache (`agent/cache.py`)

`cached(kind, key, producer)` mirrors the LLM cassette logic for network side-effects. Under `replay` it returns saved values (and faithfully re-raises recorded failures) with no HTTP; under `record` it calls the producer and saves the result write-once; under `live` it just calls through. With both cassette layers, an eval run under `LLM_MODE=replay` is fully offline, deterministic, and free.

### Tracing (`agent/tracer.py`)

Observability and eval input come from one artifact. Every meaningful event (`run_started`, `step_started`, `tool_call`, `observation`, `finding_recorded`, `plan_created/revised`, `nudge`, `finished`, `run_ended`, errors) is emitted as a structured record that is both **appended to `runs/<run_id>/trace.jsonl`** and **published to live in-process subscribers** (the web UI's SSE stream). Because the UI and the eval harness read the same trace, the UI shows exactly what the eval scores.

### Config (`agent/config.py`)

All tunables live in one place, sourced from environment variables (via `.env`) with sensible defaults: model names (`AGENT_MODEL`, `SUMMARY_MODEL`, `JUDGE_MODEL`), budgets (`STEP_BUDGET`, `TOKEN_BUDGET`, `MAX_SHORT_TERM`, `STALL_LIMIT`, `SEARCH_WITHOUT_FETCH_LIMIT`), tool tuning (search result count, page caps, fetch timeout), the API keys, and `LLM_MODE` (`live | record | replay`).

### CLI (`agent/cli.py`)

`python -m agent run "<goal>"` runs a new task (with optional `--run-id`, `--max-steps`, `--fault`); `python -m agent resume <run_id>` continues an interrupted run. It prints a summary and the report, and exits non-zero if the run did not complete. The eval harness drives the agent through the same `loop.run` entry point.

## The server (`server/app.py`)

A minimal FastAPI app for live observability:

- `POST /run` starts `loop.run` in a background daemon thread and returns a `run_id` immediately. Worker crashes are surfaced into the trace stream rather than lost.
- `GET /events/{run_id}` is a Server-Sent Events stream. It **subscribes before** replaying the on-disk trace (so no live event slips through the gap), emits the history, then follows live events until `run_ended`, with periodic keep-alives.
- `GET /` serves the single static page (`server/static/index.html`) that renders the plan, steps, findings, and final report as they stream in.

## The eval harness (`eval/`)

The eval pillar measures both *process/robustness* (deterministic) and *answer quality* (LLM judge).

- **`tasks.py`** — a small fixed suite of research goals chosen to exercise distinct behaviours: multi-part synthesis, broad/ambiguous goals that reward re-planning, and one fault-injection task (`fail_first_fetch`) that tests recovery.
- **`harness.py`** — runs each task headless from a clean run dir, then scores it. Prints a scorecard and writes full results JSON to `eval/results/`. `python -m eval run [--task <id>] [--no-judge] [--max-steps N]`.
- **`checks.py`** — deterministic, LLM-free checks: completed, has a report, cites at least `min_sources` distinct fetched URLs, no fabricated citations, within step budget, and (for fault tasks) confirmed it saw a failure and still recovered.
- **`judge.py`** — LLM-as-judge scoring the report 1–5 on relevance, grounding, completeness, and coherence. It uses the same cassette layer, so judging is deterministic under replay.

Fault injection is threaded end-to-end: the CLI/harness sets `state.fault`, `fetch_url` honours `fail_first_fetch` by raising once, and `checks.py` verifies the agent recovered.

## End-to-end flow

```
goal ─▶ loop.run
          │  (each step)
          ├─ nudge check (stall / search-without-fetch counters)
          ├─ build_context(state) ──▶ 2-message prompt
          ├─ llm.chat(tool_choice=required) ──▶ one ToolCall
          │        └─ cassette: live | record | replay
          ├─ dispatch(tool) ──▶ observation (exceptions become observations)
          │        ├─ web_search ──▶ register sources        (cache cassette)
          │        ├─ fetch_url  ──▶ pages/<hash>.txt + summary (cache cassette)
          │        ├─ record_finding ──▶ findings[]  (must be fetched)
          │        ├─ write/read_note ──▶ notes{}
          │        └─ finish ──▶ final_report  (rejects un-fetched citations)
          ├─ tracer.emit(...) ──▶ trace.jsonl + live SSE subscribers
          └─ state.persist() ──▶ state.json   (resume-safe)
          ▼
   budget exhausted? ──▶ _force_synthesis (grounded report from findings)
          ▼
   final cited markdown report
```

The same `runs/<run_id>/` artifacts (`state.json`, `trace.jsonl`, `pages/`, `notes/`) feed three consumers without duplication: `resume`, the live web UI, and the eval harness.

## Key design trade-offs

- **One action per step** trades a little throughput for a clean, linear trace and simple adaptation/stall logic.
- **Reconstructed context over a growing transcript** trades some conversational continuity for bounded, predictable token cost on long runs — recovered partly by keeping the last *K* raw turns and the notes scratchpad.
- **Enforced grounding** (at `record_finding` and again at `finish`) trades model freedom for a hard guarantee against fabricated citations.
- **Unified trace** for UI and eval avoids drift between what a human sees and what the suite scores, at the cost of coupling both to one event schema.
- **Two cassette layers** add bookkeeping but buy fully offline, deterministic, free eval runs.
