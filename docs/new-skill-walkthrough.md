# Adding a New Skill: A Walkthrough

A step-by-step guide to adding a new governance framework to the AIGovOps catalogue. The existing skills (`iso42001`, `nist-ai-rmf`, `eu-ai-act`) followed this exact pattern; use them as reference implementations.

This document is for humans or agents (Jules, Codex CLI, Claude Code) authoring a new skill. Read [AGENTS.md](../AGENTS.md) and [STYLE.md](../STYLE.md) first if you haven't.

## When to add a new skill

Add a skill when:

1. A new framework in your organization's scope is not covered (state-level AI laws, sector-specific regulation, voluntary industry standards).
2. A significantly different profile of an existing framework warrants separate treatment (an AI 600-1-style profile for NIST; a sector overlay for ISO 42001).
3. A cross-framework crosswalk is material enough to warrant its own skill (rare; usually handled as a `framework` flag on existing plugins).

Do NOT add a skill for:

- Small framework revisions (handle via the existing skill's version bump).
- Single-organization customizations (belongs in the user's own fork or config, not the upstream catalogue).
- Aspirational roadmap items (wait until the framework is published).

## The eight-step skill-authoring workflow

### Step 1: create the skill directory

```bash
mkdir -p skills/<skill-name>
```

Use kebab-case for the name (for example `nyc-ll144`, `iso-27001-ai-overlay`). The name becomes the directory under `skills/`, the key in `evals/`, and the SKILL.md frontmatter `name` field.

### Step 2: draft the operationalization map first

`skills/<skill-name>/operationalization-map.md` is where the intellectual work lives. Before writing SKILL.md body content, produce the map:

1. Enumerate every clause, article, subcategory, or control in the framework.
2. For each, assign an operationalizability class:
   - **A (automatable)**: plugin produces compliant output from structured input without human judgment.
   - **H (hybrid)**: plugin produces a draft; human reviews and approves.
   - **J (human judgment required)**: automation assists information gathering at most; automating past that point produces evidence auditors reject.
3. For each, identify the candidate artifact type from the AIGovOps vocabulary (`AISIA-section`, `risk-register-row`, `SoA-row`, `role-matrix`, `audit-log-entry`, `KPI`, `nonconformity-record`, `review-minutes`, `data-register`, and so on). Extend the vocabulary only with strong rationale.
4. Assign a leverage rating (H/M/L) based on frequency, tedium, and error-rate of manual production.
5. Note crosswalks to `iso42001`, `nist-ai-rmf`, `eu-ai-act` in a Notes column. Shared operationalizations flag which existing plugin serves this framework via its `framework` flag.

The map's output: a priority-ranked Tier 1/Tier 2/Tier 3 backlog. Tier 1 items are what the SKILL.md body expands in depth.

Reference: `skills/iso42001/operationalization-map.md` shows the full pattern.

### Step 3: draft SKILL.md

Every SKILL.md must have exactly six section headers in this order (enforced by CI):

1. `## Overview`
2. `## Scope`
3. `## Framework Reference`
4. `## Operationalizable Controls`
5. `## Output Standards`
6. `## Limitations`

Frontmatter (also CI-enforced) must contain: `name`, `version`, `description`, `frameworks`, `tags`, `author`, `license`.

For the body:

- **Overview**: one-paragraph explanation of the framework and what this skill operationalizes.
- **Scope**: explicit in-scope and out-of-scope items. What this skill covers; what it does not cover (legal advice, sector-specific overlays, and so on).
- **Framework Reference**: authoritative source citation, document structure, related frameworks, enforcement timeline (if staged like EU AI Act).
- **Operationalizable Controls**: **the biggest section.** Tier 1 items get full treatment with: requirement summary, inputs, process, output artifact, citation anchors, auditor acceptance criteria, human-review gate. Tier 2 items get abbreviated bullets. Tier 3 items get prescriptive prose only (judgment-bound; do not automate).
- **Output Standards**: reference STYLE.md; note any framework-specific conventions (applicability dating for EU AI Act, dual-citation rendering for cross-framework orgs).
- **Limitations**: what the skill does NOT do. Certification, legal advice, final audit conclusions.

Set `version: 0.1.0-stub` if body sections are empty; `0.2.0-draft` if drafted but unvalidated; `0.2.0` or later once validated against the authoritative framework text.

### Step 4: eval stubs

`evals/<skill-name>/test_cases.yaml` must exist with at minimum 3 test cases.

Per-case schema (enforced at review, not CI):

```yaml
test_cases:
  - id: <skill-name>-001
    tier: T1.N
    description: |
      Human-readable description of what this case validates.
    input: <structured input or prose>
    expected_outputs:
      - "Specific expected output claim"
      - "Specific expected output claim"
    clause_references:
      - "ISO/IEC 42001:2023, Clause X.X"
    status: stub
    validated_by: null
    authored_by: "AIGovOps Contributors"
```

Stubs are authored alongside the SKILL.md draft. A Lead Implementer validation pass flips each `status: stub` to `status: validated` with `validated_by` populated. Stubs do not count toward the minimum-three validated-eval merge requirement.

### Step 5: register in indexes

Update two files:

- `skills/README.md`: add a row to the skill index table.
- Top-level `README.md`: add a row to the Skills table.

Status starts at `stub`, moves to `draft`, then `released`.

### Step 6: if a new plugin is needed, follow the plugin-author contract

If the skill requires a new plugin (either a framework-distinctive operationalization like `metrics-collector` for NIST, or a new artifact type), follow `plugins/README.md`:

1. Copy the structure of an existing plugin (`plugins/role-matrix-generator/` is the simplest reference).
2. Declare the plugin's `AGENT_SIGNATURE`, `REQUIRED_INPUT_FIELDS`, `VALID_<ENUM>` tuples.
3. Implement `generate_<artifact>(inputs) -> dict`, `render_markdown(artifact) -> str`, and `render_csv` if tabular.
4. Validate structurally (raise `ValueError`) and content-wise (surface warnings).
5. Write tests that cover happy path, every validation error, every warning trigger, citation format, rendering, and no-em-dashes.
6. Register in `plugins/README.md` and top README.
7. Add a tool entry in `aigovclaw/tools/aigovops_tools.py` with the schema and safety properties.
8. Add an aigovclaw workflow file in `aigovclaw/workflows/<name>.md` if the plugin has a dedicated workflow.

Reference: `plugins/data-register-builder/` and `plugins/applicability-checker/` are the most recent plugin additions, both done per this pattern.

### Step 7: extend existing plugins with a framework flag when possible

Before authoring a new plugin, check whether an existing plugin covers the operationalization with a framework flag. Examples:

- `risk-register-builder` supports `framework: iso42001 | nist | dual`. Adding EU AI Act is a citation-map extension, not a new plugin.
- `aisia-runner` serves iso42001 Clause 6.1.4, NIST MAP 1.1/3.1/3.2/5.1, and EU AI Act Article 27 FRIA via the same plugin.
- `role-matrix-generator`, `nonconformity-tracker`, `metrics-collector` all support multi-framework rendering.

Extending is cheaper than adding. Six of nine Tier 1 EU AI Act operationalizations reused existing iso42001 plugins via framework flags; only `applicability-checker` and `high-risk-classifier` (Phase 4) needed new plugins.

### Step 8: validation pass

Before graduating from `-draft` to released:

1. Every `[verify]` marker in the SKILL.md and operationalization-map is resolved.
2. Every eval test case has `status: validated` and `validated_by` populated.
3. The plugin tests pass (including newly-written ones for this skill).
4. The consistency audit at `tests/audit/consistency_audit.py` reports 0 findings.
5. The integration tests at `tests/integration/test_plugin_chain.py` pass (if new plugin added).
6. CI is green on the PR.

A Lead Implementer or equivalent practitioner for the framework attests validation. The attesting name appears in the eval `validated_by` fields and in the SKILL.md version bump commit message.

## Structured-data files alongside SKILL.md

Some frameworks benefit from structured-data files (YAML or JSON) that plugins read at runtime rather than hard-coding. Example: `skills/eu-ai-act/enforcement-timeline.yaml` and `skills/eu-ai-act/delegated-acts.yaml` power the `applicability-checker` plugin.

Use structured data when:

- The data changes over time (framework revisions, delegated acts) and updates should not require plugin code changes.
- Multiple plugins read the same reference (the EU AI Act timeline is referenced by `applicability-checker`, the gap-assessment when targeting EU AI Act, and future plugins).
- The data has a clear schema that would make narrative prose either redundant or hard to keep consistent.

Structured-data files live at the skill level (not the plugin level), because they describe the framework, not a specific plugin's behavior.

## Checklist

Before opening a PR:

- [ ] `skills/<name>/operationalization-map.md` drafted with A/H/J classification, priority-ranked backlog, open questions.
- [ ] `skills/<name>/SKILL.md` drafted with complete frontmatter and all six section headers.
- [ ] `evals/<name>/test_cases.yaml` has at least 3 cases.
- [ ] Skill registered in `skills/README.md` and top-level `README.md`.
- [ ] If new plugin: `plugins/<name>/` with plugin.py, tests/test_plugin.py, README.md, all tests pass.
- [ ] If new plugin: registered in `plugins/README.md`, top-level README, and `aigovclaw/tools/aigovops_tools.py`.
- [ ] If new plugin: `aigovclaw/workflows/<name>.md` wired to the plugin.
- [ ] Consistency audit: 0 findings (`python3 tests/audit/consistency_audit.py`).
- [ ] Integration tests: green (`python3 tests/integration/test_plugin_chain.py`).
- [ ] CI green on the PR.

## What reviewers look for

- Structural correctness: all six section headers, frontmatter fields, eval schema compliance.
- Citation format per STYLE.md throughout the body.
- Prohibited-content compliance: no em-dashes, no emojis, no hedging.
- Operationalizability classifications are defensible: J-class items genuinely judgment-bound; A-class items genuinely automatable.
- Tier 1 operationalizations cover the framework's highest-leverage requirements; Tier 3 items are justifiably judgment-only.
- Cross-framework extension preferred over new-plugin authoring where possible.
- Eval stubs are concrete enough that a Lead Implementer validation pass is possible.

## Reference implementations

- **iso42001**: certification-grade management-system skill. First-authored, deepest coverage. Reference for "full-framework" skill structure.
- **nist-ai-rmf**: voluntary risk-framework skill. Reference for cross-referencing to iso42001 instead of duplicating shared operationalizations.
- **eu-ai-act**: regulation-based skill with structured data files. Reference for staged-enforcement frameworks and for integrating delegated-act tracking.

The three existing skills covered the three major framework archetypes; any new skill should fit one of these patterns or justify why it doesn't.
