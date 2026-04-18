# Contributing to AIGovOps

Thank you for considering a contribution. Read [STYLE.md](STYLE.md) before writing anything. STYLE.md is the canonical quality standard and is non-negotiable.

## Accepted contribution types

| Type | What it is |
|---|---|
| New skills | A new SKILL.md and matching evals directory covering a framework or framework section not yet in the catalogue. |
| Plugin additions | A new executable unit that produces a concrete governance artifact (audit log, SoA row, risk register entry, gap assessment, and so on). |
| Eval test cases | Additional test cases for existing skills, validated against authoritative framework text. |
| Bug reports | A skill output, plugin output, or framework citation that is incorrect, ambiguous, or non-conformant with STYLE.md. |
| Framework update implementations | Code or content changes implementing an upstream framework revision (in response to an open framework-update issue). |

## Quality bar

All contributions must meet the certification-grade standard defined in [STYLE.md](STYLE.md). All skill contributions must:

- Pass CI (frontmatter lint, markdown lint, eval presence check).
- Include a minimum of three eval test cases in `evals/<skill>/test_cases.yaml`.
- Use the exact citation formats specified in STYLE.md.
- Contain none of the prohibited language listed in STYLE.md.

## Skill submission checklist

Before opening a PR for a new skill, confirm every item below.

1. The skill directory is named in kebab-case and lives at `skills/<skill-name>/`.
2. The directory contains a SKILL.md with all seven required frontmatter fields.
3. The SKILL.md contains all six required section headers in the exact order specified in STYLE.md.
4. All framework references in the SKILL.md use the citation formats specified in STYLE.md.
5. A matching `evals/<skill-name>/test_cases.yaml` exists with at least three test cases.
6. Each eval test case has been validated against the authoritative framework text and the `validated_by` field is populated.
7. The SKILL.md contains no prohibited language (em-dashes, emojis, hedging phrases).
8. The SKILL.md links to the most recent authoritative source for each framework cited.
9. The skill is listed in the Skills table in the repository [README.md](README.md).
10. The skill version follows semver, and stub versions use the `-stub` suffix.

## Plugin submission checklist

Before opening a PR for a new plugin, confirm every item below.

1. The plugin directory is named in kebab-case and lives at `plugins/<plugin-name>/`.
2. The directory contains a README.md describing inputs, outputs, and example invocation.
3. The plugin code (Python, shell, or other) has docstrings or header comments explaining each public function or entry point.
4. The plugin produces deterministic output for deterministic input. Any non-determinism must be explicitly documented in the README.
5. The plugin output, if it cites framework controls, uses the citation formats specified in STYLE.md.
6. The plugin handles missing or malformed input by raising a clear error, not by producing degraded output.
7. The plugin contains no prohibited language in code, comments, or output.
8. The plugin is listed in the Plugins table in the repository [README.md](README.md).

## How to submit

1. Fork the repository.
2. Create a feature branch named `add-<skill-name>` or `add-<plugin-name>` or `fix-<short-description>`.
3. Make your changes. Run CI locally if possible.
4. Open a PR against `main` with a description that explains the contribution and links to any related issue.
5. Respond to review feedback. Maintainers may request changes to bring the contribution to certification-grade quality.

## Reporting bugs

Use the [skill-bug issue template](.github/ISSUE_TEMPLATE/skill-bug.md). Include the skill name, the input that produced the incorrect output, the expected output, and the authoritative framework reference that supports the expected output.

## Reporting framework changes

Use the [framework-update issue template](.github/ISSUE_TEMPLATE/framework-update.md). Include the framework name, the change summary, the source URL, the publication date, and a list of skills in this repository that reference the changed material.
