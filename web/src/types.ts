// One typed contract end-to-end: this discriminated union mirrors the events
// emitted by the backend `agent/tracer.py`. The whole UI is "switch on ev.type",
// so adding/removing a backend event is a compile-time-checked change here too.

export type PlanStatus = "pending" | "active" | "done" | "dropped";

export interface PlanStep {
  id: number;
  text: string;
  status: PlanStatus;
}

export interface Finding {
  claim: string;
  source_url: string;
  quote: string;
  step: number;
  index?: number;
}

interface Base {
  seq: number;
  ts: number;
}

export type TraceEvent = Base &
  (
    | { type: "run_started"; data: { goal: string; run_id: string; step_budget: number } }
    | { type: "plan_created" | "plan_revised"; data: { plan: PlanStep[] } }
    | { type: "step_started"; data: { step: number } }
    | { type: "tool_call"; data: { step: number; tool: string; args: Record<string, unknown> } }
    | { type: "observation"; data: { step: number; tool: string | null; ok: boolean; observation: string } }
    | { type: "finding_recorded"; data: Finding }
    | { type: "note_written"; data: { name: string; chars: number; overwrote: boolean } }
    | { type: "nudge"; data: { step: number; kind: string } }
    | { type: "compaction"; data: { findings_digested: number; digest_chars: number } }
    | { type: "verify_started"; data: { findings: number; skill?: string | null } }
    | { type: "verify_result"; data: { n_issues: number; issues?: unknown[] } }
    | { type: "verify_failed"; data: { retry: number; n_issues: number } }
    | { type: "verify_exhausted"; data: { n_issues: number } }
    | { type: "steer_injected"; data: { chars: number } }
    | { type: "reoriented"; data: { text: string } }
    | { type: "budget_event"; data: { kind: string } }
    | { type: "force_synthesis"; data: { findings: number } }
    | { type: "report_delta"; data: { text: string } }
    | { type: "finished"; data: { report: string; sources_cited: string[]; num_findings: number } }
    | {
        type: "run_ended";
        data: {
          status: string;
          done: boolean;
          steps: number;
          findings: number;
          sources_fetched?: number;
          nudges?: number;
          verify_retries?: number;
          compactions?: number;
        };
      }
    | { type: "skills_listed"; data: { count: number } }
    | { type: "skill_loaded"; data: { name: string; checklist_chars: number } }
    | { type: "reference_read"; data: { skill: string; path: string; chars: number } }
    | { type: "docx_exported"; data: { path: string; bytes: number } }
    | { type: "error"; data: { where?: string; msg: string } }
  );

export type EventType = TraceEvent["type"];
