"""Skills layer — progressive disclosure of reusable expertise (the Claude
"skills" pattern), wired into our own loop.

A *skill* is a directory (or flat folder) containing a `SKILL.md` whose YAML
frontmatter gives `name` + `description` (the router the model matches against),
plus reference files holding the detailed pipelines. The point is the same as the
notes/pages strategy: keep the heavyweight reference bodies OUT of the rolling
prompt, and pull exactly one in (JIT) once the model has chosen a pipeline.

- list_skills()            -> [{name, description}]   (cheap; for routing)
- load_skill(name)         -> SKILL.md body            (router + pipelines + checklist)
- read_reference(name,path)-> one capped reference body (the chosen pipeline)

Path handling: a SKILL.md may reference `references/contract-draft.md` while the
files actually live flat next to SKILL.md (`contract-draft.md`). read_reference
resolves both layouts.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from . import config


# --- frontmatter ---------------------------------------------------------
def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (meta, body). Minimal YAML: handles `key: value` and `key: >`
    folded block scalars (enough for name + description)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")

    meta: dict[str, str] = {}
    key = None
    buf: list[str] = []
    folded = False

    def _flush():
        nonlocal key, buf, folded
        if key is not None:
            meta[key] = " ".join(s.strip() for s in buf).strip() if folded else "\n".join(buf).strip()
        key, buf, folded = None, [], False

    for line in fm.split("\n"):
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if m and (not line.startswith((" ", "\t"))):
            _flush()
            key, val = m.group(1), m.group(2).strip()
            if val in (">", "|", ">-", "|-"):
                folded = True  # value continues on indented lines below
            else:
                meta[key] = val.strip().strip('"').strip("'")
                key = None
        elif key is not None:
            buf.append(line)
    _flush()
    return meta, body


# --- discovery -----------------------------------------------------------
@lru_cache(maxsize=1)
def _index() -> dict:
    """name -> {root: Path, skill_md: Path, meta: dict}. Any SKILL.md under
    SKILLS_DIR (recursively) is a skill; its directory is the skill root."""
    out: dict[str, dict] = {}
    base = config.SKILLS_DIR
    if not base.exists():
        return out
    for skill_md in sorted(base.rglob("SKILL.md")):
        meta, _ = _split_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
        name = (meta.get("name") or skill_md.parent.name).strip()
        out[name] = {"root": skill_md.parent, "skill_md": skill_md, "meta": meta}
    return out


def list_skills() -> list[dict]:
    return [{"name": n, "description": (info["meta"].get("description") or "").strip()}
            for n, info in _index().items()]


def load_skill(name: str) -> str:
    info = _index().get(name)
    if info is None:
        raise KeyError(f"unknown skill '{name}'. Available: {', '.join(_index()) or '(none)'}")
    _, body = _split_frontmatter(info["skill_md"].read_text(encoding="utf-8", errors="replace"))
    return body


def reference_files(name: str) -> list[str]:
    """Actual reference markdown files for a skill (excluding SKILL.md), as the
    exact `references/<file>` paths to pass to read_reference. Stops the model
    guessing filenames that don't exist."""
    info = _index().get(name)
    if info is None:
        return []
    return [f"references/{p.name}" for p in sorted(info["root"].glob("*.md"))
            if p.name != "SKILL.md"]


def _resolve_reference(root: Path, path: str) -> Path | None:
    """Resolve a reference path against a skill root, tolerating the
    references/<f> vs flat <f> mismatch. Stays within the skill root."""
    cand = path.strip().lstrip("/")
    names = [cand, cand.split("/")[-1], f"references/{cand.split('/')[-1]}"]
    for rel in names:
        p = (root / rel)
        try:
            p_resolved = p.resolve()
            if p_resolved.is_file() and str(p_resolved).startswith(str(root.resolve())):
                return p_resolved
        except OSError:
            continue
    return None


# Keyword backstop: models tend to invent semantic reference names
# (e.g. "nda-mutual-draft.md", "offer-letter-standard.md"). When the requested path
# doesn't exist, map its keywords to the correct pipeline rather than erroring.
# Ordered: most specific first ("review" beats "nda" so "nda-review" -> review).
_ALIAS_RULES = [
    (("review", "redline", "risk"), "contract-review.md"),
    (("sublease",), "sublease-agreement.md"),
    (("subcontract",), "subcontractor-agreement.md"),
    (("triple", "nnn"), "triple-net-lease-agreement.md"),
    (("lease",), "lease-amendment.md"),
    (("ads", "analytics", "dojo", "offer", "internship"), "ads-documents.md"),
    (("nda", "msa", "sow", "employment", "dpa", "draft", "contract"), "contract-draft.md"),
]


def _alias_filename(path: str) -> str | None:
    stem = path.lower()
    for keys, fname in _ALIAS_RULES:
        if any(k in stem for k in keys):
            return fname
    return None


def read_reference(name: str, path: str) -> str:
    info = _index().get(name)
    if info is None:
        raise KeyError(f"unknown skill '{name}'")
    target = _resolve_reference(info["root"], path)
    redirect = None
    if target is None:  # invented filename -> alias to the matching pipeline
        alias = _alias_filename(path)
        if alias:
            target = _resolve_reference(info["root"], alias)
            redirect = target.name if target is not None else None
    if target is None:
        available = sorted(p.name for p in info["root"].glob("*.md") if p.name != "SKILL.md")
        raise FileNotFoundError(
            f"reference '{path}' not found for skill '{name}'. Available: {', '.join(available)}")
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > config.REFERENCE_MAX_CHARS:
        text = text[: config.REFERENCE_MAX_CHARS] + "\n\n[...reference truncated...]"
    if redirect:
        text = (f"(requested '{path}' — resolved to the matching pipeline reference "
                f"'{redirect}')\n\n{text}")
    return text


def extract_validation_checklist(skill_body: str) -> str:
    """Pull the universal '## Validation checklist' block from a SKILL.md body so
    the fresh-context critic can enforce it. Returns '' if absent."""
    m = re.search(r"##\s*Validation checklist\s*(.*?)(?:\n##\s|\Z)", skill_body, re.S | re.I)
    return m.group(1).strip() if m else ""
