# Evals

This directory contains the evaluation harness for AIGovOps skills. Every skill in `skills/` must have a matching directory here containing a `test_cases.yaml` file with at least three test cases.

## Purpose

The eval harness validates skill outputs against known-correct framework mappings. A skill that produces an output not matching the expected framework citation, control mapping, or clause reference fails the eval. Failed evals block PR merges.

This is the mechanism by which the catalogue maintains its certification-grade standard at scale. Without evals, regressions in skill output quality are invisible until a human auditor catches them. With evals, regressions surface in CI.

## Layout

```
evals/
├── <skill-name>/
│   └── test_cases.yaml
└── <skill-name>/
    └── test_cases.yaml
```

The directory name under `evals/` must match the skill directory name under `skills/` exactly.

## Test case schema

Each `test_cases.yaml` contains a top-level `test_cases` list. Every entry has the following fields.

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique identifier within this file. Convention: `<skill-name>-NNN`. |
| `description` | string | yes | One-line description of what this test case validates. |
| `input` | string or object | yes | The input given to the skill. |
| `expected_outputs` | list of strings | yes | The outputs the skill must produce. |
| `clause_references` | list of strings | yes | Authoritative framework citations supporting the expected output. Use the citation format defined in [STYLE.md](../STYLE.md). |
| `status` | string | yes | One of `stub`, `validated`, `deprecated`. |
| `validated_by` | string or null | yes | Name of the validator. Required when `status: validated`. |

## Validation requirement

A test case is considered valid only when `status: validated` and `validated_by` is populated with the name of a contributor who has confirmed the expected outputs against the authoritative framework text. Stub test cases do not count toward the minimum-three requirement for a skill to merge.

## Running evals locally

Phase 3. The eval runner is not yet implemented. CI currently only verifies that `test_cases.yaml` files exist for each skill (the eval-stub-check job in `.github/workflows/ci.yml`).
