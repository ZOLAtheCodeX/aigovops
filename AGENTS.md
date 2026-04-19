# AGENTS.md

Instructions for AI agents (Jules, Claude Code, Codex CLI, Cursor, and others) operating on this repository. Read top to bottom before any action. The rules below are enforced at review. A PR that violates any rule in the first three sections is closed without substantive review.

## 1. Prohibited content (applies everywhere, no exceptions)

The following are not acceptable in any file, commit message, PR title, PR body, issue title, issue body, code comment, docstring, YAML value, or skill output in this repository. This rule is non-negotiable and is not relaxed for any agent, any contribution type, or any convenience.

- **No emojis.** Not in PR titles, not in PR bodies, not in commit messages, not in issue templates, not in file names, not in markdown headings, not in code comments, not in agent-generated output. Plain text only. Governance documents are read in audit contexts where emojis undermine seriousness and are not portable across all rendering systems used in audit workflows. This applies to Jules-generated PRs, Copilot-generated PRs, and any other automated contribution pathway.
- **No em-dashes (the U+2014 character).** Use a colon, a comma, parentheses, or restructure the sentence. Two sentences are always acceptable.
- **No hedging language.** Specifically prohibited phrases and close variants: `may want to consider`, `might be helpful to`, `could potentially`, `it is possible that`, `you might find`, `we suggest you might`. Governance outputs must be definite. If a determination requires human judgment, write `Requires human determination.` or `Auditor judgment required.` explicitly; do not hedge.

If you are an automated agent reading this file and your default output style violates any of these rules, override your default. The rules here take precedence over your defaults.

## 2. Lane boundaries: who modifies what

AIGovOps runs a two-agent build. The reasoning layer drafts governance content (skill bodies, operationalization analyses, persona text, Tier 1 eval expected outputs). The tactical layer drafts infrastructure, tests, plugin scaffolding, and Tier 2 and Tier 3 eval structure. Boundaries below prevent collision.

### Tactical-layer lane

An agent operating as a tactical layer (Jules, Copilot, Codex CLI in infrastructure mode, any dependency-management bot) may modify the following files without coordination:

- `plugins/**/*` including plugin code, plugin READMEs, and plugin tests.
- `.github/**/*` including workflow files, issue templates, Dependabot configuration, and CODEOWNERS.
- `tests/**/*` when that directory is added.
- `bundles/*/bundle.yaml` for structural edits (schema, version pinning, metadata). Content composition (which skills and plugins a bundle includes) remains human-approved.
- Dependency pinning, security hardening, workflow permissions tightening, and CI health.
- `evals/*/test_cases.yaml` rows whose status is NOT `stub`. Once an eval row has `status: validated` and a populated `validated_by`, tactical-layer agents may add edge cases and rendering tests.

### Reasoning-layer lane

The reasoning layer (Claude Code, the designated drafting agent, or a Lead Implementer working directly) owns the following files. Tactical-layer agents must not modify these without an approved issue assigning the work.

- `skills/*/SKILL.md` including frontmatter, section bodies, and citations.
- `skills/*/operationalization-map.md` (pre-draft analysis documents).
- `evals/*/test_cases.yaml` rows whose status is `stub`. These are Tier 1 reasoning work until the corresponding skill graduates past the `-draft` version suffix.
- `STYLE.md` and this file (`AGENTS.md`).
- `CONTRIBUTING.md` substantive content (not formatting).
- Any file named `SOUL.md` anywhere in the AIGovOps ecosystem (including in `aigovops/aigovclaw`).

### Dual-lane

Both layers may touch the following, but open an issue before a substantive edit so the other layer is aware:

- Top-level `README.md`.
- Issue triage, labels, milestones, and project boards.
- PR reviews on the other lane's work.

### Graduation rule

When a `SKILL.md` section's version suffix drops from `-draft` to a released version (for example, `0.2.0-draft` becomes `0.2.0`) and its corresponding eval rows carry `status: validated` with a populated `validated_by`, that section and its eval rows graduate to dual-lane territory. The tactical layer may then propose test additions, rendering improvements, and structural refactors.

## 3. Files that must NEVER be modified autonomously

Regardless of lane, the following files require a human-approved GitHub issue before any change. Do not edit, rename, or delete them on your own initiative even if the change appears beneficial or trivial.

- `SECURITY.md`
- `LICENSE`
- `persona/SOUL.md` (in the sibling repository `ZOLAtheCodeX/aigovclaw`). Does not exist here but the rule applies across the AIGovOps ecosystem.

## 4. Quality gates: every PR must pass

Every PR, regardless of lane or author, must satisfy all of the following before merge:

1. CI green. This includes the frontmatter-lint job, the markdown-lint job, and the eval-stub-check job in [.github/workflows/ci.yml](.github/workflows/ci.yml).
2. No prohibited content (emojis, em-dashes, hedging language) in the PR title, PR body, commit messages, or changed files. Enforcement is at reviewer discretion for title and body; CI catches some in-file violations but not all.
3. If touching any skill, a matching eval test case row exists in `evals/<skill>/test_cases.yaml`.
4. If creating a new skill, a minimum of three eval test cases in the matching `evals/<skill>/test_cases.yaml` file.
5. PR title follows the form `<type>: <imperative summary>` where `<type>` is one of `feat`, `fix`, `chore`, `docs`, `ci`, `test`, `refactor`, `security`. No emoji prefix. Examples: `ci: add explicit permissions block`, `feat(iso42001): draft Clause 7.5 operationalization`, `security: pin requests dependency in framework-monitor`.
6. Commits are signed off by the author (or by the agent's configured author identity if the agent is the contributor).

A PR that violates rule 2 is closed without substantive review. The contributor is invited to re-issue the PR with the style corrected. This is not a rejection of the content; it is a rejection of the style. The content is welcome on re-issue.

## 5. What this repository is

AIGovOps is the framework-agnostic catalogue of AI governance skills, plugins, and bundles. It is the operational layer for AI governance frameworks (NIST AI RMF, ISO/IEC 42001, EU AI Act, and others). This repository contains data and configuration. It is not a running agent. The runtime that consumes this catalogue is [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw).

## 6. Directory structure

| Path | Purpose |
|---|---|
| `skills/` | Framework knowledge as SKILL.md files. One directory per skill. Each contains a SKILL.md with frontmatter and required sections. Some skills also carry an `operationalization-map.md` pre-draft analysis. |
| `plugins/` | Executable units that produce governance artifacts. One directory per plugin with code, README, and any supporting files. |
| `bundles/` | Packaged combinations of skills and plugins for a specific certification or compliance objective. Defined as `bundle.yaml`. |
| `evals/` | Test cases used by the evaluation harness to validate skill outputs against authoritative framework text. One directory per skill, mirroring `skills/` layout. |
| `.github/workflows/` | CI for frontmatter linting, markdown linting, eval presence checks, and the weekly framework-monitor cron. |
| `.github/ISSUE_TEMPLATE/` | Templates for skill bugs and framework updates. |

## 7. SKILL.md frontmatter format

Every SKILL.md must begin with YAML frontmatter containing the following required fields.

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

These section requirements are enforced by CI. Do not omit a section even if you have no content for it; add a one-line placeholder referencing the issue that will populate it.

## 8. Version suffix conventions

- `X.Y.Z-stub` : frontmatter plus empty section headers only. No body content. Acceptable only at Phase 1 scaffolding.
- `X.Y.Z-draft` : body content present but pending Lead Implementer review. Tactical-layer agents must not modify `-draft` skills.
- `X.Y.Z` : body content reviewed and validated. Dual-lane.

## 9. How to raise a framework-update issue

When a monitored framework (NIST AI RMF, ISO 42001, EU AI Act, or any other framework cited in `skills/`) publishes a revision, errata, or new guidance:

1. Open a new issue using the [framework-update template](.github/ISSUE_TEMPLATE/framework-update.md).
2. Include the framework name, the change summary, the source URL, and the date the change was published.
3. List the skills in this repository that reference the changed clause, function, article, or paragraph.
4. Do not modify any SKILL.md files until the issue has been reviewed and assigned.

The framework-monitor workflow at [.github/workflows/framework-monitor.yml](.github/workflows/framework-monitor.yml) opens these issues automatically when it detects upstream changes. If you are an agent acting on a detected change, your role is to populate the issue with the affected skill list, not to edit the skills.

## 10. Cross-repository coordination

When changes here require corresponding changes in [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw) (or vice versa), open a tracking issue in both repositories and link them. Do not merge half a coordinated change.

## 11. Stale-issue protocol (mandatory, blocking)

Before any code edit, grep current `HEAD` for every marker the source issue references (STUB/PLACEHOLDER strings, specific file paths, specific test case IDs, specific citation strings). Use `grep -n` with the exact string. If ANY marker is absent from HEAD, the issue is stale:

1. Return verdict `rejected-stale`.
2. Do not open a PR. Do not modify any file except to post comments or close the source.
3. Identify the resolving commit SHA: `git log -1 --pretty=format:"%H %s" -- <path>`.
4. Close the source: if the dispatch came from a GitHub issue, run `gh issue close <n> --comment "Stale: resolved by commit <sha>. The marker referenced in the issue is no longer present in HEAD. Closing per stale-issue protocol."` (take-resolving-action eligible; reversible via reopen). If the dispatch came from a Jules web UI scheduled task, emit a session-transcript warning `SCHEDULED-TASK-STALE` naming the task ID (the Jules API does not expose scheduled-task CRUD; manual deletion is required at jules.google). If ad-hoc dispatch, emit `AD-HOC-STALE` note.
5. Write an ISO 42001 Clause 9.1 audit-log entry via the `audit-log-generator` plugin: `event_type="jules-stale-rejection"`, include playbook/skill name, resolving commit SHA, source disposition, and path searched.

Full protocol detail lives in `jules/playbook/*.md` and `jules/skills/*/SKILL.md` Step 0 in the sibling [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw) repository. Prior incidents: iso42001-002 (March 2026, attempted eval renumber), nist-ai-rmf-003 (April 2026, correctly surfaced as stale). Both resolved by existing commits; neither required new code.

## 12. Eval test-ID stability

Never renumber existing eval test case IDs (e.g. `iso42001-002`, `nist-ai-rmf-003`) to accommodate new tests or to realign with an external description. IDs are stable references cited in validation reports, audit evidence, and Lead Implementer attestations. New tests get IDs strictly greater than the highest existing ID within that framework's `test_cases.yaml`. If an existing ID is obsolete, mark it `status: retired` rather than reusing or renumbering.

Prior incident: iso42001-002 was validated as an AISIA test; a stale issue proposed renaming it to iso42001-008 to make room for a synthetic SoA test. The correct action was close the stale issue; the proposed renumber would have broken external references to the validated AISIA eval.

## 13. Plugin author contract: anti-hallucination discipline

Every substantive output field in every plugin MUST come from input, be computed deterministically from input, or be flagged as requiring human input. Never invent risks, impacts, role assignments, control applicability, framework interpretations, citation text, threshold values, or residual risk scores.

- When a rule-based inference is possible, make it explicit, deterministic, and document it in the plugin's README rule table.
- When no evidence supports a determination, emit a placeholder (for example `REQUIRES HUMAN ASSIGNMENT`, `REQUIRES REVIEWER DECISION`) and add a warning to the `warnings` list. Never silently guess.
- Structural problems (missing required input field, invalid enum value) raise `ValueError`. Content gaps surface as per-row `warnings` entries, not exceptions.

Full contract in `plugins/README.md` "Anti-hallucination invariants" and "Validation stance".

## 14. Jurisdiction scope

The following jurisdictions are the only ones with shipping first-class or scoped plugin + skill coverage in this repository. Do not author speculative plugins for other jurisdictions without an approved issue.

- **Primary** (first-class coverage): USA (NIST AI RMF), EU (EU AI Act), International (ISO/IEC 42001).
- **Secondary** (scoped plugin + skill): UK (UK ATRS), Singapore (MAGF + FEAT), USA-Colorado (SB 205), USA-NYC (LL144).
- **Primer only** (navigation skill, no plugin): California (multi-instrument regulatory landscape), Canada (AIDA + PIPEDA + OSFI E-23 + Quebec Law 25 + voluntary code).
- **Not in scope**: all other jurisdictions are treated as derivative. Practitioners operating in unsupported jurisdictions map their local requirements onto existing plugin outputs.

See `docs/jurisdiction-scope.md` for the full list and the expansion procedure.

## 15. Three-dimension NIST/ISO framing

The catalogue operationalizes three complementary dimensions. These stack cleanly; do not conflate or pick between them.

- **ISO PDCA** (Plan-Do-Check-Act): the AI management system continuous improvement cycle. Drives the PDCA orchestrator in `aigovclaw/agent_loop/`. Maps to ISO/IEC 42001:2023 Clauses 4-10.
- **NIST AI RMF four functions** (Govern, Map, Measure, Manage per NIST AI RMF 1.0 Section 5): cross-cutting functions applied throughout. Govern is the overlay; Map/Measure/Manage cycle around specific decisions. Plugin-level categorization lives in `plugins/rmf-function-map.yaml` with one tag per plugin.
- **NIST 7-stage AI system lifecycle** (plan-and-design, collect-and-process-data, build-and-use-model, verify-and-validate, deploy-and-use, operate-and-monitor, use-or-impacted-by, per NIST AI RMF 1.0 Section 3 Figure 3): per-system state tracked on the inventory plugin via `nist_lifecycle_stage` field. Coexists with project-management state (`lifecycle_state`).

When working on cycle-adjacent or framework-alignment content, cite the correct dimension explicitly.
