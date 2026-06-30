# Build session logs

Raw, unedited Claude Code session transcripts from building this project, exported
verbatim so the work is fully traceable. Each file is a JSONL conversation log — one
JSON event per line (user messages, assistant turns, tool calls, tool results).

| File | Session | Scope |
|---|---|---|
| `b1c461f2-63d4-4ef0-b267-2f0a7ff83944.jsonl` | 1 | Initial build: agent loop, tools, state, tracer, web UI, eval harness, offline-replay cassettes, first live eval, and the scratchpad/cadence upgrade. |
| `05266f0b-4856-4a89-a57b-e4f74e3ba030.jsonl` | 2 | Robustness & eval hardening: fresh-context critic, context compaction, wall-clock budget, jittered retry, trajectory metrics, resume reorientation, `trace` CLI, kill switch/steering, and dedup. |

Notes:
- Unedited. Filenames are the original Claude Code session IDs; this README is the
  only added file.
- The session-2 log is a snapshot taken near the end of that session, so it omits the
  final turn that performed the export itself.
- Scanned for secrets before export — no API keys or tokens appear; credentials lived
  only in a git-ignored `.env` and were never printed to the session.

To list the event types in a log:

```bash
python -c "import json; [print(json.loads(l).get('type','?')) for l in open('build_sessions/05266f0b-4856-4a89-a57b-e4f74e3ba030.jsonl', encoding='utf-8')]"
```
