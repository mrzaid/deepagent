import type { TraceEvent } from "./types";

export interface RunOpts {
  fault?: string;
  maxSteps?: number;
}

// POST /run -> { run_id }. Starts the agent loop server-side (background thread).
export async function startRun(goal: string, opts: RunOpts = {}): Promise<string> {
  const body: Record<string, unknown> = { goal };
  if (opts.fault) body.fault = opts.fault;
  if (opts.maxSteps) body.max_steps = opts.maxSteps;
  const res = await fetch("/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`/run failed: ${res.status}`);
  const json = (await res.json()) as { run_id: string };
  return json.run_id;
}

// Subscribe to the run's SSE trace stream. The server replays history then
// follows live, so a late subscriber still sees the whole run.
export function subscribe(runId: string, onEvent: (ev: TraceEvent) => void): EventSource {
  const es = new EventSource(`/events/${encodeURIComponent(runId)}`);
  es.onmessage = (m: MessageEvent<string>) => {
    try {
      onEvent(JSON.parse(m.data) as TraceEvent);
    } catch {
      /* ignore keep-alives / malformed frames */
    }
  };
  return es;
}
