---
name: paralegal
description: >
  Use this skill for legal document drafting and review. Handles seven pipelines:
  references/contract-draft.md (new NDAs, MSAs, SOWs, employment contracts, DPAs, amendments) with
  market-standard defaults and jurisdiction-aware guardrails,
  references/contract-review.md (redline existing contracts, produce risk analysis and negotiation guidance),
  references/lease-amendment.md (modify existing lease terms subordinate to a master lease),
  references/subcontractor-agreement.md (construction or services subcontract tied to a prime contract),
  references/sublease-agreement.md (commercial sublease subordinate to a master lease),
  references/triple-net-lease-agreement.md (full commercial NNN lease agreements), and
  references/ads-documents.md (Analytics Dojo SMC Private employment offer letters, employment agreements,
  internship offer letters, internship agreements — governed by Pakistan law). Produces attorney-review-ready
  drafts with mandatory blank-marking, market-standard benchmarks, and jurisdiction checks.
---

# paralegal Skill

## Environment

`SKILL_DIR` is provided to you at runtime. Use that.

### Context

This skill produces legal document drafts and reviews for attorney review. All output must include a disclaimer that it is not legal advice. Never invent party names, amounts, dates, or provisions not explicitly provided.

---

Handle the request directly. Do NOT spawn sub-agents. Always produce the complete legal document or review the user asked for.

## Pipeline Routing

| Pipeline | When to use | Guide |
|---|---|---|
| **A. CONTRACT DRAFT** — draft a new contract from scratch | No input contract; user wants a fresh NDA, MSA, SOW, employment agreement, DPA, or amendment. When user asks to create/generate/export a document file, output a `.docx` with bracketed placeholders preserved and annotation comments (`// NOTE`, `// ALT`, `// RISK`) stripped. | `references/contract-draft.md` |
| **B. CONTRACT REVIEW** — review and redline an existing contract | Input contract exists; user wants risk analysis, redlines, negotiation posture, or executive summary | `references/contract-review.md` |
| **C. LEASE AMENDMENT** — amend terms in an existing lease | Base lease exists; user wants to modify rent, term, use, maintenance, or other provisions | `references/lease-amendment.md` |
| **D. SUBCONTRACTOR AGREEMENT** — draft a subcontractor agreement | Prime contract exists; user needs a subcontract for construction or professional services | `references/subcontractor-agreement.md` |
| **E. SUBLEASE AGREEMENT** — draft a commercial sublease | Master lease exists; user needs a sublease agreement with landlord consent | `references/sublease-agreement.md` |
| **F. TRIPLE-NET LEASE** — draft a commercial NNN lease | User needs a full triple-net (NNN) commercial lease agreement | `references/triple-net-lease-agreement.md` |
| **G. ADS DOCUMENTS** — draft an Analytics Dojo employment or internship document | User wants any offer letter, employment agreement, or internship agreement **for Analytics Dojo SMC Private** (Pakistan). Triggers on: "ADS offer letter", "Analytics Dojo employment agreement", "ADS internship letter", "ADS contract", "offer letter for ADS", "employment agreement Pakistan", or any request explicitly naming Analytics Dojo or ADS as the issuing company. **Do NOT use Pipeline A for these** — ADS documents use Pakistan law, fixed company defaults, and pre-approved template structures that override DSD/Washington-law defaults. | `references/ads-documents.md` |

> **Pipeline G disambiguation rule:** If the user mentions "employment agreement", "offer letter", or "internship agreement" AND also references Analytics Dojo, ADS, Analytics Dojo SMC Private, or Pakistan employment — route to Pipeline G, not Pipeline A. Pipeline A is for generic or DSD-entity contracts only.

### Reference files — pass ONE of these EXACT paths to `read_reference` (do NOT invent a filename)

There is **no per-document file** — e.g. there is no `nda-draft.md`, `nda-mutual-draft.md`, `msa.md`, or `offer-letter.md`. Every from-scratch contract uses `references/contract-draft.md`. Map the document type to the path below:

| Document type(s) | `read_reference` path |
|---|---|
| **NDA · MSA · SOW · employment contract · DPA · IP assignment · amendment-from-scratch** | `references/contract-draft.md` |
| review / redline / risk-analysis of an existing contract | `references/contract-review.md` |
| amend an existing lease | `references/lease-amendment.md` |
| subcontractor agreement | `references/subcontractor-agreement.md` |
| commercial sublease | `references/sublease-agreement.md` |
| triple-net (NNN) commercial lease | `references/triple-net-lease-agreement.md` |
| Analytics Dojo (ADS) offer letter / employment / internship | `references/ads-documents.md` |

(These are the only seven reference files. `use_skill` also lists them; if a path isn't found, re-read this table and pick the exact match.)

## Quick-start workflow

```
# references/contract-draft.md (Pipeline A)
1. Collect intake: document type, full legal names of parties, governing law, key business terms
2. Load references/contract-draft.md → follow intake checklist + section outline for the doc type
3. Draft using market-standard defaults table; mark every unresolved field as [BLANK]
4. Prepend attorney-review disclaimer
5. If user requests a file/document: output a .docx — preserve all [BRACKETED PLACEHOLDERS],
   strip all // NOTE / // ALT / // RISK annotation comments, retain the disclaimer block

# references/contract-review.md (Pipeline B)
1. Identify review perspective: customer / vendor / neutral
2. Run pre-review checklist: blanks, missing exhibits, governing law, insurance
3. Load references/contract-review.md → apply redlining framework + tier system
   (Tier 1 = non-starter, Tier 2 = important, Tier 3 = desirable)
4. Output: executive summary, key terms table, red flags, risk analysis, suggested redlines

# references/lease-amendment.md (Pipeline C)
1. Collect: base lease, prior amendments, modification instructions, authority, jurisdiction
2. Load references/lease-amendment.md → follow section outline and amendment patterns
3. Include ratification clause tying back to base lease; mark open items as [TBD]

# references/subcontractor-agreement.md (Pipeline D)
1. Collect: prime contract, scope documents, project details, party info, insurance requirements
2. Load references/subcontractor-agreement.md → follow section outline, payment clause template
3. Verify state-specific compliance: retainage caps, prompt payment, anti-indemnity, prevailing wage

# references/sublease-agreement.md (Pipeline E)
1. Collect: master lease, parties, premises description, deal terms, landlord consent status
2. Load references/sublease-agreement.md → review master lease restrictions before drafting
3. Follow 16-section draft structure; flag term overflow or conditional consent issues

# references/triple-net-lease-agreement.md (Pipeline F)
1. Collect: parties, premises, rent/term, expense scope, use/compliance, defaults, mortgage, execution kit
2. Load references/triple-net-lease-agreement.md (intake validation + draft modules)
3. Populate clause summary; run jurisdiction checks; verify 8-item maintenance matrix

# references/ads-documents.md (Pipeline G)
1. Identify document type: Standard Employment / Sales / Business Development / Internship
2. Identify output format: Offer Letter only / Agreement only / Both
3. Collect variable fields: recipient name, title, reporting line, start date, compensation,
   commission terms (Sales and BD only) — all other fields are ADS fixed defaults
4. Load references/ads-documents.md → apply ADS fixed defaults + Pakistan labour law compliance table
5. Populate template; mark every missing variable as [BLANK]
6. Output .docx — filename: ADS-[DocType]-[RecipientLastName]-v1.0-DRAFT-[YYYYMMDD].docx
```

## Goal Decomposition & Sequential Execution

Before producing any draft or analysis, the agent must follow this protocol for every pipeline invocation:

**Step 1 — State the final goal.**
Write one sentence naming the complete deliverable before any work begins.
> Example: *"Draft a balanced mutual NDA governed by Washington law between DSD and Acme Corp."*
> Example: *"Draft an ADS Sales Employment Offer Letter and Agreement for [Recipient Name]."*

**Step 2 — Load the reference and decompose into ordered tasks.**
Read the relevant reference guide(s) for the matched pipeline. Derive a numbered task list directly from the steps, sections, and checklists in that guide. Tasks must map to explicit reference structure — no free-form additions.

| Pipeline | Reference(s) to load | Task source |
|----------|----------------------|-------------|
| A — Contract Draft | `references/contract-draft.md` | Step 1 Intake → Step 2 Architecture §§ 1–25 → Step 3 Mandatory Blocks → DSD Standards → Output Template → `.docx` Generation rules |
| B — Contract Review | `references/contract-review.md` | Step 1 Role/Power → Pre-review checklist → Mandatory Highlights (×5) → Redline framework → Full output structure |
| C — Lease Amendment | `references/lease-amendment.md` | Prerequisites → Section outline (Preamble → Boilerplate → Execution Blocks) → Pitfalls check |
| D — Subcontractor Agreement | `references/subcontractor-agreement.md` | Prerequisites → 12-section outline → Payment clause → Insurance → Indemnification → Termination → State compliance |
| E — Sublease Agreement | `references/sublease-agreement.md` | Master lease review → 16-section draft → Section requirements → Pitfalls check |
| F — Triple-Net Lease | `references/triple-net-lease-agreement.md` | Intake validation (8 categories) → 16 draft modules → Clause summary → Maintenance matrix → Insurance schedule → Exhibits → Pre-execution checklist |
| G — ADS Documents | `references/ads-documents.md` | Step 1 Doc-type identification → Step 2 Variable intake → Step 3 Fixed defaults application → Step 4 Pakistan law compliance check → Step 5 Template population → Step 6 Hardened checklist → `.docx` output |

**Step 3 — Execute sequentially; mark each task `[DONE]` before the next begins.**
Work through the task list one item at a time. After completing a task, write `[DONE]` next to it. Do not start the following task until the current one is explicitly marked `[DONE]`.

**Step 4 — No final output until all tasks are `[DONE]`.**
Never produce the draft, review, or summary while any task remains incomplete. If a task cannot be completed (missing information, unresolvable blank), mark it `[BLOCKED — <reason>]` and surface it to the user before continuing.

---

## Validation checklist

Always run these checks before delivering any output:

```
[ ] All required fields are present or explicitly marked as [BLANK] / [TBD]
[ ] Governing law and jurisdiction identified
[ ] Market-standard benchmarks applied (see references/contract-draft.md / references/contract-review.md)
[ ] Jurisdiction-specific rules checked (anti-indemnity, retainage, prompt payment, prevailing wage)
[ ] Flow-down obligations verified for subcontractor agreements
[ ] NNN maintenance matrix populated; structural repairs not shifted to tenant without instruction
[ ] Ratification clause present for amendments and subleases
[ ] ADS fixed defaults applied and Pakistan labour law compliance table checked (Pipeline G only)
[ ] Attorney-review disclaimer included at top of output
```

## Critical rules

1. **No hallucination.** Never invent party names, addresses, dollar amounts, dates, or legal provisions. Use only information explicitly provided. Mark every missing required field as `[BLANK — confirm with client]`.
2. **Attorney review.** Every output must begin with: *This document is a draft for attorney review only and does not constitute legal advice.*
3. **Jurisdiction checks.** Always confirm governing law before drafting. For leases and subcontracts, verify state-specific rules: anti-indemnity statutes, retainage caps, prompt-payment requirements, prevailing wage. See `references/subcontractor-agreement.md` and `references/triple-net-lease-agreement.md`.
4. **Market-standard defaults.** Use benchmarks in `references/contract-draft.md` and `references/contract-review.md` as starting positions; flag any deviation as a negotiation point.
5. **Preserve unresolved blanks.** Never assume statutory defaults. Preserve `[BLANK]` / `[TBD]` markers for all open fields so the reviewing attorney can identify them.
6. **Flow-down obligations.** For subcontractor agreements, ensure all prime-contract obligations (insurance, indemnity, IP, safety, change orders) flow down appropriately. See `references/subcontractor-agreement.md`.
7. **NNN economics.** In triple-net leases, never shift structural repair obligations (roof, foundation, exterior walls) to the tenant without explicit client instruction. See `references/triple-net-lease-agreement.md`.
8. **ADS fixed identity.** For Pipeline G, never alter the company name, registered address, client entity, or governing law. These are locked. See `references/ads-documents.md` Fixed Defaults table.

## Hardened Checklist Protocol — Pipelines A, B & G

For **Pipeline A (Contract Draft)**, **Pipeline B (Contract Review)**, and **Pipeline G (ADS Documents)**, the internal checklist from the reference guide is a **mandatory blocking gate**. It must be executed as a discrete, numbered task. Mark every item `[DONE]` or `[FAIL — <reason>]`. The agent must never proceed to the Validation checklist, final draft, or final answer until every item is `[DONE]`. Resolving a `[FAIL]` item takes priority over all other work.

### Pipeline A — Contract Draft hardened checklist

Run this as a named task (e.g., Task 9 in the example sequence above). Complete it in order; do not skip items.

```
[ ] All 25 architecture sections present, or explicitly scoped out with rationale recorded
[ ] All 6 mandatory drafting blocks drafted and present:
      Governing Law & Jurisdiction | Liability Cap | Indemnification |
      Confidentiality | Termination | IP Ownership
[ ] Every unresolved field marked [BLANK] / [TBD] / [CONFIRM WITH COUNSEL] — none assumed
[ ] DSD-specific standards applied for the document type (MSA / SOW / NDA / Employment / DPA)
[ ] Market-standard defaults applied from benchmarks table; deviations flagged as negotiation points
[ ] Attorney-review disclaimer present at top of document
[ ] Annotation conventions correctly applied — // NOTE, // ALT (user-favorable), // RISK
[ ] If .docx output requested: annotations stripped; [BRACKETED PLACEHOLDERS] preserved verbatim;
    filename follows convention [DocType]-[PartyA]-[PartyB]-DRAFT-[YYYYMMDD].docx
```

### Pipeline B — Contract Review hardened checklist

Run this as a named task before producing any review output. Complete it in order; do not skip items.

```
[ ] Review perspective identified and recorded: customer / vendor / neutral
[ ] Pre-review checklist complete: blanks located, missing exhibits noted, governing law confirmed,
    insurance requirements verified, signature status and version checked
[ ] All 5 universal mandatory highlights addressed:
      Insurance | Governing Law & Jurisdiction | Liability & Indemnification |
      Amendment Rights | Termination
[ ] Redlines produced using the three-tier system:
      Tier 1 = non-starter | Tier 2 = important | Tier 3 = desirable
[ ] Full output structure complete:
      Executive Summary | Key Terms table | Mandatory Highlights | Red Flags Quick Scan |
      Risk Analysis | Proposed Redlines | Negotiation Priority matrix |
      Missing Provisions | Jurisdiction-Specific Alerts
[ ] Market-standard benchmarks applied; yellow and red thresholds explicitly flagged
[ ] Document-type checklist applied:
      NDA / SaaS–MSA / Service Agreement / Employment / M&A / Government / Finder–Broker
[ ] Attorney-review disclaimer present in output
```



> **Enforcement rule:** If any item is `[FAIL]`, stop, resolve it, and re-mark it `[DONE]` before continuing. A single unresolved `[FAIL]` blocks finalization. Do not route around a `[FAIL]` by moving to the Validation checklist or producing partial output.

---

## References

| File | Topic |
|---|---|
| `references/contract-draft.md` | CONTRACT DRAFT pipeline: intake checklist, 25-section outline, universal mandatory blocks (governing law, liability cap, indemnification, confidentiality, termination, IP), market-standard defaults table, document-type quick reference (NDA, MSA, SOW, Employment, DPA, Amendments) |
| `references/contract-review.md` | CONTRACT REVIEW pipeline: redlining framework, dual-party tier system (1=non-starter / 2=important / 3=desirable), risk analysis output structure, market-standard benchmarks, negotiability guide, document-type checklists (NDA, SaaS/MSA, Service, Employment, M&A, Government, Finder/Broker) |
| `references/lease-amendment.md` | LEASE AMENDMENT: prerequisites, amendment patterns (rent, term, use, maintenance, new provisions), ratification & integration clauses, execution blocks (individuals, entities, notarization, witnesses, spousal consent), pitfalls |
| `references/subcontractor-agreement.md` | SUBCONTRACTOR AGREEMENT: 12-section outline, payment clause template (lump sum, T&M, retainage, disputed amounts), insurance minimums table, indemnification checklist with state anti-indemnity statute compliance, termination framework matrix, state-specific compliance checks |
| `references/sublease-agreement.md` | SUBLEASE AGREEMENT: master lease review checklist, 16-section draft structure, section requirements (Preamble through Execution), pitfalls (term overflow, absolute prohibitions, conditional consent, jurisdiction-specific rules) |
| `references/triple-net-lease-agreement.md` | TRIPLE-NET LEASE (concise): intake validation (8 categories), 14 draft modules, clause summary population, jurisdiction checks (anti-indemnity, holdover rent, guaranty, notice, attorney-fee symmetry), pitfalls |
| `references/ads-documents.md` | ADS DOCUMENTS pipeline: fixed company defaults, variable intake checklist, four document-type templates (Standard Employment / Sales / Business Development / Internship), Pakistan labour law compliance table, benefits schedules, Exhibit structures, hardened checklist |