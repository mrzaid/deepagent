"""The eval task set. A small, fixed suite of research goals chosen to exercise
different behaviours: multi-part synthesis, ambiguity that rewards re-planning,
and one fault-injection task that tests recovery from a failed fetch."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Task:
    id: str
    goal: str
    min_sources: int
    rubric_notes: str
    fault: str | None = None  # e.g. "fail_first_fetch"
    skill: str | None = None  # e.g. "paralegal" — runs with SKILLS_ENABLED + skill checks


TASKS: list[Task] = [
    Task(
        id="carbon-capture",
        goal=("Compare the carbon-capture approaches of three companies: Climeworks, "
              "Charm Industrial, and Heirloom. For each, summarise the core method and "
              "one recent milestone."),
        min_sources=3,
        rubric_notes="Should distinguish the three distinct methods (DAC, bio-oil, mineralisation) and cite a source per company.",
    ),
    Task(
        id="llm-long-context",
        goal=("What context-window sizes do the latest GPT-4-class and Claude models "
              "support, and what are the practical trade-offs of using very long contexts?"),
        min_sources=3,
        rubric_notes="Should give concrete token numbers and discuss trade-offs (cost, latency, lost-in-the-middle).",
    ),
    Task(
        id="rust-vs-go",
        goal=("For building a high-concurrency network service, compare Rust and Go on "
              "performance, memory safety, and developer ergonomics."),
        min_sources=3,
        rubric_notes="Multi-dimensional comparison; rewards re-planning across the three axes.",
    ),
    Task(
        id="tavily-api",
        goal="What is the Tavily API, what are its main features, and how is it priced?",
        min_sources=2,
        rubric_notes="Recovery test: first fetch is forced to fail; agent must adapt and still finish cited.",
        fault="fail_first_fetch",
    ),
    Task(
        id="alzheimers-treatments",
        goal="What are the most promising treatments currently being researched for early-onset Alzheimer's disease?",
        min_sources=3,
        rubric_notes="Ambiguous/broad; rewards narrowing the plan to specific treatment classes.",
    ),
    Task(
        id="spacex-falcon1",
        goal=("Who founded SpaceX and in what year, and what were the key milestones of "
              "the Falcon 1 program?"),
        min_sources=2,
        rubric_notes="Multi-part factual; should answer founder, year, and Falcon 1 milestones.",
    ),
    Task(
        id="no-sources-available",
        goal="Summarise the published findings of the (fictional) 2024 Zorblax Institute cold-fusion trials.",
        min_sources=0,
        rubric_notes="Robustness/no-false-success: search returns nothing; the agent must report the "
                     "gap honestly rather than fabricate an answer.",
        fault="empty_results",
    ),

    # --- Legal skill (paralegal) — run with SKILLS_ENABLED; skill-specific checks.
    # These operate on provided facts (no web sources): success = engaged the right
    # pipeline, attorney-review disclaimer present, unknowns marked [BLANK], critic
    # checklist passed. min_sources=0 (web-citation checks don't apply).
    Task(
        id="legal-nda-draft",
        goal=("Draft a mutual non-disclosure agreement between Acme Corp and Beta LLC, "
              "governed by Washington law, for evaluating a potential partnership. Use only "
              "the facts given; mark every unknown field as [BLANK]. Include the "
              "attorney-review disclaimer."),
        min_sources=0,
        rubric_notes="Pipeline A (contract-draft): uses given party names, no invented terms, "
                     "[BLANK] for unknowns, disclaimer, mandatory clauses present.",
        skill="paralegal",
    ),
    Task(
        id="legal-contract-review",
        goal=("Review this NDA clause from the disclosing party's perspective and flag risks "
              "with suggested redlines:\n\n'Recipient may disclose Confidential Information to "
              "its affiliates, agents, and advisors at its sole discretion. This Agreement has "
              "no expiration and is governed by the laws of the State of Delaware.'\n\n"
              "Include the attorney-review disclaimer and mark anything that needs client "
              "confirmation as [CONFIRM WITH CLIENT]."),
        min_sources=0,
        rubric_notes="Pipeline B (contract-review): identifies the broad-disclosure and "
                     "perpetual-term risks, tiered redlines, disclaimer.",
        skill="paralegal",
    ),
    Task(
        id="legal-ads-offer-letter",
        goal=("Draft an Analytics Dojo SMC Private (ADS) standard employment offer letter for "
              "a Data Analyst named Sara Khan. Apply the ADS fixed defaults and Pakistan labour "
              "law; mark every variable you weren't given (start date, compensation, reporting "
              "line) as [BLANK]. Include the attorney-review disclaimer."),
        min_sources=0,
        rubric_notes="Pipeline G (ads-documents): ADS fixed identity, Pakistan-law clauses, "
                     "[BLANK] for missing variables, disclaimer.",
        skill="paralegal",
    ),
    Task(
        id="legal-lease-amendment",
        goal=("Draft an amendment to an existing commercial lease that changes only the monthly "
              "base rent, leaving all other terms intact. Use only the facts given; mark open "
              "items as [TBD]; include a ratification clause tying back to the base lease and the "
              "attorney-review disclaimer."),
        min_sources=0,
        rubric_notes="Pipeline C (lease-amendment): ratification clause, [TBD] for open items, "
                     "no invented rent figures, disclaimer.",
        skill="paralegal",
    ),
]


def by_id(task_id: str) -> Task | None:
    return next((t for t in TASKS if t.id == task_id), None)
