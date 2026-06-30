# deepagent

A small **long-running research agent** with its own hand-written agent loop — no
agent frameworks (no LangChain / LangGraph / AutoGen / CrewAI). You give it a
research question; it plans sub-questions, searches the web, reads sources,
records grounded findings, **adapts its plan when steps fail**, has a
**fresh-context critic** check its own draft, and writes a **cited** report. A
minimal web UI streams every step live, and a runnable eval harness scores the
agent on a fixed task set — offline and reproducibly.

- **Language:** Python 3.12 · **LLM:** OpenAI (tool calling) · **Search:** Tavily
- **Interface:** CLI + a **React + TypeScript** SPA (FastAPI + live Server-Sent-Events)
- **Thin libraries only:** `openai`, `requests`, `trafilatura`, `fastapi`/`uvicorn`,
  `tiktoken`, `python-dotenv`. The loop, prompts, context handling, and tool
  orchestration are all my own code. (No *agent* frameworks — React is just the UI;
  the interaction model is mine to choose.)

I spent my time where the brief weights it: the **agent loop and its robustness
over many steps**, and the **evaluation harness**. I treated the happy path as the
easy 20% and put the effort into what happens when steps fail, when the context
would otherwise grow without bound, and when the model is tempted to claim success
it hasn't earned.

---

## Deliverables — where each lives

| # | Deliverable | Where |
|---|-------------|-------|
| 1 | **Source code** (public repo, clear structure, run instructions) | this repo — structure at the bottom, run steps in [Quickstart](#quickstart) |
| 2 | **README** (how it works, key decisions, more time) | this file |
| 3 | **Eval harness + results** | `python -m eval run`; code in `eval/`, results in `eval/results/`, scorecard [below](#evaluation-harness-eval) |
| 4 | **Example run** (a real task, start → finish) | [`examples/tavily-api/`](#example-run) — report + full trace + state |
| 5 | **Short video (3–5 min)** | **▶ <ADD YOUR VIDEO LINK HERE>** |
| 6 | **Build session logs** (raw, unedited) | [`build_sessions/`](#) |

---

## How it works

### The loop in one picture

```
goal ─▶ plan ─▶ ┌─────────────────────────────────────────────┐
                │  each turn: rebuild a BOUNDED context from    │
                │  STATE ▶ ask model for ONE next tool ▶ run it │
                │  ▶ observe ▶ update state ▶ persist to disk   │
                └───────────────┬─────────────────────────────┘
  update_plan · web_search · fetch_url · record_finding · write/read_note · finish
                                │
              done? ▶ fresh-context CRITIC ▶ accept │ reopen with critique
                                │
              budget out? ▶ force-synthesis (grounded report from findings)
                                ▼
                       cited markdown report
```

The agent is **not a fixed prompt chain**. Every iteration the model freely
chooses the next action from the current state, so it can re-search after a dead
end, re-plan mid-run, or finish early when it has enough.

### 1. The control loop (`agent/loop.py`) — the core

A single explicit `while` loop. Each turn it (1) builds a bounded prompt from
state, (2) asks the model for exactly **one** tool call (`tool_choice="required"`),
(3) executes the tool — where a raised exception becomes an `ERROR: …` observation
rather than a crash, so **failures are data the model reacts to** — then (4)
updates state, runs stall accounting, and persists to disk. It stops when the
model calls `finish` (subject to the critic, below), or when a budget runs out, in
which case `force_synthesis` writes a grounded report directly from the recorded
findings — so **a run never ends without a cited answer.**

### 2. State-as-context (`agent/state.py` + `agent/context.py`) — the key idea

Long runs blow past the context window if you append every message and every
fetched page. Instead I keep a structured `ResearchState` as long-term memory and
**reconstruct a compact prompt each turn** from it: the goal, budget remaining, the
plan with per-step status, findings so far (one line each with a source index), a
source list (titles + URLs + short summaries — **never page bodies**), and only the
**last K raw tool turns** for tactical continuity. Full page text is written to
`runs/<id>/pages/<hash>.txt` and never re-enters the prompt. The result: prompt
size stays roughly constant no matter how many steps the agent takes.

### 3. Tools (`agent/tools/`)

Each tool is a plain function `(args, state, tracer) -> observation` and raises on
failure:

| tool | what it does |
|------|--------------|
| `update_plan` | set/replace the plan; planning is an **observable tool call**, not hidden reasoning |
| `web_search` | Tavily search; registers result URLs as known (unfetched) sources |
| `fetch_url` | download → extract readable text → store full text on disk → return summary + excerpt |
| `record_finding` | append a grounded claim; **rejects** citing a URL that wasn't fetched |
| `write_note` / `read_note` | scratchpad memory: offload outlines/drafts so they leave the rolling context until read back |
| `finish` | finalise; **rejects** a report citing any URL the agent never fetched |

The set is small and non-overlapping on purpose — if I can't say which tool
applies, the model can't either.

### 4. Grounding is enforced in code, not just prompted

Fabricated or unsupported sources are the classic research-agent failure, so I
block them at three points rather than asking the model nicely:

1. `record_finding` only accepts a URL the agent has already fetched;
2. `finish` rejects any report citing an un-fetched URL;
3. a **fresh-context critic** (`agent/verifier.py`) then reviews the draft.

The critic is the important one: `finish` only proves a citation was *fetched*, not
that the source actually *supports* the claim. So after a draft is finalised, an
**independent reviewer with a clean context** — it sees only the goal, the evidence
ledger (claim + quote + source), and the draft, never the worker's plan or
reasoning — checks for unsupported claims and coverage gaps. If it finds issues and
retries remain, the run reopens with the critique injected as the next note and the
agent revises; otherwise the draft is accepted. The worker, anchored on its own
process, tends to miss exactly what a cold reviewer catches.

### 5. Bounded context, for real (`agent/compaction.py`)

The "bounded context" claim only holds if the rebuilt prompt stays bounded as
findings accumulate. Past a threshold, older findings collapse into a digest and
only the most recent render verbatim; older source summaries drop while the stable
`[n]` citation numbering is preserved. The full lists never leave `state`, so
`finish`/synthesis still see everything — only the *prompt* is compacted.

### 6. Robustness over many steps

- **Three budgets** — `STEP_BUDGET`, `TOKEN_BUDGET`, and a **wall-clock**
  (`WALL_CLOCK_BUDGET`) — bound every run; a breach falls through to force-synthesis,
  and the context warns the model as the step budget nears empty.
- **Stall + cadence nudges:** no-progress and "searched repeatedly without reading a
  source" both trigger one-off corrective notes.
- **Resume + reorientation:** state persists after every step; a resumed run takes a
  short *reorientation* turn first, so it re-grounds instead of acting amnesiacally.
- **Operator controls:** `runs/<id>/AGENT_STOP` (or Ctrl-C) halts cleanly and
  resumably; `runs/<id>/STEER.md` injects one-time guidance mid-run.

### 6b. Reliability: retries + schema-validated I/O (`agent/llm.py`)

Two layers, both with the same principle — *only retry what's worth retrying, and
validate before you trust*:

- **Transient-only retry with jittered exponential backoff.** API calls retry up to
  4× with `random.uniform(0, min(2**attempt, 8))` (full jitter — avoids synchronised
  retry storms), but **only for transient failures**: rate limits, timeouts,
  connection errors, and 5xx/429. Permanent 4xx (bad request, context-length, auth)
  raise immediately — retrying wastes quota and delays the real failure.
- **Schema-validated structured outputs with retry-on-validation.** Where the agent
  consumes structured JSON — the **fresh-context critic** (`CriticVerdict`) and the
  **eval judge** (`JudgeVerdict`) — `llm.structured()` parses the response into a
  **pydantic** model and treats a `ValidationError`/parse failure as *transient*: it
  re-asks the model rather than accepting malformed data, and falls back to a
  deterministic check only after the retry budget is spent. Malformed model output is
  a retryable error, not a crash. (Adopted from the `reference/docex-app-main` best
  practices; see CHANGELOG 0.6.0.)

**What I deliberately did *not* add** (judgment — the brief penalises unjustified
complexity): **tenacity** (our hand-rolled backoff is already equivalent, and one
small loop is easier to read than a decorator stack) and a **circuit breaker** (it
earns its keep in a high-throughput, multi-tenant service; this is a single-user,
budget-bounded agent that already aborts on a permanent error and is capped by
step/token/wall-clock budgets — the blast radius a breaker would contain is already
closed).

Together with the grounding gates above, that's **four safety layers** on what the
model produces: `record_finding` and `finish` gate citations, the critic checks
support/coverage, and pydantic gates the *shape* of structured outputs — and every
tool error becomes an observation, so a failure is data the model reacts to, never a
crash.

### 7. Observability is the eval input (`agent/tracer.py`)

One `Tracer` emits structured events (`plan_created`, `tool_call`, `observation`,
`finding_recorded`, `nudge`, `compaction`, `verify_*`, `budget_event`,
`force_synthesis`, `report_delta`, `finished`, `run_ended`, …) to `trace.jsonl`
**and** to live SSE subscribers. The web UI renders that stream, the eval harness
reads the same file, and `python -m agent trace <id>` renders it as a timeline. One
artifact, three jobs — so what you watch is exactly what gets scored.

The loop forces a tool call every turn, so the live mid-run feel is event-streaming
at *step* granularity. The one natural-language output — the **final report** —
streams **token-by-token**: `llm.chat` surfaces clean report text from the streaming
`finish` tool-call argument (and streams force-synthesis text directly) via
`report_delta` events that type into the UI panel. `stream` isn't part of the
cassette key, so recorded eval runs still replay byte-identically.

### 8. The web UI (`web/` — React + TypeScript)

The live UI is a small **React + TypeScript** SPA (Vite). The interaction model is
mine to choose; I used TS to make the **trace the single typed contract end-to-end**:
`web/src/types.ts` is a discriminated union of `TraceEvent` that mirrors the backend
`tracer.py`, and the whole app is a reducer that `switch`es on `ev.type` (so adding
or removing a backend event is a compile-time-checked change on both sides — the type
checker caught a real bug while I built it). It's deliberately tiny: one screen, no
router, no state library — `useReducer` over an `EventSource`, ~5 components
(`RunControls`, `PlanPanel`, `TraceTimeline`, `FindingsPanel`, `ReportPanel`).

**No Node needed to run it:** Vite builds into `server/static/` and the compiled
bundle is committed, so `uvicorn server.app:app` serves the SPA as-is. To work on
the frontend:

```bash
cd web && npm install
npm run dev        # Vite dev server on :5173, proxies /run + /events to FastAPI :8000
npm run build      # typecheck + emit the committed bundle into ../server/static
```

The one honest cost of this choice: a `node_modules`/build step now exists for UI
*development* (the runtime doesn't need it). The CLI remains the primary harness
demo; the SPA is the observability layer.

---

## Where deepagent sits in the loop stack

An agent is loops nested inside loops. From the inside out: the **token loop**
(the model decoding, ~seconds), the **agent turn** (one tool call → observe,
~minutes), the **goal loop** (run → judge → retry until the goal is met, ~hours),
the **meta-loop** (spawning and reviewing other agents, ~days), and an open-ended
**goal-setting loop**.

deepagent builds and hardens **loops 1–3**. Loop 2 is my control loop (one tool
call per step); loop 3 is the fresh-context critic — "judge: off-goal → revise" is
the run reopening, "judge: goal met" is acceptance. I deliberately stop there.
Loops 4–5 (multi-agent orchestration, autonomous goal-setting) are where the
brief's "keep it simple" says don't go, so I didn't.

The framing also names my bias: early on, the valuable skill is knowing when to go
**down** a loop when things go wrong (reliability) — the critic dropping back into
the worker, a budget breach dropping to a grounded partial. Going **up** a loop
(more agents, more autonomy) buys leverage, but it's the wrong trade for a small,
reliability-graded task. deepagent is a down-the-stack reliability story by design.

---

## Quickstart

```bash
# 1. install
python -m venv .venv
.venv/Scripts/activate            # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

# 2. configure keys
cp .env.example .env              # set OPENAI_API_KEY + TAVILY_API_KEY

# 3a. run headless (CLI)
python -m agent run "Compare the carbon-capture approaches of Climeworks, Charm Industrial, and Heirloom"

# 3b. run with the live web UI (React+TS SPA; pre-built bundle is committed)
python -m uvicorn server.app:app --port 8000   # open http://localhost:8000
#    (no Node needed — server/static ships the compiled bundle)

# 4. run the evaluation harness
python -m eval run                # all tasks: deterministic checks + trajectory metrics + LLM judge
LLM_MODE=replay python -m eval run   # offline & free, from committed cassettes

# 5. inspect / control a run
python -m agent trace <run_id> [--verbose]
python -m agent resume <run_id>
touch runs/<run_id>/AGENT_STOP    # graceful kill; echo guidance > runs/<id>/STEER.md to steer
```

Every run writes artifacts to `runs/<run_id>/`: `state.json`, `trace.jsonl`,
`pages/*.txt` (full page text, kept out of the prompt), and `notes/*.txt`.

---

## Example run

A real task, start to finish, committed under [`examples/tavily-api/`](examples/tavily-api) —
the fault-injection task, where the **first `fetch_url` is forced to fail**:

> *What is the Tavily API, what are its main features, and how is it priced?*

- **`report.md`** — the final cited report.
- **`trace.jsonl`** — every event, the same stream the UI renders and the eval reads.
- **`state.json`** — the final structured state (plan, findings, sources).

What to look at (visible in the trace): the **first fetch fails** and becomes an `ERROR`
observation, and the agent **re-searches and recovers**; search → fetch → record cycles
produce grounded findings; and the **fresh-context critic in action** — two `verify_failed`
events where the cold reviewer rejected the draft, then the agent revised and finished
(`verify_retries = 2`). Replay it as a readable timeline:

```bash
LLM_MODE=replay python -m eval run --task tavily-api   # regenerates runs/eval-tavily-api/
python -m agent trace eval-tavily-api                  # render it step by step
```

---

## Evaluation harness (`eval/`)

`python -m eval run` runs the agent on a fixed task set and scores each run three
ways:

- **Deterministic checks** (`eval/checks.py`), no LLM: completed? produced a report?
  cited ≥ `min_sources` *distinct fetched* sources? **no fabricated citations**?
  within step budget? **critic accepted the claims**? plus per-scenario checks —
  recovered from a forced fetch failure, and **no false success when no sources
  exist**. **Skill (legal) tasks** swap the web-citation checks for skill-appropriate
  ones (engaged the right pipeline, disclaimer present, unknowns marked `[BLANK]`).
- **Trajectory metrics** (`eval/harness.py`, derived from the trace): the "how it
  got there" signal — `tool_error_rate`, `replans`, `nudges_by_kind`,
  `verify_retries`, `compactions`.
- **LLM-as-judge** (`eval/judge.py`): answer quality, 1–5 on relevance, grounding,
  completeness, coherence.

The harness evaluates at two loop levels: the **goal loop** (did the critic/judge
accept the result — `claims_verified`, judge scores) and the **agent-turn loop**
(was the trajectory sound — `tool_error_rate`, `replans`, `nudges`). End-state and
path, not just the final answer.

**Replayable & offline.** The LLM client and the `web_search`/`fetch_url` tools each
have a cassette layer. Record once with `LLM_MODE=record`; then `LLM_MODE=replay`
reruns the whole suite deterministically with no network and no cost. Cassettes are
**write-once** (record never clobbers), which is what makes replay reproduce a
recorded run exactly.

### Results

Latest run — model **`gpt-5.1`** for agent, summaries, and judge
(`eval/results/20260629-170728.json`), reproducible offline with
`LLM_MODE=replay python -m eval run`:

| Task | Steps | Findings | Replans | Checks | VRetry | Judge avg |
|------|------:|---------:|:------:|:------:|:------:|:---------:|
| carbon-capture | 19 | 2 | 2 | **5/6** | 2 | 4.75 |
| llm-long-context | 20 | 1 | 4 | **5/6** | 2 | 3.75 |
| rust-vs-go | 18 | 1 | 4 | **5/6** | 1 | 3.75 |
| tavily-api *(fault: fetch fails)* | 19 | 3 | 2 | **6/7** | 2 | 4.75 |
| alzheimers-treatments | 19 | 1 | 12 | **4/6** | 2 | 4.25 |
| spacex-falcon1 | 20 | 1 | 3 | **5/6** | 2 | 3.75 |
| no-sources-available *(fault: no results)* | 20 | 0 | 7 | 6/6 | 0 | 3.25 |

**Deterministic checks: 36/43 · Mean judge score: 4.04 / 5.** The fault task still
**recovered** and the **no-sources** task still refused to fabricate; the **critic
fired on 6 of 7 tasks** (`VRetry`). Failures cluster in two checks: `cited≥N`
(several reports cite only 1 source) and `claims_verified` (the critic's issues
weren't fully resolved within the retry budget).

> **This is an eval-driven model finding, not a happy number.** `gpt-5.1` is the
> best base model on this key, but on *this* harness it scores **lower** than
> `gpt-4.1-mini` did (36/43 · 4.04 vs **41/43 · 5.0**). Why: it **over-deliberates
> and under-collects** — it spends its step budget replanning (e.g. **12 replans**
> on `alzheimers`) instead of fetching/recording, so it gathers fewer findings and
> cites fewer sources; and the gpt-5.1 critic is stricter, leaving outstanding
> issues. The loop, step budget, and cadence nudges were tuned for `gpt-4.1-mini`.
> I run `gpt-5.1` as the strongest base model and let the eval state the trade-off
> openly; the fix is to tune the loop for a reasoning model (next section).

### Legal-skill eval (the `paralegal` pipelines)

The harness also evaluates the **skill** path: four tasks run with `SKILLS_ENABLED`
and are scored by **skill-appropriate checks** instead of web-citation ones — a
legal draft has no sources to cite, so success is: *engaged the right pipeline*
(`used_skill` + `loaded_pipeline`), *attorney-review disclaimer present*, *unknowns
marked `[BLANK]`/`[TBD]` rather than invented*, and the *critic accepted the skill's
validation checklist*. The harness flips `SKILLS_ENABLED` per task, so the research
runs above stay byte-identical.

| Legal task | Pipeline | Steps | Checks | VRetry |
|------------|----------|------:|:------:|:------:|
| legal-nda-draft | A · contract-draft | 17 | **7/9** | 2 |
| legal-contract-review | B · contract-review | 10 | 8/9 | 2 |
| legal-ads-offer-letter | G · ADS / Pakistan law | 14 | **9/9** | 1 |
| legal-lease-amendment | C · lease-amendment | 19 | 8/9 | 2 |

All four **engaged the correct pipeline, marked unknowns, and (3 of 4) included the
disclaimer**; the recurring miss is `claims_verified` — the gpt-5.1 critic, now
enforcing the skill's *validation checklist*, leaves an issue or two — plus one
disclaimer omission on the NDA draft (a real finding: the agent sometimes relies on
the `.docx` export, which force-prepends the disclaimer, and omits it from the report
body). Combined with research: **68/79 deterministic checks**, reproducible offline.

> **An eval that drove a fix.** The first legal runs showed the model inventing
> reference filenames (`nda-mutual-draft.md`, `offer-letter-standard.md`) and wasting
> a step on the error each time. Prompt guidance alone didn't stop it, so
> `read_reference` now keyword-aliases an invented name to the correct pipeline
> (transparently noted). After the fix: **zero reference errors** and faster legal
> runs (`contract-review` 15→10 steps, `ads-offer-letter` 8/9→9/9).

### What I learned

- **A stronger base model is not automatically a better agent.** The eval's whole
  point: swapping in `gpt-5.1` *dropped* the score because our loop rewards acting
  (search→fetch→record) and the reasoning model prefers to plan. The harness turned
  a vibe ("use the best model") into a measured trade-off. The fix is loop-side:
  raise the step budget for reasoning models, add stronger "act, don't re-plan"
  pressure, and cap consecutive replans.
- **The fresh-context critic earns its keep.** `verify_retries` fired on 6 of 7
  tasks — the worker produced a draft a cold reviewer rejected, then revised.
  Catching that *before* completion is the single highest-signal guard.
- **Citation completeness is the stubborn weakness**, and worse under gpt-5.1: most
  reports cite only 1 distinct source. The right fix is a `finish` gate on
  **distinct sources cited**, not just findings recorded.
- **Deterministic replay is keyed to the model + subtle to get right.** The cassette
  key includes the model, so a model swap requires a re-record (as here). And
  hashing the full prompt is fragile because it embeds LLM-generated summaries —
  **write-once cassettes** made record/replay byte-identical.

---

## Key decisions & trade-offs

- **Stateless LLM calls + reconstructed context** instead of the multi-turn
  tool-message protocol. This is the most important choice: it bounds context growth
  and makes each step independently inspectable, at the cost of not relying on the
  provider's implicit conversation memory.
- **One tool call per step** — simpler, cleaner traces, easier adaptation than
  parallel calls; a small throughput cost for a big observability win.
- **Grounding enforced in code, not prompts** — `record_finding`/`finish`/critic make
  fabrication actually fail rather than merely discouraged.
- **Trace as the single source of truth** for the UI and the eval, so the demo and
  the score can't drift apart.
- **FastAPI + one static page**, no frontend build — the fastest path to good live
  observability.

### What I deliberately left out (and why)

The brief rewards *the simplest harness that works* and penalises unjustified
complexity, so I chose **not** to build:

- **An event-sourcing rewrite.** `state.json` (a fold persisted every step) already
  gives correct, crash-safe resume; an append-only event log would be machinery the
  task doesn't need.
- **Separate planner/worker/critic *services* or a multi-agent fan-out.** Planning
  stays the `update_plan` tool inside the one loop, and the critic is one extra
  stateless call — not a third process.
- **A vector store, git-per-run, or a provider swap.** None would move the grade.
- **A read-only research sub-agent** is the one place more machinery could plausibly
  help; it's off by default because it risks the core for a ~15× token cost. It's
  the first thing on the roadmap.

This restraint is a deliberate choice, not an omission — a finished, narrow agent
beats an ambitious half-built one.

### How I spent my time (and what I traded off)

Roughly in priority order, matching where the brief puts the weight:

- **Most of it on the loop + robustness** (40% of the grade): the control loop,
  bounded state-as-context + compaction, the grounding gates, the fresh-context
  critic, budgets, stall/cadence nudges, resume/reorientation, and the retry/backoff
  + schema-validated I/O. This is where long runs live or die.
- **A solid chunk on the eval harness** (30%): the cassette record/replay layer (so
  it runs offline and reproducibly), deterministic checks, trajectory metrics, the
  LLM judge — and actually *using* it, which is what surfaced the model and
  citation-completeness findings.
- **Deliberately little on the UI:** the React+TS SPA is a thin observability layer
  over the trace, not a product. The CLI is the primary harness.
- **The legal skill is an optional extension**, gated off by default so it never
  touches the research loop or its cassettes.

**Trade-offs I made on purpose:** depth on reliability + eval over breadth of
features; single-threaded over multi-agent; grounding enforced in code over trusting
prompts; and I left the *distinct-sources `finish` gate* and the read-only sub-agent
unbuilt because the eval shows the first is the higher-value next step. If I had the
marginal hour back, I'd spend it there and on tuning the loop for a reasoning model —
because the eval, not a hunch, says those are the live weaknesses.

---

## What I'd do with more time

Near-term, within this architecture:

- A **distinct-sources `finish` gate** (cite ≥ N distinct fetched sources, not just
  record N findings) — the fix for the one recurring eval miss.
- A **contradictory-sources** eval scenario (two sources disagree → assert the agent
  surfaces the conflict instead of silently picking one), and a larger task set with
  inter-rater judge averaging.
- **Source dedup / domain-trust weighting** before fetching, and **adversarial
  finding verification** (a second model tries to refute each finding).

Longer-term — the "v3" direction, where the harness grows up into a platform:

- **An optional read-only sub-agent**: fan out one isolated researcher per broad
  sub-question, each returning a ≤1–2k-token condensed summary into the ledger
  (Cognition's one endorsed use of sub-agents), with the token-cost trade-off
  documented and the feature off by default.
- **Event-sourced state** (append-only `events.jsonl` + git-checkpointed run dirs)
  if runs ever need a fully diffable, replayable audit trail beyond the current
  `state.json` + `trace.jsonl`.
- **Cross-run memory** via a vector store for within-run semantic recall of findings
  and reuse across tasks.
- A **rubric-based critic** (functionality / coverage / source-quality / clarity with
  few-shot anchors) instead of binary accept/reopen, and **browser-verified
  sourcing** where the critic re-opens a couple of cited URLs itself.

### Production direction: a shared-document VFS + an orchestrator

With a production mindset, the natural next step is to let agents collaborate on
**one artifact** rather than pass strings around, and to make the main agent an
**orchestrator** rather than a worker. Two pieces that reinforce each other:

- **A virtual filesystem (VFS) so agents work on a single document.** Today the
  agent's working memory is structured state plus `notes/` and `pages/` files.
  Production-scale, I'd promote that to a proper VFS: the report (or contract) is a
  single, versioned document that the loop — and any sub-agents — read and **patch**
  through file operations, instead of regenerating prose each turn. That buys a
  single source of truth, partial edits, a diffable history of *who changed what*,
  and concurrency-safe collaboration. It's the "filesystem" pillar from Anthropic's
  long-running-agent work, done durably.
- **One orchestrator spawning read-only/scoped sub-agents.** The main agent does no
  real work — it decomposes the goal, spawns **fresh-context** sub-agents (each with
  "necessary and sufficient" context and the right model tier for the job), reviews
  their condensed results, and respawns as needed. This keeps the orchestrator's
  context lean and gives every sub-agent a fresh set of eyes, avoiding bias and
  context rot.

The pairing is the point: **the VFS is what makes the orchestrator pattern safe.**
Sub-agents collaborate by reading and writing the one shared document — with diffs
and an audit trail — not by stitching strings together. The orchestrator sequences
the edits, the fresh-context critic still gates the result, and `trace.jsonl` keeps
the whole multi-agent run observable. Crucially I'd ship this **measured** — the
orchestrated mode benchmarked against the single-threaded baseline on tokens,
latency, and judge score — so the extra machinery has to earn its place rather than
being added on faith. This is loop 3 → loop 4 in the loop-stack, kept honest by the
same grounding, observability, and eval guarantees as the single-threaded core.

### Extending to a compliance / due-diligence workflow

The same harness maps onto regulated knowledge work with little change: the
two-gate grounding + fresh-context critic become an auditable "every assertion
traces to a fetched primary source" guarantee; `trace.jsonl` is a complete,
replayable audit log of what was read and concluded; kill/steer gives a human
reviewer an intervention point; and swapping the web tools for document-store tools
(SEC EDGAR, a contract repository) turns it into a sourced due-diligence or
policy-review assistant whose claims can always be checked against the cited source.

### Skills (optional, `SKILLS_ENABLED=1`)

A Claude-style **skills** layer makes that concrete. A skill is a `SKILL.md` router
(name + description) plus detailed reference pipelines, loaded by progressive
disclosure — exactly the notes/pages strategy: `list_skills` → `use_skill(name)`
(loads the router) → `read_reference(name, path)` (pulls in ONE pipeline, capped,
out of the rolling prompt). A shipped **`paralegal`** skill (`skills/`) has seven
legal drafting/review pipelines; `export_docx` renders a finished draft to an
attorney-review `.docx`, and the fresh-context critic enforces the skill's
validation checklist.

```bash
SKILLS_ENABLED=1 python -m agent run \
  "Draft a mutual NDA between Acme Corp and Beta LLC under Washington law; export a .docx"
```

Two deliberate design points: skill tools are **gated off by default** so the
research loop and its eval cassettes are untouched; and `finish`'s
web-source requirement is **mode-aware** (a legal draft has no URLs — anti-fabrication
still applies, but the skill checklist + critic stand in for web grounding). Honest
caveat: deepagent is at heart a research agent, so the natural split is the research
loop for legal-*research* questions and the skill pipelines for drafting/review of a
provided document.

---

## Project structure

```
agent/
  loop.py        control loop (plan→act→observe→adapt; budgets, nudges, critic gate,
                 compaction, reorient, kill/steer, force-synthesis)
  state.py       ResearchState dataclass + JSON persistence + resume
  context.py     bounded prompt reconstruction from state (compaction-aware)
  compaction.py  collapse older findings into a digest
  verifier.py    fresh-context critic that gates completion (skill-checklist aware)
  skills.py      skill discovery + loaders (SKILL.md router, JIT references)
  docx.py        dependency-free .docx writer (attorney-review export)
  prompts.py     SYSTEM, SYNTHESIS, CRITIC, REORIENT, SKILLS_ADDENDUM
  llm.py         OpenAI wrapper: tool calls, token accounting, jittered retry, cassettes
  cache.py       record/replay cassettes for web_search + fetch_url (offline eval)
  tracer.py      structured events → trace.jsonl + live SSE pub/sub
  config.py      budgets, models, knobs, keys (env-driven)
  cli.py         python -m agent run | resume | trace
  tools/         web_search, fetch_url, update_plan, record_finding,
                 write_note, read_note, finish + skill_tools (gated)
server/
  app.py         FastAPI: POST /run, GET /events/{id} (SSE), GET /, /assets mount
  static/        committed React+TS build (index.html + assets/) — served as-is
web/             React + TypeScript SPA source (Vite); builds into server/static
  src/types.ts   TraceEvent union mirroring tracer.py (one typed contract)
  src/state.ts   useReducer over the event stream      src/api.ts  SSE client
  src/components/  RunControls · PlanPanel · TraceTimeline · FindingsPanel · ReportPanel
eval/
  tasks.py checks.py judge.py harness.py   runnable eval + scorecard + trajectory metrics
  cassettes/ results/                       committed: offline replay + scorecard
skills/            paralegal skill: SKILL.md router + 7 reference pipelines
tests/             core-loop + robustness + skills tests (mocked LLM + network)
examples/          a real run committed for inspection (the Example Run deliverable)
runs/              per-run state.json + trace.jsonl + pages/ + notes/ (git-ignored)
build_sessions/    raw, unedited AI build-session logs (how this was built)
```

---

## Note on "no frameworks"

`fastapi`/`uvicorn` are a web server, `trafilatura` is an HTML→text extractor,
`openai`/`requests` are clients, `tiktoken` counts tokens. None of them orchestrate
the agent. The loop, the planning, the context-window management, the tool dispatch,
and the prompts are all in this repo.
