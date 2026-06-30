import type { TraceEvent } from "./types";
import { initialState, type StepItem, type TimelineItem, type UIState } from "./view";

export type Action =
  | { kind: "reset"; goal: string } // about to start a run
  | { kind: "clear" } // wipe the view back to idle, no run
  | { kind: "event"; ev: TraceEvent };

function argsToText(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v).slice(0, 80)}`)
    .join(", ");
}

// Update the most recent step card (by step number) immutably.
function patchStep(timeline: TimelineItem[], n: number, patch: Partial<StepItem>): TimelineItem[] {
  for (let i = timeline.length - 1; i >= 0; i--) {
    const it = timeline[i];
    if (it.kind === "step" && it.n === n) {
      const next = timeline.slice();
      next[i] = { ...it, ...patch };
      return next;
    }
  }
  return timeline;
}

function marker(timeline: TimelineItem[], cls: "nudge" | "info", text: string): TimelineItem[] {
  return [...timeline, { kind: "marker", cls, text }];
}

export function reducer(state: UIState, action: Action): UIState {
  if (action.kind === "clear") {
    return initialState;
  }
  if (action.kind === "reset") {
    return { ...initialState, phase: "live", status: "Starting…", goal: action.goal };
  }
  const ev = action.ev;
  switch (ev.type) {
    case "run_started":
      return { ...state, goal: ev.data.goal, runId: ev.data.run_id, phase: "live", status: `Researching: ${ev.data.goal}` };
    case "plan_created":
    case "plan_revised":
      return { ...state, plan: ev.data.plan };
    case "step_started":
      // a fresh draft may stream during this step, so clear the report buffer
      return { ...state, report: "", reportStreaming: false, timeline: [...state.timeline, { kind: "step", n: ev.data.step }] };
    case "tool_call":
      return { ...state, timeline: patchStep(state.timeline, ev.data.step, { tool: ev.data.tool, args: argsToText(ev.data.args) }) };
    case "observation":
      return { ...state, timeline: patchStep(state.timeline, ev.data.step, { ok: ev.data.ok, obs: ev.data.observation }) };
    case "finding_recorded":
      return { ...state, findings: [...state.findings, ev.data] };
    case "report_delta":
      return { ...state, report: state.report + ev.data.text, reportStreaming: true };
    case "finished":
      return { ...state, report: ev.data.report || state.report, reportStreaming: false };
    case "run_ended":
      return {
        ...state,
        phase: "done",
        status: `Done · ${ev.data.steps} steps · ${ev.data.findings} findings · ${ev.data.verify_retries ?? 0} critic retries · ${ev.data.status}`,
      };
    case "nudge":
      return {
        ...state,
        timeline: marker(
          state.timeline,
          "nudge",
          ev.data.kind === "search_without_fetch"
            ? "↻ searching without reading — nudged to fetch a source"
            : "↻ stall detected — nudged to change approach",
        ),
      };
    case "compaction":
      return { ...state, timeline: marker(state.timeline, "info", `⊟ compacted ${ev.data.findings_digested} older findings into a digest`) };
    case "verify_failed":
      return { ...state, timeline: marker(state.timeline, "nudge", `⚖ critic rejected the draft (retry ${ev.data.retry}, ${ev.data.n_issues} issue(s)) — revising`) };
    case "verify_exhausted":
      return { ...state, timeline: marker(state.timeline, "nudge", `⚖ critic still flagged ${ev.data.n_issues} issue(s); accepted after retries`) };
    case "budget_event":
      return { ...state, timeline: marker(state.timeline, "nudge", `⏱ budget reached (${ev.data.kind}) — synthesising`) };
    case "force_synthesis":
      return { ...state, report: "", timeline: marker(state.timeline, "info", "⚙ budget exhausted — synthesising report from findings") };
    case "note_written":
      return { ...state, timeline: marker(state.timeline, "info", `📝 ${ev.data.overwrote ? "updated" : "wrote"} note '${ev.data.name}' (${ev.data.chars} chars)`) };
    case "steer_injected":
      return { ...state, timeline: marker(state.timeline, "info", `⇄ operator steer injected (${ev.data.chars} chars)`) };
    case "reoriented":
      return { ...state, timeline: marker(state.timeline, "info", `🧭 reoriented on resume`) };
    case "skill_loaded":
      return { ...state, activeSkill: ev.data.name, timeline: marker(state.timeline, "info", `🧩 loaded skill '${ev.data.name}'`) };
    case "reference_read":
      return { ...state, timeline: marker(state.timeline, "info", `📚 read ${ev.data.path}`) };
    case "docx_exported":
      return { ...state, timeline: marker(state.timeline, "info", `📄 exported ${ev.data.path}`) };
    case "error":
      return { ...state, timeline: marker(state.timeline, "nudge", `✗ error: ${ev.data.msg}`) };
    default:
      return state;
  }
}
