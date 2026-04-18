# CLAUDE.md

Registration and operating instructions for Claude Code working on this repository.

## Load order

1. Load [STYLE.md](STYLE.md) before writing any skill, plugin, or eval content. STYLE.md is the canonical quality reference for this repository.
2. Load [AGENTS.md](AGENTS.md) for repository structure, prohibited content rules, and quality gates.
3. Load [CONTRIBUTING.md](CONTRIBUTING.md) for submission checklists.

## Skill registration

All skills in `skills/` are registered for use in this repository. Each subdirectory of `skills/` is a single skill. Read the SKILL.md in each directory to learn what the skill does.

When extending or modifying a skill, run the eval harness against the corresponding `evals/<skill>/test_cases.yaml` before opening a PR.

## Operating rules

- Never modify `SECURITY.md` or `LICENSE` without an approved GitHub issue.
- Never modify any file under `persona/` if such a directory exists.
- Run the eval harness after any skill modification. CI will reject PRs that change a skill without a corresponding eval test case update.
- Follow STYLE.md for citation formats, prohibited language, and required SKILL.md sections.

## Anti-patterns to avoid

- Adding emojis to any file.
- Using em-dashes (U+2014). Use a colon, comma, parentheses, or restructure.
- Using hedging language ("may want to consider", "might be helpful to", "could potentially").
- Creating a SKILL.md that omits any of the six required section headers.
- Adding a skill without a matching `evals/<skill>/test_cases.yaml` containing at least three test cases.

## Cross-repository context

The runtime that consumes this catalogue is at https://github.com/ZOLAtheCodeX/aigovclaw. When making changes that affect skill loading or directory structure, consider whether the runtime needs a corresponding update.
