"""Offline tests: mock the LLM and network to exercise the full agent loop with
no API keys and no network. Run with `pytest -q` or `python tests/test_offline.py`.

These cover the behaviours that matter most for a long-running agent: the loop
runs to completion, tracing/persistence happen, grounding is enforced (fabricated
citations are rejected), and the force-synthesis fallback produces a grounded
report when the budget runs out.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import config, llm, loop                      # noqa: E402
from agent.llm import LLMResponse, ToolCall              # noqa: E402
import agent.tools.search as search                      # noqa: E402
import agent.tools.fetch as fetch                        # noqa: E402
from agent.tracer import read_trace                      # noqa: E402


# ---- shared mocks -------------------------------------------------------
def _install_network_mocks():
    search._tavily = lambda q, n: [
        {"title": "Example A", "url": "https://example.com/a", "content": "X is true because reasons."},
        {"title": "Example B", "url": "https://example.com/b", "content": "Y is relevant too."},
    ]

    class _Resp:
        def __init__(self, text): self.text = text
        def raise_for_status(self): pass

    fetch.requests.get = lambda url, headers=None, timeout=None: _Resp(
        f"<html><head><title>Page</title></head><body><p>X is true because reasons.</p></body></html>"
    )


def _scripted_llm(script):
    state = {"i": 0}

    def fake_chat(messages, tools=None, tool_choice=None, model=None, temperature=0.0, max_retries=4, **kwargs):
        i = state["i"]; state["i"] += 1
        if i < len(script):
            name, args = script[i]
            return LLMResponse(tool_calls=[ToolCall(id=f"c{i}", name=name, args=args)],
                               usage={"total_tokens": 50})
        # default once script is exhausted: keep searching (never finishes)
        return LLMResponse(tool_calls=[ToolCall(id="cx", name="web_search", args={"query": "more"})],
                           usage={"total_tokens": 50})

    return fake_chat


def _clean(run_id):
    shutil.rmtree(config.RUNS_DIR / run_id, ignore_errors=True)


# ---- tests --------------------------------------------------------------
def test_happy_path():
    _install_network_mocks()
    llm.simple = lambda system, user, model=None, temperature=0.0, **kw: LLMResponse(content="summary", usage={"total_tokens": 5})
    llm.chat = _scripted_llm([
        ("update_plan", {"steps": [{"text": "Find X"}, {"text": "Find Y"}]}),
        ("web_search", {"query": "what is X"}),
        ("fetch_url", {"url": "https://example.com/a"}),
        ("record_finding", {"claim": "X is true", "source_url": "https://example.com/a", "quote": "X is true"}),
        ("finish", {"report": "# R\n\nX is true [1].\n\n## Sources\n[1] A — https://example.com/a"}),
    ])
    _clean("t-happy")
    st = loop.run("Is X true?", run_id="t-happy", max_steps=10)
    assert st.done
    assert len(st.findings) == 1
    assert "example.com/a" in st.final_report
    seen = {e["type"] for e in read_trace("t-happy")}
    assert {"run_started", "plan_created", "tool_call", "observation",
            "finding_recorded", "finished", "run_ended"} <= seen
    _clean("t-happy")


def test_fabricated_citation_rejected():
    _install_network_mocks()
    llm.simple = lambda system, user, model=None, temperature=0.0, **kw: LLMResponse(content="summary", usage={"total_tokens": 5})
    llm.chat = _scripted_llm([
        ("update_plan", {"steps": [{"text": "q"}]}),
        ("fetch_url", {"url": "https://example.com/a"}),
        ("finish", {"report": "Claim [1].\n\n## Sources\n[1] Fake — https://fabricated.example/zzz"}),
        ("record_finding", {"claim": "X", "source_url": "https://example.com/a", "quote": "x"}),
        ("finish", {"report": "Claim [1].\n\n## Sources\n[1] A — https://example.com/a"}),
    ])
    _clean("t-ground")
    st = loop.run("ground check", run_id="t-ground", max_steps=10)
    obs = [e for e in read_trace("t-ground") if e["type"] == "observation"]
    assert any("fabrication" in e["data"].get("observation", "") for e in obs)
    assert st.done and "example.com/a" in st.final_report
    _clean("t-ground")


def test_force_synthesis_on_budget_exhaustion():
    _install_network_mocks()

    def simple_router(system, user, model=None, temperature=0.0, **kw):
        if "FINAL research report" in system:
            return LLMResponse(content="# Forced\n\nX [1].\n\n## Sources\n[1] A — https://example.com/a",
                               usage={"total_tokens": 20})
        return LLMResponse(content="summary", usage={"total_tokens": 5})

    llm.simple = simple_router
    llm.chat = _scripted_llm([
        ("update_plan", {"steps": [{"text": "q"}]}),
        ("fetch_url", {"url": "https://example.com/a"}),
        ("record_finding", {"claim": "X is true", "source_url": "https://example.com/a", "quote": "x"}),
        # then loops on web_search forever -> budget exhausts
    ])
    _clean("t-force")
    st = loop.run("force synth", run_id="t-force", max_steps=6)
    assert st.done and "Forced" in st.final_report
    assert any(e["type"] == "force_synthesis" for e in read_trace("t-force"))
    _clean("t-force")


def test_notes_scratchpad():
    _install_network_mocks()
    llm.simple = lambda system, user, model=None, temperature=0.0, **kw: LLMResponse(content="summary", usage={"total_tokens": 5})
    llm.chat = _scripted_llm([
        ("update_plan", {"steps": [{"text": "q"}]}),
        ("write_note", {"name": "outline", "content": "1. intro 2. body"}),
        ("read_note", {"name": "outline"}),
        ("fetch_url", {"url": "https://example.com/a"}),
        ("record_finding", {"claim": "X", "source_url": "https://example.com/a", "quote": "x"}),
        ("finish", {"report": "X [1].\n\n## Sources\n[1] A — https://example.com/a"}),
    ])
    _clean("t-notes")
    st = loop.run("notes goal", run_id="t-notes", max_steps=10)
    assert st.notes.get("outline") == "1. intro 2. body"
    ev = read_trace("t-notes")
    assert any(e["type"] == "note_written" and e["data"]["name"] == "outline" for e in ev)
    assert any(e["type"] == "observation" and "1. intro 2. body" in e["data"].get("observation", "") for e in ev)
    assert st.done
    _clean("t-notes")


def test_search_without_fetch_nudge():
    _install_network_mocks()
    llm.simple = lambda system, user, model=None, temperature=0.0, **kw: LLMResponse(content="summary", usage={"total_tokens": 5})
    # search repeatedly with distinct queries (so it's not flagged as a plain repeat-stall)
    llm.chat = _scripted_llm([
        ("update_plan", {"steps": [{"text": "q"}]}),
        ("web_search", {"query": "q1"}),
        ("web_search", {"query": "q2"}),
        ("web_search", {"query": "q3"}),
        ("web_search", {"query": "q4"}),
    ])
    _clean("t-nudge")
    loop.run("nudge goal", run_id="t-nudge", max_steps=8)
    ev = read_trace("t-nudge")
    assert any(e["type"] == "nudge" and e["data"].get("kind") == "search_without_fetch" for e in ev), \
        "expected a search_without_fetch nudge"
    _clean("t-nudge")


def test_stream_report_extraction():
    # the streaming layer surfaces clean report TEXT from partial tool-call JSON
    from agent.llm import _decode_report_value, _ReportStreamer
    assert _decode_report_value('{"rep') is None                      # value not started
    assert _decode_report_value('{"report": "Hel') == "Hel"           # partial
    assert _decode_report_value('{"report": "a\\nb') == "a\nb"        # escape decoded
    assert _decode_report_value('{"report": "done"}') == "done"        # complete
    chunks = []
    s = _ReportStreamer(chunks.append)
    for partial in ['{"report": "Hel', '{"report": "Hello wo', '{"report": "Hello world"}']:
        s.feed(partial)
    assert "".join(chunks) == "Hello world"   # only new suffixes emitted, no repeats


def test_structured_validates_and_retries():
    # reference pattern: malformed structured output is transient -> retry; on a
    # valid response, return the pydantic-validated model.
    from pydantic import BaseModel
    from agent import llm

    class M(BaseModel):
        x: int

    llm.config.LLM_MODE = "live"  # retries only fire when not cassette-fixed
    seq = ["not json at all", '{"x": "not-an-int"}', '{"x": 7}']
    state = {"i": 0}
    def fake_simple(system, user, model=None, temperature=0.0, **kw):
        i = min(state["i"], len(seq) - 1); state["i"] += 1
        return LLMResponse(content=seq[i], usage={"total_tokens": 1})
    llm.simple = fake_simple

    obj, _usage = llm.structured("s", "u", M, max_validation_retries=3)
    assert obj.x == 7 and state["i"] == 3  # took two retries, then validated

    # never-valid -> raises StructuredOutputError (caller falls back)
    llm.simple = lambda system, user, model=None, temperature=0.0, **kw: LLMResponse(content="nope", usage={})
    raised = False
    try:
        llm.structured("s", "u", M, max_validation_retries=1)
    except llm.StructuredOutputError:
        raised = True
    assert raised


def test_resume_persists_and_reloads():
    from agent.state import ResearchState
    _clean("t-resume")
    st = ResearchState.new("resume goal", run_id="t-resume")
    st.steps = 3
    st.persist()
    again = ResearchState.load("t-resume")
    assert again.goal == "resume goal" and again.steps == 3
    _clean("t-resume")


if __name__ == "__main__":
    test_happy_path(); print("PASS happy_path")
    test_fabricated_citation_rejected(); print("PASS fabricated_citation_rejected")
    test_force_synthesis_on_budget_exhaustion(); print("PASS force_synthesis")
    test_stream_report_extraction(); print("PASS stream_report_extraction")
    test_structured_validates_and_retries(); print("PASS structured_validates_and_retries")
    test_notes_scratchpad(); print("PASS notes_scratchpad")
    test_search_without_fetch_nudge(); print("PASS search_without_fetch_nudge")
    test_resume_persists_and_reloads(); print("PASS resume")
    print("\nALL OFFLINE TESTS PASSED")
