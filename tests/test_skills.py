"""Offline tests for the skills layer (agent/skills.py + skill tools + docx).
No API keys, no network. Uses the real skills/ directory for discovery."""
from __future__ import annotations

import io
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import config, skills, verifier                 # noqa: E402
from agent.llm import LLMResponse                           # noqa: E402
from agent.state import ResearchState                       # noqa: E402
from agent.tracer import Tracer                             # noqa: E402
from agent.tools.skill_tools import use_skill, read_reference, list_skills, export_docx  # noqa: E402


def _state(rid):
    shutil.rmtree(config.RUNS_DIR / rid, ignore_errors=True)
    return ResearchState.new("goal", run_id=rid), Tracer(rid, (config.RUNS_DIR / rid))


def _clean(rid):
    shutil.rmtree(config.RUNS_DIR / rid, ignore_errors=True)


# ---- discovery / loaders ------------------------------------------------
def test_list_and_load_skill():
    names = [s["name"] for s in skills.list_skills()]
    assert "paralegal" in names
    body = skills.load_skill("paralegal")
    assert "Pipeline Routing" in body and "Hardened Checklist" in body


def test_read_reference_aliases_invented_names():
    # models invent semantic filenames; the keyword backstop resolves them to the
    # right pipeline (with a transparent note) instead of erroring.
    cases = {
        "references/nda-mutual-draft.md": "contract-draft.md",
        "references/offer-letter-standard.md": "ads-documents.md",
        "references/nda-review.md": "contract-review.md",
        "references/lease-rent-amendment.md": "lease-amendment.md",
    }
    for bad, expected in cases.items():
        body = skills.read_reference("paralegal", bad)
        assert body.startswith(f"(requested '{bad}' — resolved to the matching pipeline reference '{expected}')"), \
            f"{bad} should alias to {expected}"
    # a truly unmappable name still errors with the available list
    try:
        skills.read_reference("paralegal", "references/zzz-unknown.md")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_read_reference_handles_both_paths_and_caps():
    via_ref = skills.read_reference("paralegal", "references/contract-draft.md")
    via_flat = skills.read_reference("paralegal", "contract-draft.md")
    assert via_ref == via_flat and len(via_ref) > 100
    assert len(via_ref) <= config.REFERENCE_MAX_CHARS + 40  # cap + truncation marker
    try:
        skills.read_reference("paralegal", "does-not-exist.md")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


# ---- tools --------------------------------------------------------------
def test_use_skill_sets_active_and_checklist():
    st, tr = _state("t-skill-use")
    out = use_skill({"name": "paralegal"}, st, tr)
    assert st.active_skill == "paralegal"
    assert st.skill_checklist and "disclaimer" in st.skill_checklist.lower()
    assert "Pipeline" in out
    # available reference paths are enumerated so the model doesn't guess filenames
    assert "references/contract-draft.md" in out
    _clean("t-skill-use")


def test_read_reference_tool_uses_active_skill():
    st, tr = _state("t-skill-ref")
    use_skill({"name": "paralegal"}, st, tr)
    out = read_reference({"path": "references/contract-review.md"}, st, tr)  # name defaults to active
    assert "Reference" in out and len(out) > 200
    _clean("t-skill-ref")


def test_export_docx_strips_annotations_keeps_blanks():
    st, tr = _state("t-skill-docx")
    content = ("# Mutual NDA\n\nParty A: [BLANK] // NOTE confirm legal name\n"
               "Term: 2 years // ALT 3 years\n\nGoverning law: Washington.")
    msg = export_docx({"title": "NDA Draft", "filename": "nda.docx", "content": content}, st, tr)
    assert "output/nda.docx" in msg
    docx_path = st.run_dir / "output" / "nda.docx"
    assert docx_path.exists()
    with zipfile.ZipFile(io.BytesIO(docx_path.read_bytes())) as z:
        assert "word/document.xml" in z.namelist()
        doc = z.read("word/document.xml").decode("utf-8")
    assert "[BLANK]" in doc                       # placeholder preserved
    assert "confirm legal name" not in doc        # // NOTE stripped
    assert "3 years" not in doc                   # // ALT stripped
    assert "attorney review only" in doc.lower()  # disclaimer ensured
    _clean("t-skill-docx")


# ---- critic enforces the skill checklist --------------------------------
def test_verifier_injects_skill_checklist():
    st, tr = _state("t-skill-verify")
    st.active_skill = "paralegal"
    st.skill_checklist = "[ ] Attorney-review disclaimer included\n[ ] Every blank marked [BLANK]"
    st.final_report = "Some draft."
    captured = {}

    import agent.llm as llm
    def fake_simple(system, user, model=None, temperature=0.0):
        captured["user"] = user
        return LLMResponse(content='{"pass": true, "issues": []}', usage={"total_tokens": 5})
    llm.simple = fake_simple

    issues = verifier.verify(st, tr)
    assert issues == []
    assert "SKILL VALIDATION CHECKLIST" in captured["user"]
    assert "Attorney-review disclaimer" in captured["user"]
    _clean("t-skill-verify")


if __name__ == "__main__":
    for fn in [test_list_and_load_skill, test_read_reference_aliases_invented_names,
               test_read_reference_handles_both_paths_and_caps,
               test_use_skill_sets_active_and_checklist, test_read_reference_tool_uses_active_skill,
               test_export_docx_strips_annotations_keeps_blanks, test_verifier_injects_skill_checklist]:
        fn(); print("PASS", fn.__name__)
    print("\nALL SKILLS TESTS PASSED")
