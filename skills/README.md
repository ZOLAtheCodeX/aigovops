# Skills

This directory contains the AIGovOps skills catalogue. Each subdirectory is a single skill, defined by a SKILL.md file.

A skill is a knowledge package that operationalizes a specific AI governance framework or framework section. Skills are framework-agnostic in the sense that they can be loaded by any agent runtime that reads SKILL.md or AGENTS.md (Hermes Agent, Claude Code, Codex CLI, Cursor, Jules, and others).

## Skill index

| Skill | Framework | Version | Status |
|---|---|---|---|
| [iso42001](iso42001/SKILL.md) | ISO/IEC 42001:2023 | 0.2.0 | released |
| [nist-ai-rmf](nist-ai-rmf/SKILL.md) | NIST AI RMF 1.0 | 0.2.0 | released |
| [eu-ai-act](eu-ai-act/SKILL.md) | EU AI Act (Regulation (EU) 2024/1689) | 0.2.0 | released |
| [colorado-ai-act](colorado-ai-act/SKILL.md) | Colorado Senate Bill 24-205 (Colorado AI Act) | 0.1.0 | released |
| [nyc-ll144](nyc-ll144/SKILL.md) | NYC Local Law 144 of 2021 (bias audit for AEDTs) | 0.1.0 | released |
| [california-ai](california-ai/SKILL.md) | California AI regulatory landscape primer | 0.1.0 | released |
| [canada-aida](canada-aida/SKILL.md) | Canada AI regulatory landscape primer (AIDA, PIPEDA, OSFI E-23, Treasury Board Directive, Quebec Law 25, Voluntary Code) | 0.1.0 | released |
| [cross-framework-crosswalk](cross-framework-crosswalk/SKILL.md) | Cross-framework coverage, gaps, and matrix queries (ISO 42001, NIST AI RMF, EU AI Act, UK ATRS, Colorado SB 205, NYC LL144, California) | 0.1.0 | released |
| [singapore-ai-governance](singapore-ai-governance/SKILL.md) | Singapore MAGF 2e, MAS FEAT Principles, AI Verify | 0.1.0 | released |
| [internal-audit](internal-audit/SKILL.md) | ISO/IEC 42001:2023, Clause 9.2 (Internal audit) | 0.1.0 | released |
| [ai-system-inventory](ai-system-inventory/SKILL.md) | AI system inventory operationalization (ISO/IEC 42001:2023 Clause 4.3 and 7.5, NIST AI RMF GOVERN 1.6, EU AI Act Article 11, UK ATRS, Colorado SB 205) | 0.1.0 | released |
| [incident-reporting](incident-reporting/SKILL.md) | External AI incident reporting (EU AI Act Article 73, Colorado SB 205 Sections 6-1-1702(7) / 6-1-1703(7), NYC LL144; composes with ISO/IEC 42001:2023 Clause 10.2 internal nonconformity tracking) | 0.1.0 | released |
| [supplier-vendor](supplier-vendor/SKILL.md) | Supplier and vendor governance (ISO/IEC 42001:2023 Annex A.10, EU AI Act Article 25 and 26(a), NYC LL144 Section 5-300, NIST GOVERN 6.1 and 6.2) | 0.1.0 | released |
| [evidence-bundle](evidence-bundle/SKILL.md) | Evidence bundle packaging for audits, attestations, and regulatory submissions (ISO/IEC 42001:2023 Clause 7.5.3, NIST AI RMF MANAGE 4.2, EU AI Act Articles 11 and 12 and 19, UK ATRS Section Impact assessment) | 0.1.0 | released |
| [certification-readiness](certification-readiness/SKILL.md) | Certification readiness assessment. Consumes an evidence bundle and returns a graduated readiness verdict (ISO/IEC 42001:2023 Clauses 9.2, 9.3, 10.1; EU AI Act Article 43, Annex VI, Annex VII; Colorado SB 205 Section 6-1-1706(3)) | 0.1.0 | released |
| [post-market-monitoring](post-market-monitoring/SKILL.md) | Post-market monitoring plan (EU AI Act Article 72, ISO/IEC 42001:2023 Clause 9.1, NIST AI RMF MANAGE 4.1 / 4.2, UK ATRS Section Risks) | 0.1.0 | released |
| [gpai-obligations](gpai-obligations/SKILL.md) | EU AI Act Articles 51 to 55 general-purpose AI (GPAI) obligations: systemic-risk classification, universal Article 53 obligations, Article 54 authorised-representative check, Article 55 systemic-risk additional obligations, downstream-integrator posture | 0.1.0 | released |
| [human-oversight](human-oversight/SKILL.md) | EU AI Act Article 14, ISO/IEC 42001:2023 Annex A controls A.9.2 / A.9.3 / A.9.4, NIST AI RMF MANAGE 2.3 dedicated human-oversight design (ability coverage, override capability, biometric dual-assignment, operator training, automation bias mitigations) | 0.1.0 | released |
| [robustness-evaluation](robustness-evaluation/SKILL.md) | Point-in-time robustness evaluation (EU AI Act Article 15, ISO/IEC 42001:2023 Annex A Control A.6.2.4, NIST AI RMF MEASURE 2.5 / 2.6 / 2.7) | 0.1.0 | released |
| [bias-evaluation](bias-evaluation/SKILL.md) | Fairness and bias evaluation across NYC LL144 Section 5-301 four-fifths rule, EU AI Act Article 10(4), Colorado SB 205 Section 6-1-1702(1), Singapore MAS Veritas (2022), ISO/IEC 42001 Annex A Control A.7.4, and NIST AI RMF MEASURE 2.11 | 0.1.0 | released |

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
