# STYLE.md

Canonical quality standard for AIGovOps. Read this before writing any skill, plugin, eval, or governance output.

## Definition of certification-grade

An output is certification-grade if a practicing ISO/IEC 42001 Lead Auditor or NIST AI RMF practitioner would accept it as audit evidence without correction. This is the minimum acceptable quality bar for any skill output, plugin output, or bundle output in this repository.

If you are not confident an output meets this bar, mark it explicitly as a draft and add a TODO referencing the specific gap.

## Citation formats

All framework references must use the exact formats below. Citation precision is part of the certification-grade standard. A correctly-numbered but mis-formatted citation will be rejected.

### ISO/IEC 42001:2023

Format: `ISO/IEC 42001:2023, Clause X.X.X`

Examples:

- `ISO/IEC 42001:2023, Clause 6.1.2`
- `ISO/IEC 42001:2023, Annex A, Control A.6.2.4`
- `ISO/IEC 42001:2023, Clause 8.3`

Use the full standard identifier on first reference in any document. Subsequent references in the same document may use `ISO 42001, Clause X.X.X` for brevity.

### NIST AI RMF 1.0

Format: `<FUNCTION> <Subcategory>` where FUNCTION is one of GOVERN, MAP, MEASURE, MANAGE.

Examples:

- `GOVERN 1.1`
- `MAP 3.5`
- `MEASURE 2.7`
- `MANAGE 4.3`

When referencing the framework as a whole on first use, write `NIST AI Risk Management Framework 1.0 (AI RMF 1.0)`.

### EU AI Act (Regulation (EU) 2024/1689)

Format: `EU AI Act, Article XX, Paragraph X` where applicable.

Examples:

- `EU AI Act, Article 9, Paragraph 2`
- `EU AI Act, Article 14`
- `EU AI Act, Annex III, Point 5`

For Recitals: `EU AI Act, Recital XX`. For Annexes: `EU AI Act, Annex X, Point Y`.

### Colorado AI Act (Senate Bill 24-205)

Format: `Colorado SB 205, Section <section>` where `<section>` follows the Colorado Revised Statutes codification under Title 6, Article 1, Part 17 (sections 6-1-1701 through 6-1-1707). Sub-paragraphs use parentheses as in the codified text.

Examples:

- `Colorado SB 205, Section 6-1-1701(3)`
- `Colorado SB 205, Section 6-1-1702(2)`
- `Colorado SB 205, Section 6-1-1703(4)(b)`
- `Colorado SB 205, Section 6-1-1706(4)`

Short-form `SB 205 s. 6-1-1703(3)` is acceptable in tabular contexts after the first full reference in the same document.

### UK Algorithmic Transparency Recording Standard (ATRS)

Format: `UK ATRS, Section <name>` where `<name>` is one of the eight canonical ATRS template v2.0 section names: `Owner and contact`, `Tool description`, `Tool details`, `Impact assessment`, `Data`, `Risks`, `Governance`, `Benefits`.

Examples:

- `UK ATRS, Section Owner and contact`
- `UK ATRS, Section Tool description`
- `UK ATRS, Section Impact assessment`

On first reference in any document, include the authoritative source URL: `https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies`. When pinning to a specific template version, append the version string (for example `ATRS Template v2.0`).

### NYC Local Law 144 of 2021 (bias audit for AEDTs)

Three citation forms are accepted and each has a fixed prefix:

- For the law itself: `NYC LL144`.
- For sections of the DCWP Final Rule (6 RCNY Chapter 5, Subchapter T, Sections 5-300 through 5-304): `NYC LL144 Final Rule, Section <n>`.
- For the implementing regulation chapter as a whole: `NYC DCWP AEDT Rules, Subchapter T`.

Examples:

- `NYC LL144`
- `NYC LL144 Final Rule, Section 5-301`
- `NYC LL144 Final Rule, Section 5-303`
- `NYC LL144 Final Rule, Section 5-304`
- `NYC DCWP AEDT Rules, Subchapter T`

On first reference in a document, include the authoritative source URL for the rule: `https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/`.

### California AI regulatory instruments

California has multiple instruments, each with its own citation format:

- CPPA Automated Decisionmaking Technology regulations: `CCPA Regulations (CPPA), Section <section>`.
- CCPA as amended by CPRA (statute): `California Civil Code, Section 1798.<section>`.
- SB 942 (AI Transparency Act) and AB 2013 (Training Data Transparency) provisions codified in the Business and Professions Code: `California Business and Professions Code, Section <section>`.
- California Attorney General AI guidance: `California Attorney General Guidance (YYYY-MM-DD)`.
- Vetoed SB 1047 referenced for completeness only: `California SB 1047 (vetoed)`.

Examples:

- `CCPA Regulations (CPPA), Section 7150`
- `California Civil Code, Section 1798.100`
- `California Business and Professions Code, Section 22757.1`
- `California Attorney General Guidance (2024-12-18)`

On first reference in a document, include the relevant portal URL: CPPA regulations (https://cppa.ca.gov/regulations/), California Legislative Information (https://leginfo.legislature.ca.gov/), California Attorney General AI hub (https://oag.ca.gov/ai).

### Canadian AI regulatory instruments

Canada has multiple instruments, each with its own citation format:

- AIDA (draft, Bill C-27, Part 3): `Canada AIDA (Bill C-27, Part 3), Section <n>`.
- AIDA (once in force): `AIDA Section <n>`.
- PIPEDA (statute): `PIPEDA, Section <n>`. Principles in Schedule 1: `PIPEDA, Schedule 1, Principle <n>`.
- Consumer Privacy Protection Act (proposed, Bill C-27, Part 1): `CPPA (Bill C-27, Part 1), Section <n>`.
- OSFI Guideline E-23 (Model Risk Management): `OSFI Guideline E-23, Paragraph <n>`.
- Treasury Board Directive on Automated Decision-Making: `Canada Directive on Automated Decision-Making, Subsection <n>`.
- Quebec Law 25: `Quebec Law 25, Section <n>`.
- Canada Voluntary Code of Conduct on Advanced Generative AI Systems: `Canada Voluntary AI Code (2023), Principle <n>`.

Examples:

- `Canada AIDA (Bill C-27, Part 3), Section 7`
- `PIPEDA, Section 6.1`
- `PIPEDA, Schedule 1, Principle 4.3`
- `OSFI Guideline E-23, Paragraph 18`
- `Canada Directive on Automated Decision-Making, Subsection 6.1`
- `Quebec Law 25, Section 12.1`
- `Canada Voluntary AI Code (2023), Principle Transparency`

On first reference in a document, include the relevant portal URL: ISED AIDA companion document (https://ised-isde.canada.ca/site/innovation-better-canada/en/artificial-intelligence-and-data-act-aida-companion-document), Parliament of Canada Bill C-27 (https://www.parl.ca/DocumentViewer/en/44-1/bill/C-27), Office of the Privacy Commissioner of Canada (https://www.priv.gc.ca/), OSFI (https://www.osfi-bsif.gc.ca/), Treasury Board Directive (https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai.html), Commission d'acces a l'information du Quebec (https://www.cai.gouv.qc.ca/).

### Singapore AI governance instruments

Four Singapore instruments each have a fixed citation prefix:

- Singapore Model AI Governance Framework, Second Edition (IMDA/PDPC, 2020): `Singapore MAGF 2e, Pillar <name>` for the four pillars (Internal Governance Structures and Measures; Determining the Level of Human Involvement; Operations Management; Stakeholder Interaction and Communication), or `Singapore MAGF 2e, Section <section>` for a specific section reference.
- MAS FEAT Principles (2018): `MAS FEAT Principles (2018), Principle <Fairness|Ethics|Accountability|Transparency>`. One of the four fixed principle names.
- AI Verify (IMDA 2024): `AI Verify (IMDA 2024), Principle <name>` where `<name>` is one of the 11 AI Verify principles (`accountability`, `data-governance`, `human-agency-oversight`, `inclusive-growth`, `privacy`, `reproducibility`, `robustness`, `safety`, `security`, `transparency`, `fairness`).
- MAS Veritas methodology (2019 through 2022): `MAS Veritas (2022)` for the methodology as a whole. Phase-specific references use `MAS Veritas Document <n>: <phase>` (for example `MAS Veritas Document 1: Fairness`).

Examples:

- `Singapore MAGF 2e, Pillar Internal Governance Structures and Measures`
- `Singapore MAGF 2e, Pillar Operations Management`
- `MAS FEAT Principles (2018), Principle Fairness`
- `AI Verify (IMDA 2024), Principle human-agency-oversight`
- `MAS Veritas (2022)`

On first reference in a document, include the authoritative source URL: MAGF 2e (https://www.pdpc.gov.sg/help-and-resources/2020/01/model-ai-governance-framework), AI Verify Foundation (https://aiverifyfoundation.sg/), MAS (https://www.mas.gov.sg/).

### Statutory-presumption relationship (crosswalk)

Crosswalk output uses a fixed 7-value relationship vocabulary defined in `plugins/crosswalk-matrix-builder/data/SCHEMA.md`. One value, `statutory-presumption`, is canonical and load-bearing and must not be flattened into `satisfies` or `partial-satisfaction` in any citation or downstream artifact.

`statutory-presumption` applies when a statute explicitly recognizes conformance with another framework as rebuttable evidence of compliance. The canonical reference example is `Colorado SB 205, Section 6-1-1706(3)`, which names conformance with the NIST AI Risk Management Framework 1.0 or ISO/IEC 42001:2023 as a rebuttable presumption of reasonable care for a deployer defending against an attorney-general action. `Colorado SB 205, Section 6-1-1706(4)` extends the same posture to the affirmative-defense-on-cure pathway. Every `statutory-presumption` row in the crosswalk must carry confidence `high`, must cite the statute itself, and must be asymmetric (`bidirectional: false`). Downstream plugins citing a statutory-presumption row must preserve the vocabulary value verbatim; rewriting to `satisfies` is a citation-quality defect.

## Prohibited language

The following are not acceptable in any output produced by a skill, plugin, or contributor in this repository.

### Em-dashes

The U+2014 character is prohibited. Use one of:

- A colon, when introducing an explanation or list.
- A comma, when joining two related independent clauses.
- Parentheses, when adding a parenthetical aside.
- Two sentences, when the clauses are genuinely independent.

### Emojis in any output

No emojis in skill outputs, plugin outputs, README files, comments, commit messages, or PR descriptions. Governance documents are read in audit contexts. Emojis undermine the seriousness of the output and are not portable across all rendering systems used in audit workflows.

### Hedging phrases

The following phrases and close variants are prohibited:

- "may want to consider"
- "might be helpful to"
- "could potentially"
- "it is possible that"
- "you might find"
- "we suggest you might"

Governance outputs must be definite. State the determination. If a determination requires human judgment, write "Requires human determination." or "Auditor judgment required." rather than hedging.

## Required SKILL.md sections

Every SKILL.md must contain the following section headers in this exact order:

```markdown
## Overview
## Scope
## Framework Reference
## Operationalizable Controls
## Output Standards
## Limitations
```

A SKILL.md missing any of these sections will fail CI. The sections may contain TODO markers during stub stages, but the headers themselves must always be present.

## Required SKILL.md frontmatter fields

Every SKILL.md must begin with YAML frontmatter containing all of the following fields:

| Field | Type | Description |
|---|---|---|
| `name` | string (kebab-case) | The skill identifier. Must match the directory name. |
| `version` | string (semver) | Skill version. Stub versions use the suffix `-stub` (for example `0.1.0-stub`). |
| `description` | string (multi-line allowed) | What the skill does and which framework or framework section it covers. |
| `frameworks` | list of strings | Authoritative framework identifiers (for example `ISO/IEC 42001:2023`, `NIST AI RMF 1.0`). |
| `tags` | list of strings | Searchable tags. |
| `author` | string | Skill author. Use `AIGovOps Contributors` for community contributions. |
| `license` | string | License identifier. Always `MIT` for skills in this repository. |

Frontmatter completeness is enforced by CI.

## Output formatting

- Use Markdown for all human-readable outputs. Use JSON for structured outputs intended for programmatic consumption.
- Use ATX-style headers (`#`, `##`, `###`) not Setext.
- Use fenced code blocks with language identifiers.
- Use tables for any tabular comparison or mapping. Plain prose is acceptable for narrative content.
- One blank line between sections. No trailing whitespace.
