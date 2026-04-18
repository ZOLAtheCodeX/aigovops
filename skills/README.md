# Skills

This directory contains the AIGovOps skills catalogue. Each subdirectory is a single skill, defined by a SKILL.md file.

A skill is a knowledge package that operationalizes a specific AI governance framework or framework section. Skills are framework-agnostic in the sense that they can be loaded by any agent runtime that reads SKILL.md or AGENTS.md (Hermes Agent, Claude Code, Codex CLI, Cursor, Jules, and others).

## Skill index

| Skill | Framework | Version | Status |
|---|---|---|---|
| [iso42001](iso42001/SKILL.md) | ISO/IEC 42001:2023 | 0.2.0-draft | draft |
| [nist-ai-rmf](nist-ai-rmf/SKILL.md) | NIST AI RMF 1.0 | 0.2.0-draft | draft |
| [eu-ai-act](eu-ai-act/SKILL.md) | EU AI Act (Regulation (EU) 2024/1689) | 0.1.0-stub | stub |

## Adding a new skill

Read [STYLE.md](../STYLE.md) and [CONTRIBUTING.md](../CONTRIBUTING.md) before starting. Every new skill must:

1. Live in a kebab-case directory under `skills/`.
2. Contain a SKILL.md with all seven required frontmatter fields and all six required section headers.
3. Have a matching `evals/<skill-name>/test_cases.yaml` with at least three validated test cases.
4. Be registered in the skill index above and in the repository [README.md](../README.md).

CI enforces frontmatter, section headers, and the presence of an evals file. CI does not currently enforce test case validation status; this is a maintainer review responsibility.

## Skill naming convention

- Use kebab-case.
- Match the framework identifier where possible (`iso42001`, `nist-ai-rmf`, `eu-ai-act`).
- For framework subsections, append the section: `iso42001-clause-6`, `nist-ai-rmf-govern`.
- Avoid version numbers in the skill name. Versioning lives in the SKILL.md frontmatter.
