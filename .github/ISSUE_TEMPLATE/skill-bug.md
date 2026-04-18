---
name: Skill bug
about: Report a skill output that is incorrect, ambiguous, or non-conformant with STYLE.md
title: "[skill-bug] <skill-name>: <short description>"
labels: [bug, skill]
assignees: []
---

## Skill

Skill name:
Skill version:
Skill path: `skills/<skill-name>/SKILL.md`

## Input that produced the incorrect output

Provide the exact input. Use a fenced code block.

```text
<input here>
```

## Expected output

Describe what the skill should have produced. Cite the authoritative framework reference that supports the expected output (use the citation format defined in [STYLE.md](../../STYLE.md)).

## Observed output

Provide the actual output. Use a fenced code block.

```text
<observed output here>
```

## Authoritative reference

Cite the clause, function, subcategory, article, or paragraph that the expected output is grounded in. Include a link to the authoritative source if available.

## Severity

- [ ] Critical: produces output that would fail an audit if used as evidence
- [ ] High: produces output that misrepresents the framework
- [ ] Medium: produces output that is technically correct but ambiguous or hard to use
- [ ] Low: cosmetic, formatting, or style issue

## Additional context

Any other information that would help reproduce, triage, or fix the issue.
