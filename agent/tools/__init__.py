"""Tool registry: OpenAI function schemas + name -> callable dispatch.

Every tool is a plain function ``(args, state, tracer) -> observation_str`` and
raises on failure. The loop turns any raised exception into an observation so
the model can see what went wrong and adapt — failures are data, not crashes.
"""
from __future__ import annotations

from .search import web_search
from .fetch import fetch_url
from .plan import update_plan
from .findings import record_finding
from .finish import finish
from .notes import write_note, read_note
from .skill_tools import list_skills, use_skill, read_reference, export_docx

TOOLS = {
    "update_plan": update_plan,
    "web_search": web_search,
    "fetch_url": fetch_url,
    "record_finding": record_finding,
    "write_note": write_note,
    "read_note": read_note,
    "finish": finish,
    # skill tools (dispatchable always; only offered to the model when enabled)
    "list_skills": list_skills,
    "use_skill": use_skill,
    "read_reference": read_reference,
    "export_docx": export_docx,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "update_plan",
            "description": (
                "Create or replace your research plan as an ordered list of steps. "
                "Call this first to lay out sub-questions, and again whenever you need "
                "to re-plan (e.g. a dead end or a new angle). Mark steps done/dropped as you go."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "description": "Ordered plan steps.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "active", "done", "dropped"],
                                },
                            },
                            "required": ["text"],
                        },
                    }
                },
                "required": ["steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for sources relevant to a sub-question. Returns ranked titles, URLs and snippets.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search query."}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch a URL and read it. Returns a summary + excerpt. Fetch a source before citing it.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The URL to fetch."}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_finding",
            "description": (
                "Record a grounded finding: a factual claim, the URL it came from (must be fetched), "
                "and a short supporting quote. Build up findings before writing the report."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The factual claim."},
                    "source_url": {"type": "string", "description": "A URL you have fetched."},
                    "quote": {"type": "string", "description": "Short supporting quote from the source."},
                },
                "required": ["claim", "source_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_note",
            "description": (
                "Write a scratchpad note to offload working memory (e.g. an outline, a "
                "per-subtopic summary, a draft comparison). Notes persist across steps but "
                "stay out of your prompt until you read them. Notes are scratch, NOT evidence "
                "— grounded claims must go through record_finding. Re-writing a name overwrites it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Short note name, e.g. 'outline'."},
                    "content": {"type": "string", "description": "The note body."},
                },
                "required": ["name", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_note",
            "description": "Read back a scratchpad note by name (e.g. before writing the final report).",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "The note name to read."}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": (
                "Finalise the research with a markdown report. Cite sources inline as [n] and end "
                "with a '## Sources' section listing each [n] as 'title — url'. Only cite URLs you fetched."
            ),
            "parameters": {
                "type": "object",
                "properties": {"report": {"type": "string", "description": "The final markdown report with citations."}},
                "required": ["report"],
            },
        },
    },
]

# Skill tools are offered to the model ONLY when SKILLS_ENABLED, so the default
# research toolset (and its recorded eval cassettes) stays byte-identical.
SKILL_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List installed skills (name + description) so you can decide whether one fits the task.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_skill",
            "description": ("Load a skill's router (SKILL.md): its pipelines, routing table, and checklist. "
                            "Call this when the task matches a skill, then match the request to one pipeline."),
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Skill name, e.g. 'paralegal'."}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_reference",
            "description": ("Load ONE detailed pipeline reference for the active skill (e.g. "
                            "'references/contract-draft.md'). Use the pipeline's steps to seed update_plan."),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Skill name (defaults to the active skill)."},
                    "path": {"type": "string", "description": "Reference path from the SKILL.md routing table."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_docx",
            "description": ("Render a finished legal draft to an attorney-review .docx (annotations stripped, "
                            "bracketed placeholders preserved). Use for drafting pipelines that ask for a file."),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title."},
                    "filename": {"type": "string", "description": "Optional output filename."},
                    "content": {"type": "string", "description": "Markdown draft (defaults to the final report)."},
                },
                "required": ["title", "content"],
            },
        },
    },
]


def schemas_for(skills_enabled: bool) -> list[dict]:
    """The toolset offered to the model this run. Skill tools are appended only
    when enabled — keeping the default research prompt (and cassettes) unchanged."""
    return TOOL_SCHEMAS + (SKILL_TOOL_SCHEMAS if skills_enabled else [])


def dispatch(name: str, args: dict, state, tracer) -> str:
    if name not in TOOLS:
        raise RuntimeError(f"unknown tool: {name}")
    return TOOLS[name](args, state, tracer)
