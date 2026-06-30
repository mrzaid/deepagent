# Contract Drafting Skill

Covers drafting, reviewing, and negotiating any legal agreement — MSA, SOW, NDA, Employment, SaaS, DPA, IP Assignment, Amendment, and more. Produces annotated drafts with bracketed placeholders, risk callouts, and alternative clause language aligned to DSD's internal standards. All output is for attorney review only and does not constitute legal advice.

---

## Step 1: Intake — REQUIRED FIRST. Never draft without completing this.

| Input | Options / Notes |
|-------|-----------------|
| Document type | Full agreement / clause / amendment / SOW / schedule / term sheet |
| Mode | Draft from scratch / modify existing / convert deal memo / **review incoming counterparty paper** |
| User's party | Full legal entity name, entity type, state of formation — never a trade name or DBA |
| Counterparty | Same — if unknown: `[CONFIRM LEGAL ENTITY]` |
| Signatory | Name + title for each party — flag if title doesn't clearly imply authority |
| Drafting bias | **Balanced** (default) / DSD-favorable / Counterparty-friendly / Neutral review of incoming paper |
| Governing law | Default: Washington state — override if: CA nexus; EU/UK party; mandatory-forum state applies |
| Dispute resolution | AAA arbitration Seattle (DSD default) / litigation / tiered escalation |
| Personal data? | Yes → DPA required; cross-border → SCCs / UK Addendum required |
| International nexus? | Yes → flag OFAC, EAR/ITAR export controls, currency, withholding tax, VAT |

**Bias reference:** Balanced = mutual market-standard protections. DSD-favorable = strengthen indemnity, IP, liability cap carve-outs, tighten counterparty obligations. Counterparty-friendly = reduce friction, soften DSD obligations (use only when instructed; note exposure). Reviewing incoming = flag every deviation from DSD standard; produce redline commentary.

---

## Step 2: Pre-Draft Legal Checkpoints — Run before writing any clause.

**2.1 Jurisdiction Enforceability Screen**

| Issue | Action |
|-------|--------|
| Any party in California? | Non-competes void; mandatory CA venue for employees; `[CONFIRM WITH COUNSEL — CA NEXUS]` |
| EU/UK counterparty? | GDPR mandatory; US arbitration may not be enforceable; `[CONFIRM GOVERNING LAW WITH COUNSEL]` |
| Consumer (not B2B)? | Do NOT use this template — flag for specialist; consumer protection law applies |
| Cross-border tech transfer? | EAR/ITAR may require export license: `[CONFIRM EXPORT CONTROLS WITH COUNSEL]` |
| International payment? | Include OFAC rep; flag withholding tax and VAT treatment |

**2.2 Party & Authority Check**
Confirm full legal name matches state-of-formation records (not DBA). Confirm entity type and good standing. If signatory title doesn't clearly imply authority: `// NOTE: Confirm authority — request board resolution or officer certificate for transactions above DSD delegation threshold.`

**2.3 Consideration Check**
Verify each party receives something of value. If any obligation is illusory ("may request" / "at our discretion"): `// RISK: Illusory consideration — may render agreement unenforceable. Tighten obligation language.` For amendments: confirm new consideration exists or modification rights exist in the parent agreement.

**2.4 IP Chain-of-Title Screen**
Before drafting IP provisions: (a) Does any deliverable include pre-existing DSD IP? → License, not assignment. (b) Any third-party IP or open source? → `[IDENTIFY ALL THIRD-PARTY IP AND OPEN-SOURCE — CONFIRM LICENSE COMPATIBILITY]`. (c) Does deliverable qualify as work-for-hire under 17 U.S.C. § 101? If not, explicit written assignment required — a license does not transfer title. (d) Joint development by both parties? → Address joint ownership explicitly; never leave ambiguous.

---

## Step 3: Contract Architecture — Build every full agreement in this order.

`[REQUIRED]` sections are never omitted, even when scoping down.

1. Cover / Title Block `[REQUIRED]` — title, draft watermark, version number, date
2. Parties `[REQUIRED]` — full legal names, entity types, states of formation, addresses
3. Recitals — background and business purpose
4. Definitions `[REQUIRED]` — all capitalized terms defined before first use
5. Scope / Obligations `[REQUIRED]` — who does what, by when, to what standard; use "commercially reasonable efforts," not absolute guarantees
6. Payment Terms — amounts, schedule, invoice process, late fees, disputed invoice procedure
7. Term & Renewal — start date, duration, auto-renewal notice (90+ days DSD standard), renewal caps
8. Representations & Warranties — mutual baseline plus document-specific reps
9. Confidentiality `[REQUIRED]`
10. IP Ownership & License `[REQUIRED]`
11. Data Protection — required if personal data is processed
12. Insurance — GL $1M/$2M aggregate; E&O/Cyber $1M each (DSD standard)
13. Indemnification
14. Limitation of Liability `[REQUIRED]`
15. Termination `[REQUIRED]`
16. Survival `[REQUIRED]` — enumerate every surviving section by number and name
17. Post-Termination Obligations — data return/deletion (90-day window, standard format), IP reversion
18. Dispute Resolution
19. Governing Law & Jurisdiction `[REQUIRED]`
20. Notices
21. Assignment & Change of Control — anti-assignment on M&A trigger required
22. Audit Rights — required for SaaS, data processing, usage-based fees
23. Publicity & Press — restrict use of party name, logo, relationship disclosure without written consent
24. Severability
25. Waiver — failure to enforce one breach does not waive future enforcement rights
26. No Third-Party Beneficiaries
27. Force Majeure
28. Amendments — mutual written consent required (DSD standard); flag unilateral rights
29. Entire Agreement
30. Counterparts / E-Signature — note ESIGN/UETA compliance; flag if international party
31. Signature Blocks `[REQUIRED]` — full legal name, signatory name, title, date
32. Exhibits / Schedules — SOW, DPA, Insurance Certificate, Fee Schedule

---

## Step 4: Eight Mandatory Drafting Blocks — Required in every full agreement.

**4.1 Governing Law & Jurisdiction**
Default: Washington state law + AAA Commercial Arbitration in Seattle, WA. Deviation requires legal review. Always pair governing law with matching jurisdiction clause — never leave either blank. Include jury waiver: `// NOTE: Jury waiver enforceability varies by state; may require separate acknowledgment.`

**4.2 Limitation of Liability**
DSD standard: **2× fees paid or payable in the prior 12 months**. Market fallback: 12 months' fees. Flag anything below 6 months as Red. Cap must be in ALL CAPS to satisfy conspicuousness requirements in many states. **Carve-outs (always enumerate — never rely on implication):** fraud, willful misconduct, gross negligence, confidentiality breach, IP infringement, data breach / security incident, death or bodily injury, payment obligations, indemnification obligations. `// RISK: A cap without explicit carve-outs may limit recovery even for intentional misconduct. Courts enforce caps literally.`

**4.3 Indemnification**
Mutual preferred. Must specify: categories of covered claims; third-party claim trigger (not direct claims); prompt written notice + right to control defense + indemnitee cooperation; settlements require prior written consent of indemnitor (not to be unreasonably withheld); insurance backing. IP indemnification: if DSD deliverables infringe third-party IP, DSD indemnifies — include remedy options (procure license, modify, replace, or refund). `// NOTE: IP indemnification is a significant DSD exposure. Confirm IP clearance before execution.`

**4.4 Confidentiality**
Define broadly (written, oral, visual, electronic). Required elements: carve-outs (public domain without breach; independently developed with documentation; rightfully received from third party; legally compelled with prompt notice and cooperation to resist); standard of care = same as recipient protects own information, no less than reasonable care; use restriction = solely for purposes of this agreement; permitted disclosure = employees/contractors with need to know under binding obligations; return/destruction within 30 days of termination with written certification; publicity restriction = neither party may disclose existence or terms without prior written consent, except as required by law. `// NOTE: Trade secret protection obligations survive termination indefinitely per DTSA — enumerate this in the survival clause.`

**4.5 Termination**
Must include all five triggers: (1) Convenience — 30-day written notice, mutual; (2) Material breach — 15-day written cure period; immediate on incurable breach; (3) Insolvency — immediate; define as bankruptcy filing, assignment for benefit of creditors, appointment of receiver, or cessation of business; (4) Data breach / security incident — immediate; (5) FCPA / sanctions violation — immediate, no cure. Post-termination: 90-day data return/deletion in standard format with certification; IP reversion; accrued payment obligations survive.

**4.6 IP Ownership**

| IP Category | Default Ownership | Condition |
|-------------|------------------|-----------|
| DSD Pre-existing Materials | DSD retains | License to client for deliverable use only |
| Residual IP / methodology | DSD retains always | Include explicit residuals clause |
| Deliverables | Assigned to client | Only upon receipt of full payment |
| Client Pre-existing Materials | Client retains | License to DSD for performance only |
| Joint Development | `[ADDRESS EXPLICITLY — NO DEFAULT]` | |
| Open-Source Components | Third-party license governs | List all; confirm license compatibility |

License-back to DSD: non-exclusive, royalty-free right to use anonymized deliverables for portfolio and methodology purposes. `// RISK: Do not include license-back for PII or materials that would identify the client without explicit consent.`

**4.7 Survival**
Enumerate every surviving section by number and name. Never use "provisions that by their nature survive" as the sole survival language — courts have split on this. Minimum surviving sections: Definitions, accrued Payment Obligations, Confidentiality, IP Ownership, Indemnification, Limitation of Liability, Dispute Resolution, Governing Law, Post-Termination Obligations.

**4.8 Anti-Corruption, Sanctions & Export Controls**
FCPA: representation, prohibition on improper payments, reporting obligation, DSD right to suspend/terminate immediately without cure on credible suspicion. OFAC (required in all agreements): each party represents it is not on any OFAC SDN List, not organized in a comprehensively sanctioned country, not the target of any applicable trade or economic sanctions; prompt notification on any change. Export Controls (required where technology is a deliverable): parties comply with all applicable EAR/ITAR regulations; no export, re-export, or transfer without required authorizations; `[CONFIRM WITH COUNSEL IF DELIVERABLES MAY BE ITAR-CONTROLLED]`.

---

## Step 5: DSD-Specific Standards

**MSA:** Exact legal entity names only — no trade names. No services without fully executed SOW. All scope changes require signed change orders. SOW prevails over MSA in direct conflict. SaaS/Platform: add uptime SLA, maintenance window, data portability rights (90-day export, open format), acceptable use policy reference. Source code escrow: `[CONFIRM IF ESCROW REQUIRED]` for critical platform agreements. International clients: DPA execution required if personal data crosses borders; SCCs or UK Addendum as applicable; address data residency explicitly.

**SOW:** Must reference governing MSA by exact name and effective date. Must define: project purpose, scope with explicit out-of-scope carve-outs, deliverables with acceptance criteria, milestones, fee structure, payment schedule, change order process, project governance and escalation contacts. Use "commercially reasonable efforts" — not absolute guarantees. Cross-reference MSA for IP and confidentiality; do not restate.

**NDA:** Direction (one-way/mutual). Definition scope with exclusions explicit. Term 3–5 years; trade secret protection survives indefinitely per DTSA. Resist residuals clauses — they can effectively nullify the NDA; flag if counterparty insists. Non-solicitation of personnel: 12 months post-disclosure, mutual. Return/destruction: 30 days with written certification; DSD may retain one archival copy in counsel files.

**Amendment/Addendum:** Identify parent agreement by exact name and effective date. State which provisions are modified vs. fully restated (restated = full replacement; amended = specific language change — different legal effect). Confirm consideration. Confirm all other terms remain in full force. Re-execute signature blocks. Flag if scope is extensive enough to warrant full restatement instead.

---

## Step 6: Document Versioning & Workflow

Every draft must carry: document title, version number (v0.1 = first internal draft; v1.0 = first external transmission; v1.1 = first counterparty redline), issue date, and `DRAFT — FOR REVIEW ONLY` watermark. Include an open-items tracker listing all unresolved `[BRACKETED PLACEHOLDERS]` with section references at the top of every draft.

**Pre-transmission checklist:**
- [ ] All `[REQUIRED]` fields populated
- [ ] All `// NOTE`, `// RISK`, `// ALT` annotations stripped
- [ ] Signatory authority confirmed
- [ ] Jurisdiction enforceability screen complete
- [ ] OFAC representation included
- [ ] Attorney review completed
- [ ] Version number and date in header

**Receiving counterparty redlines:** Compare every deviation against DSD standard. Produce DSD response positions: Accept / Accept with modification / Reject with alternative / Escalate to counsel. Never accept without escalation: removal of liability cap carve-outs; IP ownership ambiguity; unilateral modification rights; missing survival clause; missing OFAC rep; cure-period removal for termination for cause.

---

## Output Template

```
[DOCUMENT TITLE]
Version [X.X] | [DATE] | DRAFT — FOR REVIEW ONLY

ATTORNEY REVIEW RECOMMENDED — This draft is for internal review only, has not been reviewed
by qualified legal counsel, and does not constitute legal advice. Do not execute without
attorney review.

OPEN ITEMS: [COUNT] unresolved placeholders as of [DATE]
[LIST EACH [BRACKETED PLACEHOLDER] WITH SECTION REFERENCE]

──────────────────────────────────────────────────────────

This [Agreement Type] ("Agreement") is entered into as of [EFFECTIVE DATE]
by and between [PARTY A FULL LEGAL NAME], a [STATE] [ENTITY TYPE] ("Company"),
and [PARTY B FULL LEGAL NAME], a [STATE] [ENTITY TYPE] ("[SHORT NAME]").

RECITALS
WHEREAS, [background / business purpose];
NOW, THEREFORE, in consideration of the mutual covenants herein, the parties agree:

1. DEFINITIONS
   1.1 "[Defined Term]" means [definition].
   [ALL CAPITALIZED TERMS DEFINED BEFORE FIRST USE]

[CONTINUE THROUGH ARCHITECTURE §§ 2–32 AS APPLICABLE]
```

**Annotation conventions:**
- `[BRACKETED PLACEHOLDER]` — missing business term; must be resolved before execution
- `[CONFIRM WITH COUNSEL]` — legal judgment required; do not resolve without attorney review
- `[CONFIRM LEGAL ENTITY]` — party name unconfirmed; must verify before execution
- `// NOTE:` — internal drafting flag; strip before external transmission
- `// ALT (DSD-favorable):` — stronger alternative; strip before transmission
- `// ALT (counterparty-friendly):` — softer alternative; strip before transmission
- `// RISK:` — material exposure callout; strip before transmission

---

## .docx Export Rules

When user requests to create, generate, produce, or export as a file:

| Rule | Detail |
|------|--------|
| Preserve all placeholders verbatim | Every `[BRACKETED PLACEHOLDER]`, `[BLANK]`, `[TBD]`, `[CONFIRM WITH COUNSEL]`, `[CONFIRM LEGAL ENTITY]` must appear exactly in the .docx |
| Strip all annotation comments | Remove all `// NOTE:`, `// ALT:`, `// RISK:` before writing to file |
| Retain attorney-review disclaimer | This is not an annotation — keep it at top of every exported file |
| Include open-items tracker | Reproduce unresolved placeholder list at top of document |
| Filename convention | `[DocType]-[PartyA]-[PartyB]-v[X.X]-DRAFT-[YYYYMMDD].docx` |
| INCOMPLETE- prefix | If any `[REQUIRED]` field or party identity is unresolved, prefix filename with `INCOMPLETE-` |

---

## Market Standard Benchmarks

| Provision | DSD Standard | Yellow Flag | Red Flag |
|-----------|-------------|-------------|---------|
| Liability cap | 2× prior 12-mo fees | 1× fees | < 6 months or uncapped |
| Carve-outs from cap | All 9 enumerated | Missing fraud/willful | Cap applies to all claims |
| Insurance — GL | $1M / $2M aggregate | $500K | Absent |
| Insurance — E&O / Cyber | $1M each | $500K | Absent |
| Termination for convenience | 30 days mutual | One-sided, 30 days | Immediate / absent |
| Cure period (for cause) | 15–30 days | < 15 days | None |
| Amendment rights | Mutual written consent | 30-day unilateral notice | Sole discretion |
| Non-compete duration | 1–2 years | 3–4 years | 5+ years |
| Auto-renewal notice | 90+ days | 60–89 days | < 60 days |
| Data export window | 90 days, open/standard format | 30 days | No right or proprietary format |
| IP assignment timing | On full payment | On substantial completion | On signing (no payment condition) |
| Governing law | Washington or mutually agreed | Counterparty-only jurisdiction | No governing law clause |
| Survival clause | Named sections enumerated | "By nature" language only | Absent |
| OFAC representation | Both parties | One party only | Absent |
| Dispute resolution | AAA arbitration | Foreign arbitration body | Courts only in counterparty's jurisdiction |
| Change of control | Triggers assignment consent | Silent | Unlimited assignment permitted |
| Audit rights (SaaS/data) | Annual, reasonable notice | Biennial | Absent |

---

## Guardrails

- **Not legal advice** — attorney-review disclaimer on every full agreement draft; never remove it
- **No hallucination** — use `[BRACKETED PLACEHOLDER]` rather than inventing any name, number, date, or term
- **Express uncertainty** — use `[CONFIRM WITH COUNSEL]` on any unsettled legal question; never assert a conclusion on jurisdiction-specific enforceability
- **Jurisdiction overrides defaults** — Washington law and AAA arbitration are defaults, not absolutes; always flag when local mandatory law may override
- **Proportionality** — match depth and formality to deal size and risk; a $5K SOW does not need the full 32-section architecture; a $5M platform MSA does
- **Counterparty paper** — when reviewing incoming drafts, produce redline commentary against DSD standard; do not rewrite in counterparty's favor without explicit instruction
- **Strip annotations before any external transmission** — presence of `// NOTE`, `// RISK`, or `// ALT` in a transmitted document is a material drafting error
- **Version every draft** — no unnumbered drafts; counterparty redlines must always be tracked against a versioned baseline

*This skill is for internal use only. Output does not constitute legal advice.*