import { useEffect, useReducer, useRef } from "react";
import { startRun, subscribe, type RunOpts } from "./api";
import { reducer } from "./state";
import { initialState } from "./view";
import type { TraceEvent } from "./types";
import RunControls from "./components/RunControls";
import PlanPanel from "./components/PlanPanel";
import FindingsPanel from "./components/FindingsPanel";
import TraceTimeline from "./components/TraceTimeline";
import ReportPanel from "./components/ReportPanel";

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const esRef = useRef<EventSource | null>(null);

  // close the stream on unmount
  useEffect(() => () => esRef.current?.close(), []);

  async function run(goal: string, opts: RunOpts) {
    esRef.current?.close();
    dispatch({ kind: "reset", goal });
    try {
      const runId = await startRun(goal, opts);
      esRef.current = subscribe(runId, (ev) => dispatch({ kind: "event", ev }));
    } catch (e) {
      const err: TraceEvent = { seq: 0, ts: 0, type: "error", data: { msg: String(e) } };
      dispatch({ kind: "event", ev: err });
    }
  }

  // Clear the view back to idle and stop watching the current run (the server-side
  // run, if any, keeps going in the background and can be re-attached by run_id).
  function clear() {
    esRef.current?.close();
    esRef.current = null;
    dispatch({ kind: "clear" });
  }

  const running = state.phase === "live";
  return (
    <div className="app">
      <header>
        <h1>deepagent</h1>
        <span className="sub">long-running research agent · live trace</span>
      </header>
      <main className="wrap">
        <RunControls disabled={running} onRun={run} onClear={clear} />

        <div className={`status ${state.phase}`}>
          <span className="dot" />
          <span>{state.status}</span>
          {state.activeSkill && <span className="skill">skill: {state.activeSkill}</span>}
        </div>

        <div className="cols">
          <div>
            <PlanPanel plan={state.plan} />
            <FindingsPanel findings={state.findings} />
          </div>
          <TraceTimeline items={state.timeline} />
        </div>

        <ReportPanel report={state.report} streaming={state.reportStreaming} />
      </main>
    </div>
  );
}
