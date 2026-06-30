"""Skill tools — the progressive-disclosure trio (+ docx export).

These mirror read_note / fetch_url exactly: each is a plain
`(args, state, tracer) -> observation` that returns text into the rolling context,
and the heavyweight reference bodies stay on disk until pulled.

  list_skills   -> cheap router: names + descriptions, so the model can match
  use_skill     -> load the SKILL.md (router + pipelines + checklist) into context;
                   mark the skill active and capture its validation checklist so the
                   fresh-context critic can enforce it
  read_reference-> JIT-load ONE chosen pipeline reference (capped)
  export_docx   -> render a finished draft to an attorney-review .docx artifact
"""
from __future__ import annotations

import re

from .. import config, skills
from ..docx import write_docx


def list_skills(args: dict, state, tracer) -> str:
    items = skills.list_skills()
    if not items:
        return "No skills are installed under skills/."
    tracer.emit("skills_listed", {"count": len(items)})
    lines = [f"- {s['name']}: {s['description']}" for s in items]
    return "Available skills:\n" + "\n".join(lines)


def use_skill(args: dict, state, tracer) -> str:
    name = (args.get("name") or "").strip()
    if not name:
        raise RuntimeError("use_skill requires a 'name'")
    body = skills.load_skill(name)  # raises KeyError -> becomes an observation
    state.active_skill = name
    state.skill_checklist = skills.extract_validation_checklist(body)
    refs = skills.reference_files(name)
    tracer.emit("skill_loaded", {"name": name, "checklist_chars": len(state.skill_checklist)})
    avail = ("\n\nAvailable reference paths (use EXACTLY one of these in read_reference — "
             "do not invent a filename):\n" + "\n".join(f"  - {r}" for r in refs)) if refs else ""
    return (f"Loaded skill '{name}'. Match the request to ONE pipeline in the routing table, "
            f"then call read_reference('{name}', '<one of the paths below>') to load its steps, "
            f"then update_plan from that guide.{avail}\n\n{body}")


def read_reference(args: dict, state, tracer) -> str:
    name = (args.get("name") or state.active_skill or "").strip()
    path = (args.get("path") or "").strip()
    if not name or not path:
        raise RuntimeError("read_reference requires 'name' and 'path' (e.g. 'references/contract-draft.md')")
    text = skills.read_reference(name, path)  # raises -> observation; handles flat vs references/
    tracer.emit("reference_read", {"skill": name, "path": path, "chars": len(text)})
    return f"Reference '{path}' for skill '{name}':\n\n{text}"


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()) or "draft"
    if not name.lower().endswith(".docx"):
        name += ".docx"
    return name[:120]


def export_docx(args: dict, state, tracer) -> str:
    """Render a finished draft to runs/<id>/output/<filename>.docx (annotations
    stripped, bracketed placeholders preserved, attorney-review disclaimer ensured)."""
    content = args.get("content") or state.final_report
    if not (content or "").strip():
        raise RuntimeError("export_docx needs 'content' (or a finished report) to render")
    title = (args.get("title") or f"{state.active_skill or 'deepagent'} draft").strip()
    filename = _safe_filename(args.get("filename") or title)
    out_path = state.run_dir / "output" / filename
    write_docx(out_path, title, content)
    rel = f"output/{filename}"
    tracer.emit("docx_exported", {"path": rel, "bytes": out_path.stat().st_size})
    return f"Wrote attorney-review document to {rel} ({out_path.stat().st_size} bytes)."
