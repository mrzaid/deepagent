# Contract Review & Redlining Skill

Covers reviewing, redlining, and interpreting any uploaded legal document — NDAs, MSAs,
employment agreements, leases, SaaS terms, M&A due diligence, and more. Flags risks across
41 CUAD categories, identifies missing or non-standard clauses, and produces prioritized
redlines from either party's negotiating position. Built on CUAD, ContractEval, and
LegalBench benchmarks; outputs an executive summary, risk heat map, and negotiation-ready
redline document.

---

## Step 0: Establish Business Context — BEFORE Any Analysis

Collect the following before reviewing. Ask if unclear.

- **Business purpose**: What is this contract for, and what does a successful outcome look like?
- **Risk tolerance**: What are the organization's known non-negotiables?
- **Signatory authority**: Who is authorized to bind the organization? Has that been confirmed?
- **Deal dynamics**: Is there time pressure to sign? Rushed signing = elevated risk — flag explicitly.
- **Counterparty relationship**: New vs. established? Prior disputes or issues?
- **Prior drafts**: Is this the first draft, a counter-redline, or a near-final version?

> **Flag immediately** if the reviewer reports being pressured to sign quickly — note this in
> Pre-Signing Alerts as: *"Signing urgency reported — heightened review warranted."*

---

## Step 1: Identify Role & Power Dynamic — REQUIRED BEFORE ANALYSIS

**Always ask if unclear:** "Which party are you, and are you reviewing or countering a redline?"

| Your Role | Primary Lens | Flag as Risky |
|-----------|-------------|---------------|
| Customer / Buyer / Licensee | Inbound vendor paper | Vendor-favorable terms |
| Vendor / Seller / Licensor | Own paper or counter-redline | Customer overreach |
| Both / Adversarial simulation | Dual-party analysis | Flag from each side separately |

**Power dynamic matters — set realistic expectations:**
- Startup vs. enterprise → limited leverage; prioritize top 3 issues only
- Sole-source vendor → focus on exit rights and data portability
- Government procurement → standard form; limited negotiating room
- Regulated terms (banking, GDPR) → some provisions are legally non-negotiable

**Vendor/Licensor protections to flag (often overlooked):**
- Customer's right to benchmark or audit (frequency abuse risk)
- Scope creep via change order or unilateral SOW expansion
- Customer's failure to provide timely access, approvals, or data
- Over-broad IP assignment stripping vendor's pre-existing IP
- Termination-for-convenience used to avoid payment after delivery
- Excessive indemnification demands from customers against vendors

---

## Step 2: Pre-Review Checklist

Before any substantive analysis, flag each of the following:

- **Blank fields**: `$X`, `TBD`, `[amount]`, `[DATE]`, `[INSERT]`
- **Missing exhibits**: List all referenced schedules; note which are absent or marked "to be agreed"
- **Exhibit consistency**: Confirm main body and all exhibits do not conflict — conflicts create ambiguity courts must resolve
- **"To be mutually agreed" exhibits**: Flag as High risk — open negotiation points that can undermine the whole agreement
- **Governing law**: Present or absent?
- **Insurance clause**: Present or absent?
- **Signature status**: Draft or executed? (Executed → review is informational only)
- **Version control**: Confirm this is the latest version — check version number and date; never review a clean copy when a redlined version exists; request the redline if absent
- **Personal guarantee clause**: Present or absent? If present: is it limited/capped or unlimited? Does it apply to individuals or only entities?
- **Version**: Clean draft or redlined?

---

## Step 3: Definitions Audit — READ FIRST

**Before analyzing any substantive clause, always read and audit the definitions section.**

Defined terms control meaning throughout the document. An unfavorable definition can make
an otherwise acceptable clause problematic.

- Extract all defined terms and their definitions
- Flag **circular definitions**, **overly broad definitions**, or **undefined capitalized terms** used in the body
- Note where a definition materially expands or limits an obligation (e.g., a broad "Confidential Information" definition vs. a narrow one; "Affiliate" defined to include future acquisitions)
- Cross-reference: are all defined terms actually used? Are key terms used in the body without being defined?
- Flag ambiguous defined terms as at minimum a Minor/Watch issue

---

## Step 4: Cross-Reference Verification

For every clause containing "as set forth in Section X," "subject to Section Y," or similar —
actually read that section in context before characterizing the clause.

**Common traps:**
- Carve-outs to liability caps buried in IP or data breach sections
- Termination triggers that expand via cross-reference to force majeure or SLA provisions
- Payment exclusions hidden in acceptance criteria sections
- Indemnification scope expanded by cross-reference to exhibit definitions

> Flag any cross-reference that materially changes the meaning of a clause as an issue in
> the Risk Analysis, even if the base clause appears acceptable.

---

## Step 5: Universal Mandatory Highlights

**Always surface all six blocks — never skip, even if acceptable.**

### Insurance
Report: coverage types required (GL, E&O/Professional Indemnity, Cyber Liability, Workers'
Comp, CAR, Performance Bond), minimum amounts, additional insured, Certificate of Insurance
requirement, link to indemnification obligations.

**Critical if absent** in any service, infrastructure, license, or indemnification-heavy agreement.

> Suggested fallback: "Each party shall maintain: (i) GL ≥ $1M per occurrence / $2M aggregate;
> (ii) Professional Indemnity/E&O ≥ $1M; (iii) Cyber Liability ≥ $1M. Certificate of Insurance
> provided on request, naming the other party as additional insured."

### Governing Law & Jurisdiction
Always extract: governing law (country/state), jurisdiction type (exclusive/non-exclusive,
courts/arbitration), venue, escalation ladder (negotiation → mediation → arbitration/litigation),
offshore flag (BVI/Cayman = high-risk), enforcement practicality.

Note: Governing Law ≠ Jurisdiction — flag when they diverge unexpectedly.

**Critical if absent** — jurisdiction becomes its own dispute.

### Liability & Indemnification
Report: cap amount and basis (mutual or one-sided), uncapped carve-outs (fraud, IP, data breach,
willful misconduct, death/injury), indemnification symmetry, insurance backing, third-party
exposure, exclusive remedy clauses.

### Amendment Rights
Flag: unilateral vs. mutual written consent, notice period, whether material terms (pricing,
scope, caps) can change without consent.

**Also flag:**
- Absence of a "No Waiver" clause — confirms past leniency doesn't set precedent
- Absence of an "Entire Agreement" / integration clause — confirms written contract supersedes prior verbal or email negotiations
- Flag absence of both as Medium risk
- Note: even with these clauses, advise client to document all agreed changes as formal written amendments, not email threads

**Critical if one party holds sole discretion to amend.**

Market standard: mutual written consent required.

### Termination
Report: convenience (mutual or one-sided, notice period), cause (triggers, cure period —
standard 30 days), insolvency trigger, post-termination obligations (data return, IP reversion,
survival of confidentiality/non-compete), dispute remedy on termination contest.

### Force Majeure
Report:
- Trigger events listed — are they specific or broad? Do they include pandemics, cyberattacks, government action, supply chain disruption?
- Effect on obligations — does it suspend performance only, or also suspend payment obligations?
- Duration limit — how long before either party can terminate due to a continuing FM event?
- Notice requirements to invoke
- Exclusions (e.g., financial hardship, foreseeable events)

**Market standard:** broad triggers including Acts of God, government action, cyber incidents;
payment obligations typically not excused; termination right after 30–90 days of continued FM event.

**Flag as Critical if:** absent entirely in service, supply, or infrastructure agreements.

> Suggested fallback: "Neither party shall be liable for delays caused by circumstances beyond
> their reasonable control, including natural disasters, government action, or cyberattacks,
> provided the affected party gives prompt written notice. If the FM event continues for more
> than [60/90] days, either party may terminate on written notice without liability."

---

## Redlining — Dual-Party Framework

### Redline Tiers
| Tier | Label | Meaning |
|------|-------|---------|
| 1 | Non-starter | Walk away if not resolved |
| 2 | Important | Push hard; accept fallback if needed |
| 3 | Desirable | Nice to have; trade freely |

### Redline Output Format
For each proposed change, produce:

```
Section: [X.X] — [Title]
Original: "[exact quoted text]"
Proposed: "[replacement text]"
Tier: [1 / 2 / 3]
Rationale (internal): [why this change is needed from your client's perspective]
Walkaway (internal): [minimum acceptable fallback]
Counterparty note (external): [neutral justification suitable to send to the other side]
```

### Counter-Redline Markup Rules (Receiving a Redlined Document)

When the user receives a document that already contains another party's redlines (the **Originating Party**) and must respond on behalf of the reviewing party (the **Responding Party**), the following rules are **mandatory and override general redlining instincts**. These rules apply regardless of which party originally drafted the document, who sent the redline, or how many rounds of markup have already occurred.

#### Two-Track Decision Rule — Apply Before Every Change

Before acting on any clause, classify it:

| Track | Clause state | What to do |
|-------|-------------|------------|
| **Track 1 — Direct Redline** | Text has NO existing markup from any prior party — original clean contract language only | Redline directly using the standard Redline Output Format: strike out, insert, or replace as needed |
| **Track 2 — Comment Only** | Text has been touched by the Originating Party (struck out, inserted, or flagged) | Do NOT redline. Add a highlight + comment recording ACCEPT, REJECT, or COUNTER only |

**The deciding question for every clause:** *"Has any prior party already marked up this specific text?"*
- No → Track 1. Redline it directly.
- Yes → Track 2. Comment on it; do not touch the existing markup.

**What the Responding Party MUST NOT do:**
- Apply Track 2 (comments only) to clean, untouched text — untouched text must be redlined directly, not just commented on
- Strike out or delete any text the Originating Party has already struck out — never touch the other side's strikethroughs
- Re-attribute or rename the Originating Party's tracked changes, comments, or markup to the Responding Party
- Overwrite or replace the Originating Party's proposed insertions as if producing a clean counter-draft

**What the Responding Party IS permitted to do:**
- **Track 1 (untouched text):** Redline directly — strike out objectionable language, insert preferred language, propose replacements using the standard Redline Output Format
- **Track 2 (already-redlined text):** Add a highlight + comment to record `ACCEPT`, `REJECT — [reason]`, or `COUNTER — [alternative language]`
- Add net-new clauses to any section, provided they do not require striking out the Originating Party's existing redlined text

**Format for Track 1 — Direct Redline (untouched text):**
Use the standard Redline Output Format above (Original / Proposed / Tier / Rationale / Walkaway / Counterparty note).

**Format for Track 2 — Comment Only (already-redlined text):**
```
[Comment — Section X.X — Responding to other side's redline]
Their change: [brief description of what the Originating Party struck out or inserted]
Our response: ACCEPT | REJECT | COUNTER
Reason: [plain-language rationale]
Counter-language (if countering): "[Responding Party's alternative proposed text]"
Tier: [1 / 2 / 3]
```

**Why this matters:** Untouched text is fully in play — redline it like any first-round review. Only the Originating Party's existing markup is off-limits for direct editing. Collapsing everything into comments loses the Responding Party's negotiating position on every clause the Originating Party never touched.

> **Step 0 check:** Before any redline work, confirm with the user — "Is this a first redline of a clean document, or a counter-redline responding to the other side's existing markup?" If counter-redline, apply the Two-Track Decision Rule to every clause before acting.

### Dual-Party / Adversarial Mode
When simulating both counsel or countering a redline, run **two named analyses** before synthesizing:

**Originating Party Counsel** — accepts, rejects, or proposes fallback on each redline, with rationale  
**Responding Party Counsel** — responds using the Counter-Redline Markup Rules above (highlight + comment; no overwriting the other side's strikethroughs)  
**Joint Delta** — summary of open items, agreed items, and recommended compromise positions

> Never let either party's counsel be purely capitulative or purely aggressive — realistic
> negotiation involves concession on some points to hold firm on others.

### Counter-Redline Response Format
When reviewing the other side's redlines:

```
Their Ask: "[their proposed language]"
Our Position: Accept / Reject / Counter
Counter-Proposal: "[our alternative language, if countering]"
Tier: [1 / 2 / 3]
Rationale: [why we accept, reject, or counter]
```

---

## Output Structure

```markdown
# Contract Review: [Document Name]
**Type:** | **Your Position:** | **Counterparty:** | **Risk Level:**
**Governing Law:** | **Insurance Clause:** | **Status:** Draft / Executed / Unknown

---
## Pre-Signing Alerts
[Blanks, missing exhibits, absent governing law or insurance, version concerns,
personal guarantees, signing pressure. "None identified" if clean.]

## Executive Summary
[3–5 sentences: overall posture, top issues, at least one positive observation.]

## Key Terms
| Term | Value | Section |
|------|-------|---------|
| Initial Term | | |
| Liability Cap | | |
| Governing Law | | |
| Insurance Required | | |
| Termination Notice | | |
| Amendment Rights | | |
| Force Majeure | | |
| Personal Guarantee | | |
| Auto-Renewal Notice Window | | |

## Definitions Audit
[List key defined terms, flag any that are circular, overly broad, undefined, or
materially expand/limit obligations. "No issues identified" if clean.]

## Mandatory Highlights
[Insurance / Governing Law & Jurisdiction / Liability & Indemnification /
Amendment Rights / Termination / Force Majeure — one subsection each]

## Red Flags Quick Scan
| Flag | Found | Section |
|------|-------|---------|
| No insurance clause | | |
| No governing law | | |
| Liability cap < 6 months | | |
| Uncapped indemnification | | |
| Unilateral amendment rights | | |
| No cure period | | |
| Offshore jurisdiction | | |
| No force majeure clause | | |
| Unlimited personal guarantee | | |
| Guarantee without cap or sunset | | |
| No "entire agreement" clause | | |
| No "no waiver" clause | | |
| Auto-renewal < 60-day opt-out | | |
| Undefined capitalized terms | | |
| Missing or incomplete exhibits | | |

## Risk Analysis
### Critical
[Clause title (§X), quoted language, issue, risk, market standard, negotiability, redline, fallback]
### Important | ### Minor / Watch | ### Reviewed & Acceptable

## Proposed Redlines
[Use the dual-party redline format above; include tier, rationale, walkaway, counterparty note]

## Negotiation Priority
| # | Issue | Ask | Fallback | Tier | Notes |
|---|-------|-----|----------|------|-------|

## Missing Provisions
| Provision | Priority | Why It Matters | Suggested Language |

## Jurisdiction-Specific Alerts
[Enforceability issues by governing law — non-compete void in CA, offshore venue
concerns, GDPR implications, etc.]

## Post-Signing Action Items
[Always populate — extract all date-triggered obligations from the contract automatically]

| Action | Deadline | Owner |
|--------|----------|-------|
| Calendar renewal opt-out deadline | [extracted date] | |
| Calendar termination notice window | [extracted date] | |
| Calendar rep & warranty survival expiry | [extracted date] | |
| Assign contract owner for compliance monitoring | Immediate | |
| Store executed copy in contract management system | Immediate | |
| Note and calendar all surviving obligations post-termination | On termination | |
| Schedule periodic compliance review | [cadence] | |
| [Any other date-triggered obligation from the contract] | | |
```

---

## Market Standard Benchmarks

| Provision | Standard | Yellow | Red |
|-----------|----------|--------|-----|
| Liability cap | 12 months' fees | 6–11 months | < 6 months |
| Insurance — GL | $1M / $2M aggregate | $500K | Absent |
| Insurance — E&O / Cyber | $1M each | $500K | Absent |
| Non-compete duration | 1–2 years | 3–4 years | 5+ years |
| Auto-renewal notice | 90+ days | 60–89 days | < 60 days |
| Auto-renewal price increase | CPI-linked or capped | Uncapped but disclosed | Silent / unilateral |
| Termination notice | Mutual, 60–90 days | One-sided, 30 days | Immediate |
| Indemnification | Mutual, capped | Asymmetric | Uncapped |
| Cure period (cause) | 30 days | 15 days | None |
| Amendment rights | Mutual written consent | 30-day unilateral notice | Sole discretion |
| SLA uptime | 99.9% with credits | 99.5% | < 99.5% or absent |
| Data export window | 90 days, standard format | 30 days | No right |
| Fee tail (broker) | 12–18 months | 24 months | Perpetual |
| M&A escrow | 10–15% for 12–18 mo | 15–20% for 18–24 mo | > 20% or > 24 mo |
| Force majeure triggers | Broad (incl. cyber, pandemic) | Narrow (Acts of God only) | Absent |
| Force majeure termination right | After 30–90 days | After 90–180 days | None / perpetual suspension |

---

## Negotiability Guide

| Rating | Meaning |
|--------|---------|
| High | Usually accepted: mutual termination, cure periods, data export, insurance, governing law fix |
| Medium | Depends on leverage: liability cap increase, SLA improvements, jurisdiction change |
| Low | Rarely changed: network rules, regulatory requirements, government standard form |
| None | Non-negotiable: card network mandates, GDPR, banking regulations |

---

## Document-Type Checklists (Abbreviated)

**NDA:** Direction (one-way/mutual), definition scope (check for over-breadth), term (3–5 yrs
typical), residuals clause, non-solicitation, return/destruction, governing law, jurisdiction.
*Personal guarantee: rare but flag if present.*

**SaaS/MSA:** Liability cap (12+ months), uptime SLA, suspension rights, data ownership,
export, deletion, price increase cap, auto-renewal notice (90+ days), subprocessors, DPA,
governing law, amendment rights, force majeure (include cyber).

**Service Agreement:** Scope/change orders, KPI/performance standards, acceptance criteria,
insurance, IP ownership (work-for-hire vs. license), termination, governing law, force majeure.

**Employment:** Compensation, at-will vs. fixed term, non-compete enforceability by state,
IP assignment (carve-out for personal projects), arbitration, governing law.
*Personal guarantee: flag immediately if present.*

**M&A (APA/SPA):** Purchase price mechanics, earnout, escrow/holdback (10–15% typical),
rep survival (12–24 months general), indemnification cap (10–20%), Rep & Warranty Insurance,
MAC carve-outs, governing law. *Personal guarantee / founder indemnity: review carefully.*

**Government/Infrastructure:** Performance bond (5–10%), insurance (CAR, GL, WC),
KPI/milestones, liquidated damages cap (≤10% of contract value), variation rights,
UNCITRAL/ICC arbitration, retention money, defects liability period, force majeure
(government action carve-out standard).

**Finder/Broker:** Fee % and base, tail period (12–24 months; perpetual = walk-away term),
exclusivity, FINRA registration if securities involved, governing law.

---

## Escalation & Subject Matter Expert Flags

Flag the following for non-legal expert review before finalization:

| Clause Area | Flag For | Trigger |
|-------------|----------|---------|
| Technology / IT terms (uptime, security standards, data architecture) | Technical SME | Any SaaS, infrastructure, or data agreement |
| Financial / payment mechanics (earnouts, revenue share, fee calculations) | Finance / CFO | M&A, revenue share, complex fee structures |
| Employment / HR terms (non-compete, comp, benefits) | HR / Employment counsel | Any employment or contractor agreement |
| Regulated industries (banking, healthcare, government) | Compliance / Regulatory counsel | Any regulated-sector contract |
| Personal guarantee | Independent legal counsel for the individual signatory | Whenever a personal guarantee is present |
| IP assignment or license (complex) | IP counsel | Broad assignments, software licensing, patent rights |

---

## Guardrails

- Not legal advice — always recommend attorney review for material terms before signing
- No hallucination — only reference and quote text actually present in the document
- Express uncertainty — say "this clause is ambiguous" rather than asserting one interpretation
- Proportionality — match depth to deal size; flag if deeper diligence is warranted
- Always include a "Reviewed & Acceptable" section — never make a review purely negative
- Dual-party mode: neither counsel should be unrealistically aggressive or capitulative
- Internal redline memos (rationale, walkaway, precedent) are never shared with counterparty
- Post-signing actions: always populate the Post-Signing Action Items table — extract all date-triggered obligations from the contract automatically rather than leaving blanks
- Version discipline: never finalize analysis on a document that may not be the latest version — confirm explicitly

*This review is for informational purposes only and does not constitute legal advice.*