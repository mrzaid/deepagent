"""ResearchState: the agent's structured long-term memory.

This is the heart of the context strategy. Rather than appending every message
and every fetched page to an ever-growing transcript, we keep a compact,
structured state object and *reconstruct* a bounded prompt from it each turn
(see context.py). State is serialised to runs/<run_id>/state.json after every
step, which gives us three things for free: crash-safe resume, a live data
source for the web UI, and the artifact the eval harness inspects.

Full page text is deliberately NOT stored in this object — it lives in
runs/<run_id>/pages/<hash>.txt so it never bloats the rolling context.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from . import config


@dataclass
class PlanStep:
    id: int
    text: str
    status: str = "pending"  # pending | active | done | dropped


@dataclass
class Finding:
    """A single grounded claim tied to a source the agent actually fetched."""
    claim: str
    source_url: str
    quote: str
    step: int


@dataclass
class Source:
    url: str
    title: str = ""
    fetched: bool = False
    summary: str = ""
    page_file: str = ""  # relative path under the run dir, if fetched


@dataclass
class Turn:
    """One executed tool call + a short observation, kept verbatim for the last
    K turns to give the model tactical continuity."""
    step: int
    tool: str
    args: dict
    observation: str  # already truncated/summarised


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]


@dataclass
class ResearchState:
    goal: str
    run_id: str = field(default_factory=_new_run_id)
    created_at: str = field(default_factory=_now)
    steps: int = 0
    done: bool = False
    final_report: str = ""
    tokens_used: int = 0

    plan: list[PlanStep] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    sources: dict[str, Source] = field(default_factory=dict)
    short_term: list[Turn] = field(default_factory=list)
    # scratchpad: virtual notes the agent writes/reads to offload working memory.
    # Only names+sizes appear in context; bodies are pulled in on demand via read_note.
    notes: dict[str, str] = field(default_factory=dict)

    # compaction digests: older findings/sources collapse here so the rebuilt
    # prompt stays bounded. The full lists above are never dropped from state.
    findings_digest: str = ""
    sources_digest: str = ""

    # active skill (paralegal pipelines etc.) — empty for plain research runs
    active_skill: str = ""
    skill_checklist: str = ""  # validation checklist the critic must also enforce

    # internal bookkeeping (persisted so resume is faithful)
    stall_counter: int = 0
    last_action_sig: str = ""
    nudges: int = 0
    searches_since_fetch: int = 0
    verify_retries: int = 0
    compactions: int = 0
    # eval fault-injection flags, e.g. {"fail_first_fetch": true}
    fault: dict = field(default_factory=dict)

    # ---- lifecycle ------------------------------------------------------
    @classmethod
    def new(cls, goal: str, run_id: Optional[str] = None, fault: Optional[dict] = None) -> "ResearchState":
        st = cls(goal=goal, fault=fault or {})
        if run_id:
            st.run_id = run_id
        st.run_dir.mkdir(parents=True, exist_ok=True)
        st.pages_dir.mkdir(parents=True, exist_ok=True)
        return st

    @classmethod
    def load(cls, run_id: str) -> "ResearchState":
        path = config.RUNS_DIR / run_id / "state.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @property
    def run_dir(self) -> Path:
        return config.RUNS_DIR / self.run_id

    @property
    def pages_dir(self) -> Path:
        return self.run_dir / "pages"

    @property
    def notes_dir(self) -> Path:
        return self.run_dir / "notes"

    def write_note(self, name: str, content: str) -> None:
        """Store a scratchpad note in state and mirror it to disk for audit."""
        self.notes[name] = content
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)[:80]
        (self.notes_dir / f"{safe}.txt").write_text(content, encoding="utf-8")

    def persist(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.run_dir / "state.json.tmp"
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.run_dir / "state.json")  # atomic-ish on same filesystem

    # ---- helpers --------------------------------------------------------
    def add_source(self, url: str, title: str = "") -> Source:
        src = self.sources.get(url)
        if src is None:
            src = Source(url=url, title=title)
            self.sources[url] = src
        elif title and not src.title:
            src.title = title
        return src

    def fetched_urls(self) -> set[str]:
        return {u for u, s in self.sources.items() if s.fetched}

    def push_turn(self, turn: Turn) -> None:
        self.short_term.append(turn)
        if len(self.short_term) > config.MAX_SHORT_TERM:
            self.short_term = self.short_term[-config.MAX_SHORT_TERM:]

    # ---- (de)serialisation ---------------------------------------------
    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "steps": self.steps,
            "done": self.done,
            "final_report": self.final_report,
            "tokens_used": self.tokens_used,
            "plan": [asdict(p) for p in self.plan],
            "findings": [asdict(f) for f in self.findings],
            "sources": {u: asdict(s) for u, s in self.sources.items()},
            "short_term": [asdict(t) for t in self.short_term],
            "notes": self.notes,
            "findings_digest": self.findings_digest,
            "sources_digest": self.sources_digest,
            "active_skill": self.active_skill,
            "skill_checklist": self.skill_checklist,
            "stall_counter": self.stall_counter,
            "last_action_sig": self.last_action_sig,
            "nudges": self.nudges,
            "searches_since_fetch": self.searches_since_fetch,
            "verify_retries": self.verify_retries,
            "compactions": self.compactions,
            "fault": self.fault,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ResearchState":
        st = cls(goal=d["goal"], run_id=d["run_id"])
        st.created_at = d.get("created_at", _now())
        st.steps = d.get("steps", 0)
        st.done = d.get("done", False)
        st.final_report = d.get("final_report", "")
        st.tokens_used = d.get("tokens_used", 0)
        st.plan = [PlanStep(**p) for p in d.get("plan", [])]
        st.findings = [Finding(**f) for f in d.get("findings", [])]
        st.sources = {u: Source(**s) for u, s in d.get("sources", {}).items()}
        st.short_term = [Turn(**t) for t in d.get("short_term", [])]
        st.notes = d.get("notes", {})
        st.findings_digest = d.get("findings_digest", "")
        st.sources_digest = d.get("sources_digest", "")
        st.active_skill = d.get("active_skill", "")
        st.skill_checklist = d.get("skill_checklist", "")
        st.stall_counter = d.get("stall_counter", 0)
        st.last_action_sig = d.get("last_action_sig", "")
        st.nudges = d.get("nudges", 0)
        st.searches_since_fetch = d.get("searches_since_fetch", 0)
        st.verify_retries = d.get("verify_retries", 0)
        st.compactions = d.get("compactions", 0)
        st.fault = d.get("fault", {})
        return st
