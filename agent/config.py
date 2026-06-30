"""Central configuration. Everything tunable lives here, sourced from env with
sensible defaults so the agent runs out-of-the-box once API keys are set."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv is optional; env may already be set
    pass


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


# --- Paths ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"
CASSETTES_DIR = ROOT / "eval" / "cassettes"
RESULTS_DIR = ROOT / "eval" / "results"
SKILLS_DIR = ROOT / "skills"

# --- Models --------------------------------------------------------------
AGENT_MODEL = os.environ.get("AGENT_MODEL", "gpt-4o")
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", "gpt-4o-mini")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gpt-4o-mini")

# --- Budgets (the levers that bound a long run) --------------------------
STEP_BUDGET = _int("STEP_BUDGET", 20)          # max agent iterations
TOKEN_BUDGET = _int("TOKEN_BUDGET", 120_000)   # cumulative prompt+completion tokens
WALL_CLOCK_BUDGET = _int("WALL_CLOCK_BUDGET", 600)  # seconds; 0 disables
MAX_SHORT_TERM = _int("MAX_SHORT_TERM", 4)     # raw tool turns kept verbatim in context
STALL_LIMIT = _int("STALL_LIMIT", 3)           # no-progress iterations before a nudge
SEARCH_WITHOUT_FETCH_LIMIT = _int("SEARCH_WITHOUT_FETCH_LIMIT", 3)  # searches in a row before a fetch nudge
REPEAT_LIMIT = _int("REPEAT_LIMIT", 3)         # identical action repeats (windowed) before a nudge

# --- Verifier (fresh-context critic) ------------------------------------
VERIFY_ENABLED = _bool("VERIFY_ENABLED", True)
MAX_VERIFY_RETRIES = _int("MAX_VERIFY_RETRIES", 2)

# --- Context compaction (keep the rebuilt prompt actually bounded) -------
COMPACT_FINDINGS_AFTER = _int("COMPACT_FINDINGS_AFTER", 12)   # compact once beyond this many
COMPACT_FINDINGS_RECENT = _int("COMPACT_FINDINGS_RECENT", 6)  # render this many verbatim
COMPACT_SOURCES_AFTER = _int("COMPACT_SOURCES_AFTER", 15)
COMPACT_EVERY = _int("COMPACT_EVERY", 4)        # re-run digest at most every N steps

# --- Tool tuning ---------------------------------------------------------
SEARCH_RESULTS = _int("SEARCH_RESULTS", 5)
PAGE_EXCERPT_CHARS = _int("PAGE_EXCERPT_CHARS", 2000)   # excerpt returned to the model
PAGE_MAX_CHARS = _int("PAGE_MAX_CHARS", 20_000)         # cap on stored page text
FETCH_TIMEOUT = _int("FETCH_TIMEOUT", 20)

# --- Skills (off by default: keeps the research loop + its eval cassettes
#     byte-identical; turn on for legal drafting/review with SKILLS_ENABLED=1) ---
SKILLS_ENABLED = _bool("SKILLS_ENABLED", False)
REFERENCE_MAX_CHARS = _int("REFERENCE_MAX_CHARS", 12_000)  # cap a pulled reference body

# --- LLM cassette mode: live | record | replay --------------------------
LLM_MODE = os.environ.get("LLM_MODE", "live").strip().lower()

# --- Keys ----------------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
