# AGENTS.md

Instructions for AI agents (Jules, Claude Code, Codex CLI, Cursor, and others) operating on this repository.

## What this repository is

AIGovOps is the framework-agnostic catalogue of AI governance skills, plugins, and bundles. It is the operational layer for AI governance frameworks (NIST AI RMF, ISO/IEC 42001, EU AI Act, and others). This repository contains data and configuration. It is not a running agent. The runtime that consumes this catalogue is [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw).

## Directory structure

| Path | Purpose |
|---|---|
| `skills/` | Framework knowledge as SKILL.md files. One directory per skill. Each contains a SKILL.md with frontmatter and required sections. |
| `plugins/` | Executable units that produce governance artifacts. One directory per plugin with code, README, and any supporting files. |
| `bundles/` | Packaged combinations of skills and plugins for a specific certification or compliance objective. Defined as bundle.yaml. |
| `evals/` | Test cases used by the evaluation harness to validate skill outputs against authoritative framework text. One directory per skill, mirroring `skills/` layout. |
| `.github/workflows/` | CI for frontmatter linting, markdown linting, eval presence checks, and the weekly framework-monitor cron. |
| `.github/ISSUE_TEMPLATE/` | Templates for skill bugs and framework updates. |

## Files that must NEVER be modified autonomously

The following files require a human-approved GitHub issue before any change. Do not edit, rename, or delete them on your own initiative even if a refactor or cleanup seems beneficial.

- `SECURITY.md`
- `LICENSE`
- Any file under `persona/` (this directory does not exist in this repo, but the rule applies if it is added)

If you believe one of these files needs a change, open an issue describing the change and the justification. Wait for a human to approve before editing.

## Quality gates that must pass before opening a PR

1. CI must pass. This includes frontmatter lint, markdown lint, and eval presence checks. See `.github/workflows/ci.yml`.
2. Any new skill must have a corresponding `evals/<skill>/test_cases.yaml` with a minimum of three test cases. See [STYLE.md](STYLE.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
3. All written content must follow [STYLE.md](STYLE.md) exactly. The style standard is the canonical quality reference for this repository.

## SKILL.md frontmatter format

Every SKILL.md must begin with YAML frontmatter containing the following required fields:

```yaml
---
name: <kebab-case-skill-id>
version: <semver>
description: >
  Multi-line description of what this skill does and which framework or framework section it covers.
frameworks:
  - <framework-id>
tags:
  - <tag>
author: <author-name-or-AIGovOps Contributors>
license: MIT
---
```

The skill body must contain the following section headers, in order:

```markdown
## Overview
## Scope
## Framework Reference
## Operationalizable Controls
## Output Standards
## Limitations
```

These section requirements are enforced by CI. Do not omit a section even if you have no content for it.

## Prohibited content in any output

The following are not acceptable in any file in this repository, including code comments, generated outputs, and PR descriptions:

- Emojis. Use plain text. CI does not currently enforce this, but PRs containing emojis will be rejected.
- Em-dashes (the U+2014 character). Use a colon, a comma, parentheses, or restructure the sentence.
- Hedging language. Specifically prohibited phrases include "may want to consider", "might be helpful to", "could potentially", and similar. Governance outputs must be definite. If a determination requires human judgment, state that explicitly.

## How to raise a framework-update issue

When a monitored framework (NIST AI RMF, ISO 42001, EU AI Act, or any other framework cited in `skills/`) publishes a revision, errata, or new guidance:

1. Open a new issue using the [framework-update template](.github/ISSUE_TEMPLATE/framework-update.md).
2. Include the framework name, the change summary, the source URL, and the date the change was published.
3. List the skills in this repository that reference the changed clause, function, article, or paragraph.
4. Do not modify any SKILL.md files until the issue has been reviewed and assigned.

The framework-monitor workflow (`.github/workflows/framework-monitor.yml`) opens these issues automatically when it detects upstream changes. If you are an agent acting on a detected change, your role is to populate the issue with the affected skill list, not to edit the skills.
