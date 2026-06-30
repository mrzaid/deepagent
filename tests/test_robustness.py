"""Offline tests for the WI-1..WI-9 robustness features. Mock the LLM + network so
they run with no API keys, no network, and are fully deterministic.

Covered: fresh-context critic (retry + exhaust + pass), context compaction,
wall-clock budget, kill+resume, operator steering, finding dedup, reorientation.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import config, llm, loop                       # noqa: E402
from agent.llm import LLMResponse, ToolCall               # noqa: E402
import agent.tools.search as search                       # noqa: E402
import agent.tools.fetch as fetch                         # noqa: E402
from agent.state import ResearchState, Finding            # noqa: E402
from agent.context import build_context                   # noqa: E402
from agent.compaction import maybe_compact                # noqa: E402
from agent.tracer import Tracer, read_trace               # noqa: E402


def _mock_network():
    search._tavily = lambda q, n: [
        {"title": "Example A", "url": "https://example.com/a", "content": "X is true."},
    ]

    class _Resp:
        def __init__(self, text): self.text = text
        def raise_for_status(self): pass

    fetch.requests.get = lambda url, headers=None, timeout=None: _Resp(
        "<html><head><title>Page</title></head><body><p>X is true because reasons.</p></body></html>")
    # plain-text summary -> verifier _parse returns {} -> deterministic fallback path
    llm.simple = lambda system, user, model=None, temperature=0.0, **kw: LLMResponse(content="summary", usage={"total_tokens": 5})


def _scripted(script):
    st = {"i": 0}

    def fake_chat(messages, tools=None, tool_choice=None, model=None, temperature=0.0, max_retries=4, **kwargs):
        i = st["i"]; st["i"] += 1
        if i < len(script):
            name, args = script[i]
            return LLMResponse(tool_calls=[ToolCall(id=f"c{i}", name=name, args=args)], usage={"total_tokens": 50})
        return LLMResponse(tool_calls=[ToolCall(id="cx", name="web_search", args={"query": "more"})], usage={"total_tokens": 50})

    return fake_chat


def _clean(rid):
    shutil.rmtree(config.RUNS_DIR / rid, ignore_errors=True)


# ---- WI-1 critic --------------------------------------------------------
def test_critic_passes_when_findings_have_quotes():
    _mock_network()
    llm.chat = _scripted([
        ("update_plan", {"steps": [{"text": "q"}]}),
        ("fetch_url", {"url": "https://example.com/a"}),
        ("record_finding", {"claim": "X is true", "source_url": "https://example.com/a", "quote": "X is true"}),
        ("finish", {"report": "X [1].\n\n## Sources\n[1] A — https://example.com/a"}),
    ])
    _clean("t-critic-pass")
    st = loop.run("g", run_id="t-critic-pass", max_steps=10)
    ev = read_trace("t-critic-pass")
    assert st.done
    assert any(e["type"] == "verify_result" and e["data"]["n_issues"] == 0 for e in ev)
    assert not any(e["type"] == "verify_failed" for e in ev)
    _clean("t-critic-pass")


def test_critic_rejects_unsupported_then_exhausts():
    # finding with an EMPTY quote -> deterministic critic fallback flags it every time
    _mock_network()
    llm.chat = _scripted([
        ("update_plan", {"steps": [{"text": "q"}]}),
        ("fetch_url", {"url": "https://example.com/a"}),
        ("record_finding", {"claim": "X is true", "source_url": "https://example.com/a", "quote": ""}),
        ("finish", {"report": "X [1].\n\n## Sources\n[1] A — https://example.com/a"}),
        ("finish", {"report": "X [1].\n\n## Sources\n[1] A — https://example.com/a"}),
        ("finish", {"report": "X [1].\n\n## Sources\n[1] A — https://example.com/a"}),
    ])
    _clean("t-critic-rej")
    st = loop.run("g", run_id="t-critic-rej", max_steps=12)
    ev = read_trace("t-critic-rej")
    n_failed = sum(1 for e in ev if e["type"] == "verify_failed")
    assert n_failed == config.MAX_VERIFY_RETRIES, f"expected {config.MAX_VERIFY_RETRIES} retries, got {n_failed}"
    assert any(e["type"] == "verify_exhausted" for e in ev)
    assert st.done  # accepted after exhausting retries
    _clean("t-critic-rej")


# ---- WI-2 compaction ----------------------------------------------------
def test_compaction_bounds_findings_render():
    _mock_network()
    _clean("t-compact")
    st = ResearchState.new("goal", run_id="t-compact")
    st.add_source("https://example.com/a", "A").fetched = True
    for i in range(40):
        st.findings.append(Finding(claim=f"claim number {i} with some text", source_url="https://example.com/a", quote="q", step=1))
    st.steps = config.COMPACT_EVERY  # eligible
    tracer = Tracer("t-compact", st.run_dir)
    assert maybe_compact(st, tracer) is True
    msg = build_context(st)[1]["content"]
    assert "[digest of earlier findings" in msg
    assert len(msg) < 4000, f"context not bounded: {len(msg)} chars"
    # all findings remain in state for finish/synthesis
    assert len(st.findings) == 40
    # adding more keeps it flat
    before = len(build_context(st)[1]["content"])
    for i in range(40, 60):
        st.findings.append(Finding(claim=f"claim {i}", source_url="https://example.com/a", quote="q", step=1))
    after = len(build_context(st)[1]["content"])
    assert abs(after - before) < 1500  # roughly flat despite +20 findings
    _clean("t-compact")


# ---- WI-3 wall-clock budget --------------------------------------------
def test_wall_clock_budget_terminates():
    _mock_network()

    class _FakeTime:
        def __init__(self): self.n = 0
        def monotonic(self):
            self.n += 1
            return self.n * 1000.0  # jumps well past any deadline after the first call

    orig_time, orig_budget = loop.time, config.WALL_CLOCK_BUDGET
    loop.time = _FakeTime()
    config.WALL_CLOCK_BUDGET = 1
    try:
        llm.chat = _scripted([("update_plan", {"steps": [{"text": "q"}]})])
        _clean("t-wall")
        st = loop.run("g", run_id="t-wall", max_steps=50)
        ev = read_trace("t-wall")
        assert any(e["type"] == "budget_event" and e["data"]["kind"] == "wall_clock" for e in ev)
        assert st.done  # force-synthesis still produced a (best-effort) report
    finally:
        loop.time, config.WALL_CLOCK_BUDGET = orig_time, orig_budget
    _clean("t-wall")


# ---- WI-8 kill + resume / steering -------------------------------------
def test_kill_switch_then_resume():
    _mock_network()
    _clean("t-kill")
    st = ResearchState.new("g", run_id="t-kill")
    st.persist()
    (st.run_dir / "AGENT_STOP").write_text("", encoding="utf-8")
    llm.chat = _scripted([("update_plan", {"steps": [{"text": "q"}]})])
    aborted = loop.run("", run_id="t-kill", resume=True, max_steps=10)
    ev = read_trace("t-kill")
    assert any(e["type"] == "run_ended" and e["data"].get("status") == "aborted" for e in ev)
    assert not aborted.done and aborted.steps == 0
    # resume to completion (AGENT_STOP was consumed on abort)
    llm.chat = _scripted([
        ("update_plan", {"steps": [{"text": "q"}]}),
        ("fetch_url", {"url": "https://example.com/a"}),
        ("record_finding", {"claim": "X", "source_url": "https://example.com/a", "quote": "X"}),
        ("finish", {"report": "X [1].\n\n## Sources\n[1] A — https://example.com/a"}),
    ])
    done = loop.run("", run_id="t-kill", resume=True, max_steps=10)
    assert done.done
    _clean("t-kill")


def test_operator_steer_injected_once():
    _mock_network()
    _clean("t-steer")
    st = ResearchState.new("g", run_id="t-steer")
    st.persist()
    (st.run_dir / "STEER.md").write_text("prioritise the pricing question", encoding="utf-8")
    llm.chat = _scripted([
        ("update_plan", {"steps": [{"text": "q"}]}),
        ("fetch_url", {"url": "https://example.com/a"}),
        ("record_finding", {"claim": "X", "source_url": "https://example.com/a", "quote": "X"}),
        ("finish", {"report": "X [1].\n\n## Sources\n[1] A — https://example.com/a"}),
    ])
    loop.run("", run_id="t-steer", resume=True, max_steps=10)
    ev = read_trace("t-steer")
    assert any(e["type"] == "steer_injected" for e in ev)
    assert not (st.run_dir / "STEER.md").exists()  # consumed once
    _clean("t-steer")


# ---- WI-6 reorientation -------------------------------------------------
def test_reorient_on_resume():
    _mock_network()
    _clean("t-reorient")
    st = ResearchState.new("g", run_id="t-reorient")
    st.add_source("https://example.com/a", "A").fetched = True
    st.findings.append(Finding(claim="X", source_url="https://example.com/a", quote="X", step=1))
    st.steps = 2
    st.persist()
    llm.chat = _scripted([("finish", {"report": "X [1].\n\n## Sources\n[1] A — https://example.com/a"})])
    loop.run("", run_id="t-reorient", resume=True, max_steps=10)
    ev = read_trace("t-reorient")
    assert any(e["type"] == "reoriented" for e in ev)
    _clean("t-reorient")


# ---- WI-9 dedup ---------------------------------------------------------
def test_record_finding_dedup():
    from agent.tools.findings import record_finding
    _clean("t-dedup")
    st = ResearchState.new("g", run_id="t-dedup")
    st.add_source("https://example.com/a", "A").fetched = True
    tracer = Tracer("t-dedup", st.run_dir)
    record_finding({"claim": "X is true", "source_url": "https://example.com/a", "quote": "q"}, st, tracer)
    record_finding({"claim": "X is true", "source_url": "https://example.com/a", "quote": "q2"}, st, tracer)
    assert len(st.findings) == 1, "duplicate (claim, source) should be skipped"
    _clean("t-dedup")


if __name__ == "__main__":
    for fn in [test_critic_passes_when_findings_have_quotes, test_critic_rejects_unsupported_then_exhausts,
               test_compaction_bounds_findings_render, test_wall_clock_budget_terminates,
               test_kill_switch_then_resume, test_operator_steer_injected_once,
               test_reorient_on_resume, test_record_finding_dedup]:
        fn(); print("PASS", fn.__name__)
    print("\nALL ROBUSTNESS TESTS PASSED")
