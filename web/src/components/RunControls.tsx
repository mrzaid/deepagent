import { useState, type FormEvent } from "react";
import type { RunOpts } from "../api";

export default function RunControls({
  disabled,
  onRun,
  onClear,
}: {
  disabled: boolean;
  onRun: (goal: string, opts: RunOpts) => void;
  onClear: () => void;
}) {
  const [goal, setGoal] = useState("");
  const [fault, setFault] = useState(false);
  const [maxSteps, setMaxSteps] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    const g = goal.trim();
    if (!g) return;
    const opts: RunOpts = {};
    if (fault) opts.fault = "fail_first_fetch";
    const n = parseInt(maxSteps, 10);
    if (n > 0) opts.maxSteps = n;
    onRun(g, opts);
  }

  function clear() {
    setGoal("");
    setFault(false);
    setMaxSteps("");
    onClear();
  }

  return (
    <form onSubmit={submit}>
      <input
        type="text"
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        placeholder="Ask a research question, e.g. Compare the carbon-capture approaches of 3 startups"
      />
      <label>
        <input type="checkbox" checked={fault} onChange={(e) => setFault(e.target.checked)} /> inject fetch fault
      </label>
      <label>
        max steps
        <input type="number" min={1} value={maxSteps} onChange={(e) => setMaxSteps(e.target.value)} placeholder="20" />
      </label>
      <button type="submit" disabled={disabled}>
        {disabled ? "Running…" : "Research"}
      </button>
      <button type="button" className="secondary" onClick={clear} title="Clear the view and start fresh">
        New
      </button>
    </form>
  );
}
