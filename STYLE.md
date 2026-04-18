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
