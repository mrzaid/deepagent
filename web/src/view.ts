import type { Finding, PlanStep } from "./types";

// Timeline items preserve arrival order, interleaving step cards with markers.
export interface StepItem {
  kind: "step";
  n: number;
  tool?: string;
  args?: string;
  ok?: boolean;
  obs?: string;
}

export interface MarkerItem {
  kind: "marker";
  cls: "nudge" | "info";
  text: string;
}

export type TimelineItem = StepItem | MarkerItem;

export interface UIState {
  runId: string | null;
  status: string;
  phase: "idle" | "live" | "done";
  goal: string;
  activeSkill: string | null;
  plan: PlanStep[];
  findings: Finding[];
  timeline: TimelineItem[];
  report: string;
  reportStreaming: boolean;
}

export const initialState: UIState = {
  runId: null,
  status: "Idle — enter a goal to begin.",
  phase: "idle",
  goal: "",
  activeSkill: null,
  plan: [],
  findings: [],
  timeline: [],
  report: "",
  reportStreaming: false,
};
