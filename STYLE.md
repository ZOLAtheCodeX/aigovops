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
