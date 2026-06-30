import type { TimelineItem } from "../view";

function StepCard({ it }: { it: Extract<TimelineItem, { kind: "step" }> }) {
  const badge = it.ok === undefined ? "running" : it.ok ? "ok" : "error";
  return (
    <div className={`step ${it.ok === false ? "err" : ""}`}>
      <div className="h">
        Step {it.n} · <span className="tool">{it.tool ?? "…"}</span> <span className={`badge ${badge}`}>{badge}</span>
      </div>
      {it.args && <div className="args">{it.args}</div>}
      {it.obs && <div className="obs">{it.obs}</div>}
    </div>
  );
}

export default function TraceTimeline({ items }: { items: TimelineItem[] }) {
  return (
    <div className="panel">
      <h2>Step timeline</h2>
      {items.length === 0 ? (
        <div className="empty">Steps will stream here.</div>
      ) : (
        items.map((it, i) =>
          it.kind === "step" ? <StepCard it={it} key={i} /> : <div className={`marker ${it.cls}`} key={i}>{it.text}</div>,
        )
      )}
    </div>
  );
}
