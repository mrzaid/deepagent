# Build session logs

Raw, **unedited** Claude Code session transcripts from building this project —
exported verbatim (byte-for-byte; sha256 verified) so you can see how the work was
actually done. These are JSONL conversation logs (one JSON event per line: user
messages, assistant turns, tool calls, and tool results).

Two sessions, in chronological order:

| File | When | What happened |
|---|---|---|
| `b1c461f2-63d4-4ef0-b267-2f0a7ff83944.jsonl` | session 1 | Planning, git/GitHub setup, initial build (loop, tools, state, tracer, web UI, eval harness), offline-replay cassette layer, first live eval + example run, and the deepagents-inspired scratchpad/cadence upgrade. |
| `05266f0b-4856-4a89-a57b-e4f74e3ba030.jsonl` | session 2 | Robustness & eval hardening (the WI-1..WI-9 plan): fresh-context critic, context compaction, wall-clock budget, jittered retry, trajectory metrics + scenarios, resume reorientation, `trace` CLI, kill switch/steering, dedup; re-record + replay verification; CHANGELOG; this export. |

Notes:
- **Not edited.** Filenames are the original Claude Code session IDs. The only
  added file in this directory is this README.
- The second log is a snapshot taken near the end of session 2, so it does not
  include the final turn that performed the export itself.
- Scanned for secrets before export — no API keys or tokens appear in the logs
  (keys lived only in a git-ignored `.env`, never printed to the session).

To read one, e.g. pretty-print the events:
`python -c "import json,sys; [print(json.loads(l).get('type','?')) for l in open('build_sessions/05266f0b-4856-4a89-a57b-e4f74e3ba030.jsonl',encoding='utf-8')]"`
