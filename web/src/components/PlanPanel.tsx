import type { PlanStatus, PlanStep } from "../types";

const MARK: Record<PlanStatus, string> = { done: "[x]", active: "[>]", dropped: "[-]", pending: "[ ]" };

export default function PlanPanel({ plan }: { plan: PlanStep[] }) {
  return (
    <div className="panel">
      <h2>Plan</h2>
      {plan.length === 0 ? (
        <div className="empty">No plan yet.</div>
      ) : (
        <ul className="plan">
          {plan.map((p) => (
            <li key={p.id}>
              <span className={`mark ${p.status}`}>{MARK[p.status] ?? "[ ]"}</span>
              <span>{p.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
