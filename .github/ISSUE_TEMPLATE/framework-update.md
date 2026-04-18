---
name: Framework update
about: Report an upstream framework revision, errata, or new guidance that affects this catalogue
title: "[framework-update] <framework-name>: <short change description>"
labels: [framework-update]
assignees: []
---

## Framework

Framework name (use the official identifier, for example `ISO/IEC 42001:2023`, `NIST AI RMF 1.0`, `EU AI Act`): 

## Change summary

A one-paragraph description of what changed. Identify the change type:

- [ ] New framework version or revision
- [ ] Errata or correction to an existing version
- [ ] New supplementary guidance, profile, or companion document
- [ ] Withdrawal or supersession

## Source

URL of the authoritative source: 

Publication date of the change: 

## Affected material

List the specific clauses, functions, subcategories, articles, paragraphs, or annexes that changed. Use the citation format defined in [STYLE.md](../../STYLE.md).

## Affected skills in this repository

List every skill in `skills/` that references the changed material. If you are unsure, list the candidates and mark them with `(verify)`.

- `skills/<skill-name>/SKILL.md`: <which sections of the SKILL.md reference the changed material>

## Affected evals

List every `evals/<skill>/test_cases.yaml` that contains a test case grounded in the changed material.

## Proposed action

- [ ] Update SKILL.md content to reflect the change
- [ ] Update eval test cases to reflect the change
- [ ] Add a deprecation note if a previously-cited clause was withdrawn
- [ ] Other (describe)

## Coordination notes

If this update requires changes to [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw) workflows, list them here.
