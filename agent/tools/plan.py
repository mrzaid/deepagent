"""update_plan tool: set or replace the plan. Planning is an explicit,
observable tool call (not hidden chain-of-thought), so the trace and UI show
exactly when and how the agent re-plans."""
from __future__ import annotations

from dataclasses import asdict

from ..state import PlanStep


def _render(plan: list[PlanStep]) -> str:
    mark = {"done": "[x]", "active": "[>]", "dropped": "[-]", "pending": "[ ]"}
    return "\n".join(f"{mark.get(p.status, '[ ]')} {p.id}. {p.text}" for p in plan)


def update_plan(args: dict, state, tracer) -> str:
    steps = args.get("steps")
    if not isinstance(steps, list) or not steps:
        raise RuntimeError("update_plan requires a non-empty list 'steps'")

    first = not state.plan
    new_plan: list[PlanStep] = []
    for i, s in enumerate(steps, 1):
        if isinstance(s, dict):
            new_plan.append(PlanStep(id=i, text=str(s.get("text", "")).strip(),
                                     status=s.get("status", "pending")))
        else:
            new_plan.append(PlanStep(id=i, text=str(s).strip()))
    state.plan = new_plan

    tracer.emit("plan_created" if first else "plan_revised",
                {"plan": [asdict(p) for p in new_plan]})
    return ("Plan set:\n" if first else "Plan revised:\n") + _render(new_plan)
