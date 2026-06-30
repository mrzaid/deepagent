# Changelog

All notable changes to **deepagent**. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); newest first.

---

## [0.8.0] — 2026-06-30 — Legal-skill eval cases + reference-resolution backstop

Extends the eval harness to cover the `paralegal` skill (the suite was research-only).

### Added
- **4 legal eval tasks** (`eval/tasks.py`, new `skill` field): `legal-nda-draft`
  (pipeline A), `legal-contract-review` (B), `legal-ads-offer-letter` (G),
  `legal-lease-amendment` (C).
- **Skill-aware checks** (`eval/checks.py`): for `skill` tasks the web-citation
  checks are replaced by `used_skill`, `loaded_pipeline`, `attorney_disclaimer`,
  `marks_unknowns` (the critic still enforces the skill's validation checklist).
- **Harness toggles `SKILLS_ENABLED` per task** (`eval/harness.py`, save/restore), so
  research tasks stay byte-identical while skill tasks get the skill tools; the judge
  is skipped for skill tasks (its rubric is research-oriented).
- Recorded skill cassettes (gpt-5.1) so the legal tasks replay offline too.

### Changed / Fixed
- **Reference-resolution backstop** (`agent/skills.py`): the model kept inventing
  reference filenames (`nda-mutual-draft.md`, `offer-letter-standard.md`, …) and
  wasting a step on the not-found error. `read_reference` now keyword-aliases an
  invented name to the correct pipeline (e.g. `*review*` → `contract-review.md`,
  `*nda/msa/draft*` → `contract-draft.md`), transparently noted in the observation.
- **`skills/SKILL.md`**: added an explicit "pass ONE of these EXACT paths" doc-type→
  file table and a note that there is no per-document file.
- New `test_read_reference_aliases_invented_names`; skills suite 8/8.

### Results
- After the fix: **zero reference-not-found errors**; legal runs faster
  (`contract-review` 15→10 steps, `ads-offer-letter` 8/9→**9/9**). Legal subtotal
  **32/36**; combined with research **68/79 deterministic checks**, reproducible via
  `LLM_MODE=replay python -m eval run`. Recurring legal miss is `claims_verified`
  (strict gpt-5.1 critic on the validation checklist) + one NDA disclaimer omission.

## [0.7.0] — 2026-06-29 — Switch to gpt-5.1 + eval-driven model finding

- **Models → `gpt-5.1`** (agent, summaries, judge) — the best model accessible on
  this key. Probed compatibility first: `gpt-5.1` accepts `temperature=0` + tools;
  `gpt-5-mini` does **not** (rejects `temperature=0`); `gpt-5.4/5.5` are not
  accessible. `.env` de-duped to a single model block.
- **Re-recorded the eval on `gpt-5.1`** so `LLM_MODE=replay` reproduces again
  (cassette keys include the model). New scorecard: **36/43 checks · mean judge
  4.04**, verified byte-identical on replay.
- **Honest finding (documented in the README):** `gpt-5.1` scores **lower** than
  `gpt-4.1-mini` did (41/43 · 5.0) on this harness — it over-deliberates and
  under-collects (e.g. 12 replans on one task), gathering fewer findings/citations
  within the step budget, and its critic is stricter. The harness turned "use the
  best model" into a measured trade-off; kept `gpt-5.1` by choice, with the loop-side
  fix (budget/nudge tuning for reasoning models) noted as next work.
- **Example run** regenerated from the `gpt-5.1` `tavily-api` trace (fault recovery +
  2 critic retries); `examples/` README updated.

## [0.6.0] — 2026-06-29 — Schema-validated structured outputs + retry

Borrowed from the `reference/docex-app-main` best practices: treat malformed
structured LLM output as a *transient* error and retry, instead of accepting
degraded data.

### Added / Changed
- **`llm.structured(system, user, schema, …)`** (`agent/llm.py`): asks for JSON,
  validates it against a **pydantic** model (`model_validate_json`), and on
  `ValidationError`/parse failure **retries** the call (malformed output = transient);
  raises `StructuredOutputError` after the cap so callers can fall back. Retries
  only fire on a live call (a cassette response is fixed). `pydantic>=2.6` added to
  requirements (already present transitively via FastAPI).
- **Critic** (`agent/verifier.py`): a `CriticVerdict`/`CriticIssue` pydantic schema
  (`pass` alias, `extra=ignore`) replaces the loose JSON parse; emits a
  `verify_retry` trace event; still degrades to the deterministic fallback.
- **Judge** (`eval/judge.py`): a `JudgeVerdict` schema (scores constrained `1..5`)
  replaces the loose parse.
- New unit test `test_structured_validates_and_retries` (malformed→retry→validate,
  then exhaustion→raise). All suites green.
- **Did NOT add** tenacity or a circuit breaker: our jittered exponential backoff
  is already equivalent, and a breaker is unjustified for a single-user agent whose
  blast radius is already bounded by run-abort + step/token/wall-clock budgets.

### Note (replay is keyed to the recorded model)
A cassette's key includes the model name, so `LLM_MODE=replay` reproduces the
committed scorecard **only with the models it was recorded under (`gpt-4.1-mini`)**.
Verified: `AGENT_MODEL=gpt-4.1-mini … LLM_MODE=replay python -m eval run` →
41/43 checks, mean judge 5.0 (critic + judge now pydantic-validated). Changing the
model in `.env` (e.g. to `gpt-5.4`) intentionally invalidates replay until re-recorded.

## [0.5.0] — 2026-06-29 — React + TypeScript front end

Replaced the single-file vanilla-JS UI with a small **React + TypeScript** SPA
(Vite) under `web/`. The interaction model is ours to choose; this is the UI layer,
not an agent framework.

### Added / Changed
- **`web/`** — Vite + React + TS, dependencies limited to React. One screen, no
  router, no state library: `useReducer` over an `EventSource`, ~5 components
  (`RunControls`, `PlanPanel`, `TraceTimeline`, `FindingsPanel`, `ReportPanel`).
- **One typed contract end-to-end**: `web/src/types.ts` is a `TraceEvent`
  discriminated union mirroring `agent/tracer.py`; the reducer switches on
  `ev.type`. (The type checker caught a real `patchStep` variance bug during the
  build — exactly the payoff.)
- **No Node at runtime**: Vite builds into `server/static/` and the **compiled
  bundle is committed**, so `uvicorn server.app:app` serves the SPA unchanged.
  `server/app.py` gains a guarded `/assets` `StaticFiles` mount for the hashed JS/CSS.
- Preserves all prior UI behaviour: live step timeline, plan/findings panels,
  event markers (nudge/compaction/verify/skill/etc.), and **token-by-token report
  streaming** via `report_delta`; adds an "active skill" badge.
- `.gitignore`: ignore `web/node_modules` only (the built bundle stays committed).

### Notes
- Build: `cd web && npm install && npm run build` (`build` = `tsc --noEmit && vite
  build`). Dev: `npm run dev` proxies `/run` + `/events` to FastAPI on :8000.
- Python suites (offline + robustness + skills) and the research-eval replay
  (41/43) are unaffected — the change is frontend + one server mount.

## [0.4.1] — 2026-06-28 — Streaming the final report

- **Token-level streaming of the final report** to the live web UI. `agent/llm.py`
  gains an `on_report_delta` callback and a streaming path (`stream=True`,
  `stream_options.include_usage`): it surfaces clean report TEXT extracted from the
  `finish` tool-call's `report` argument as it forms, and streams plain text for the
  force-synthesis path. The loop wires this to a new `report_delta` trace event; the
  web UI types the report into the panel with a blinking caret.
- Streaming is used **only** for the report-producing calls (finish / synthesis) —
  summaries, the critic, and reorientation stay non-streamed, so token accounting is
  unchanged. `stream` is not part of the cassette key, so **recorded eval runs still
  replay byte-identically** (verified 41/43).
- UI resets its buffer per step / on force-synthesis, so a critic-rejected draft and
  its re-draft each stream cleanly instead of concatenating.
- Live-verified (229 deltas reassembled correctly) + unit test for the partial-JSON
  report extractor (`test_stream_report_extraction`).

## [0.4.0] — 2026-06-28 — Skills layer (progressive-disclosure pipelines)

Adds a Claude-style **skills** capability mirroring the notes/fetch pattern: a
skill is a `SKILL.md` router (name + description in YAML frontmatter) plus detailed
reference pipelines that are pulled in just-in-time. Ships with a `paralegal` skill
(7 legal drafting/review pipelines) already under `skills/`.

### Added
- **`agent/skills.py`** — discover `SKILL.md` under `skills/`, parse frontmatter,
  `list_skills()`, `load_skill(name)`, `read_reference(name, path)` (capped, kept
  out of the rolling prompt like `pages/`), `reference_files()`,
  `extract_validation_checklist()`. Resolves the `references/<f>` vs flat `<f>`
  path mismatch in the shipped SKILL.md.
- **Three tools mirroring read_note/fetch_url** (`agent/tools/skill_tools.py`):
  `list_skills`, `use_skill` (loads router + captures the validation checklist),
  `read_reference` (JIT-loads one pipeline). Plus **`export_docx`** — a
  dependency-free `.docx` writer (`agent/docx.py`) that strips `// NOTE/ALT/RISK`
  annotations, preserves `[BRACKETED]` placeholders, and ensures the attorney-review
  disclaimer.
- **State**: `active_skill`, `skill_checklist` (round-tripped). **Tracer**:
  `skills_listed`, `skill_loaded`, `reference_read`, `docx_exported`.
- **Critic enforces the skill's validation checklist** (`agent/verifier.py`): when a
  skill is active, the checklist is injected into the fresh-context critic and the
  critic is reframed to judge the draft against it rather than web sources.

### Changed
- **Skill tools are gated behind `SKILLS_ENABLED` (default off)** so the research
  loop — and its committed eval cassettes — stay byte-identical (verified: replay
  still reproduces 41/43). Turn on with `SKILLS_ENABLED=1` for legal work.
- **`finish` grounding is now mode-aware**: anti-fabrication (no citing an
  un-fetched URL) always applies, but the *web-source-required* checks apply to
  research runs only — a legal draft legitimately has no web citations.
- The `SYSTEM` prompt gains a skills addendum **only when skills are enabled**
  (research prompt unchanged), with explicit skill-vs-research routing.

### Notes / honest caveats
- deepagent is fundamentally a research agent (search→fetch→cite); the skill
  draft/review pipelines operate on provided text, not the web. The clean split:
  research loop for legal-research questions, skill pipelines for drafting/review.
- Live-verified end to end: `use_skill('paralegal') → read_reference(contract-draft)
  → draft → export_docx` produced a real attorney-review NDA `.docx`. `gpt-4.1-mini`
  occasionally guesses a reference filename; `use_skill` now lists the exact paths
  and the error-as-observation recovers it.
- New `tests/test_skills.py` (6 tests). All suites green (offline + robustness +
  skills); research-eval replay unchanged.

---

## [0.3.0] — 2026-06-27 — Robustness & evaluation hardening

Implements the work items in `implementation_final.md` (WI-1…WI-9). The theme:
make the long-running story *undeniable* — a fresh-context critic that gates
completion, a genuinely bounded context, a complete budget/recovery circuit, and
an eval that measures the trajectory, not just the answer. Single-threaded loop,
two-gate grounding, reconstructed context, and deterministic replay were all
preserved (the invariants in `implementation_final.md` §1).

### Added

- **Fresh-context critic / verifier (WI-1).** New `agent/verifier.py`. After the
  worker calls `finish`, an independent reviewer with a *clean* context (it sees
  only the goal, the evidence ledger, and the draft — never the plan or reasoning)
  checks that every claim is supported by a cited, fetched source and that the
  goal is covered. If it finds issues and retries remain, the run reopens with the
  critique injected as the next-turn note; otherwise it's accepted.
  - `agent/prompts.py`: added `CRITIC` ("cold, independent reviewer").
  - `agent/config.py`: `VERIFY_ENABLED` (default on), `MAX_VERIFY_RETRIES` (2),
    plus a `_bool` env helper.
  - `agent/state.py`: `verify_retries` (round-tripped through `to_dict`/`from_dict`).
  - Trace events: `verify_started`, `verify_result`, `verify_failed`,
    `verify_exhausted`. New eval check `claims_verified`.
  - Deterministic fallback (no LLM/cassette): flag any finding lacking a quote,
    so offline tests stay meaningful.

- **Real context compaction (WI-2).** New `agent/compaction.py`. Beyond
  `COMPACT_FINDINGS_AFTER` findings, older ones collapse into a single
  `findings_digest` and only the most recent `COMPACT_FINDINGS_RECENT` render
  verbatim; the source list keeps stable `[n]` lines but drops older summaries.
  The full findings/sources are **never** removed from state — `finish` and
  `_force_synthesis` still see everything. Cheap-model digest with a deterministic
  concat fallback.
  - `agent/config.py`: `COMPACT_FINDINGS_AFTER=12`, `COMPACT_FINDINGS_RECENT=6`,
    `COMPACT_SOURCES_AFTER=15`, `COMPACT_EVERY=4`.
  - `agent/state.py`: `findings_digest`, `sources_digest`, `compactions` (round-tripped).
  - `agent/context.py`: `_render_findings`/`_render_sources` now compaction-aware.
  - Trace event: `compaction`.

- **Wall-clock budget (WI-3).** `agent/loop.py` now also bounds a run by elapsed
  time (`config.WALL_CLOCK_BUDGET`, default 600s, 0 disables). On breach it emits
  `budget_event{kind:"wall_clock"}` and falls through to force-synthesis. The
  deadline is recomputed each `run()` (not persisted) so a resumed run gets a
  fresh window. Step/token breaches now also emit `budget_event`.

- **Trajectory eval metrics + a no-false-success scenario (WI-5).**
  - `eval/harness.py`: derives `tool_error_rate`, `replans`, `nudges_by_kind`,
    `verify_retries`, `compactions`, `notes_written`, `tool_calls` from the trace;
    prints a TRAJECTORY METRICS block and stores the full set in the results JSON.
  - `eval/tasks.py`: new `no-sources-available` task with an `empty_results` fault.
  - `agent/tools/search.py`: `empty_results` fault injection.
  - `eval/checks.py`: `no_false_success` check (with no sources, the report must
    admit the gap and cite nothing, rather than fabricate an answer).

- **Resume "get your bearings" turn (WI-6).** On resume, before any tool call,
  a short `REORIENT` prompt has the model restate where things stand and the next
  step. Emits `reoriented`. Deterministic fallback summary if no LLM.

- **`trace` CLI renderer (WI-7).** `python -m agent trace <run_id> [--verbose]`
  renders `trace.jsonl` as a readable step → action → observation → budget
  timeline (great for the demo and for `watch`-ing a live run). stdout is
  reconfigured to UTF-8 so it's Windows-safe.

- **Operator controls: kill switch + steering (WI-8).** Before each turn the loop
  checks `runs/<id>/AGENT_STOP` (and handles SIGINT in the main thread) → halts
  cleanly with `run_ended{status:"aborted"}` and is resumable; and `runs/<id>/STEER.md`
  → injects its contents once as a steering note (`steer_injected`) then deletes it.

- **Tests.** New `tests/test_robustness.py` (8 tests): critic pass / reject+exhaust,
  compaction bounding, wall-clock termination, kill+resume, steering, reorientation,
  finding dedup. Existing `tests/test_offline.py` (6 tests) still green.

- **Web UI.** `server/static/index.html` now renders the new events
  (`verify_failed`/`verify_exhausted`, `compaction`, `budget_event`,
  `steer_injected`, `reoriented`) as timeline markers.

### Changed

- **Retry backoff now jittered (WI-4).** `agent/llm.py` uses
  `random.uniform(0, min(2**attempt, 8))` instead of a fixed sleep, to avoid
  synchronised retry storms against a rate limit.

- **`record_finding` deduplicates (WI-9).** Identical `(claim, source_url)` pairs
  are skipped so re-recording can't inflate the ledger (`agent/tools/findings.py`).

- **Stall detection is now windowed (WI-9).** `agent/loop.py` keeps a ring buffer
  of recent action signatures; an action repeated `REPEAT_LIMIT` times within the
  window counts toward a stall even if not strictly consecutive.

- **`finish` completion path.** The loop runs the critic after a successful
  `finish`; on rejection it sets `done=False`, records the critique, and continues.

### Deliberately NOT done (judgment — see README §"What I left out")

Event-sourcing rewrite, separate planner/worker/critic *services*, multi-agent
fan-out, vector store, git-per-run, provider swap. The brief rewards the simplest
harness that works; these would be unjustified complexity. The one allowed
read-only sub-agent (`implementation_final.md` §6) is left off as documented
future work.

---

## [0.2.0] — 2026-06-26 — deepagents-inspired upgrade

- **Scratchpad memory** (`write_note`/`read_note`, `agent/tools/notes.py`): a
  virtual notes store (persisted to `runs/<id>/notes/`) used as working memory;
  only note names+sizes enter the context, bodies are pulled back on demand.
  Inspired by the langchain-ai/deepagents "filesystem" pillar. (Sub-agents
  deliberately skipped.)
- **Search→fetch cadence nudge**: a targeted nudge when the agent searches
  repeatedly without reading a source (`SEARCH_WITHOUT_FETCH_LIMIT`).
- **Enriched system prompt**: notes-vs-findings discipline and the
  search→fetch→record cadence.
- Re-recorded eval (mean judge 4.79 → 5.0); new offline tests for notes + nudge.

## [0.1.0] — 2026-06-25 — Initial build

- Single-threaded **plan→act→observe→adapt** loop with one tool call per step.
- **Reconstructed bounded context** from a structured `ResearchState` each turn.
- Tools: `update_plan`, `web_search` (Tavily), `fetch_url` (readable-text extract
  + on-disk page storage), `record_finding`, `finish`.
- **Two-gate enforced grounding** (`record_finding` + `finish` reject un-fetched URLs).
- **Budgets, stall detection, force-synthesis** fallback; **crash-safe resume**.
- **Unified observability**: `trace.jsonl` + live SSE web UI (`server/`).
- **Eval harness**: deterministic checks + LLM judge + `fail_first_fetch` fault.
- **Offline replay**: cassette record/replay for LLM (`agent/llm.py`) and for
  `web_search`/`fetch_url` (`agent/cache.py`), with write-once semantics so replay
  reproduces a recorded run exactly.
