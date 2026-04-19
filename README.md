[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Build](https://img.shields.io/badge/build-pending-lightgrey.svg)](.github/workflows/ci.yml)

# AIGovOps

**The operational layer for AI governance.**

AIGovOps turns AI governance frameworks (NIST AI RMF, ISO/IEC 42001, EU AI Act, and others) into executable artifacts. This repository is the framework-agnostic catalogue. It contains three artifact types:

- **Skills** are knowledge packages. Each skill is a SKILL.md file describing how to operationalize a specific framework or framework section. Skills are loaded by any agent that reads SKILL.md or AGENTS.md (Hermes Agent, Claude Code, Codex CLI, Cursor, Jules, and others).
- **Plugins** are execution units. Each plugin is a runnable artifact (Python, shell, or other) that produces a concrete governance output: an audit log entry, a Statement of Applicability, a risk register row.
- **Bundles** are packaged combinations of skills and plugins for a specific certification or compliance objective (for example, ISO 42001 certification readiness).

## Quick install

| Target | Command |
|---|---|
| Hermes Agent (via AIGovClaw) | `git clone https://github.com/ZOLAtheCodeX/aigovclaw && cd aigovclaw && ./install.sh` |
| Claude Code | Clone this repo into `~/.claude/skills/aigovops/` |
| Codex CLI | Clone this repo into your Codex skills directory and load via `AGENTS.md` |
| Other agents | Reference SKILL.md files directly from `skills/` |

## Command-line interface

The `aigovops` CLI orchestrates every plugin in this repo against a single `organization.yaml`. One command produces the complete AIMS artifact set.

```bash
export PATH="$PWD/bin:$PATH"
aigovops doctor
aigovops run --org examples/organization.example.yaml --output /tmp/run1
```

See [cli/README.md](cli/README.md) for the full subcommand reference and the `organization.yaml` schema.

## Skills

| Skill | Framework | Status |
|---|---|---|
| [iso42001](skills/iso42001/SKILL.md) | ISO/IEC 42001:2023 | 0.2.0 |
| [nist-ai-rmf](skills/nist-ai-rmf/SKILL.md) | NIST AI RMF 1.0 | 0.2.0 |
| [eu-ai-act](skills/eu-ai-act/SKILL.md) | EU AI Act (Regulation (EU) 2024/1689) | 0.2.0 |
| [colorado-ai-act](skills/colorado-ai-act/SKILL.md) | Colorado Senate Bill 24-205 (Colorado AI Act) | 0.1.0 |
| [uk-atrs](skills/uk-atrs/SKILL.md) | UK Algorithmic Transparency Recording Standard | 0.1.0 |
| [nyc-ll144](skills/nyc-ll144/SKILL.md) | NYC Local Law 144 of 2021 (bias audit for AEDTs) | 0.1.0 |
| [california-ai](skills/california-ai/SKILL.md) | California AI regulatory landscape primer (CPPA ADMT, CCPA/CPRA, SB 942, AB 2013, AB 1008, SB 1001, AB 1836) | 0.1.0 |
| [canada-aida](skills/canada-aida/SKILL.md) | Canada AI regulatory landscape primer (AIDA draft, PIPEDA, OSFI E-23, Treasury Board Directive, Quebec Law 25, Voluntary Code) | 0.1.0 |
| [singapore-ai-governance](skills/singapore-ai-governance/SKILL.md) | Singapore MAGF 2e, MAS FEAT Principles, AI Verify | 0.1.0 |
| [ai-system-inventory](skills/ai-system-inventory/SKILL.md) | AI system inventory operationalization (ISO/IEC 42001:2023 Clause 4.3 and 7.5, NIST AI RMF GOVERN 1.6, EU AI Act Article 11, UK ATRS, Colorado SB 205) | 0.1.0 |
| [evidence-bundle](skills/evidence-bundle/SKILL.md) | Evidence bundle packaging for audits, attestations, and regulatory submissions (ISO/IEC 42001:2023 Clause 7.5.3, NIST AI RMF MANAGE 4.2, EU AI Act Articles 11 and 12 and 19, UK ATRS Section Impact assessment) | 0.1.0 |
| [certification-readiness](skills/certification-readiness/SKILL.md) | Certification readiness assessment. Consumer of evidence bundles; returns graduated readiness verdict (ISO/IEC 42001:2023 Clauses 9.2, 9.3, 10.1; EU AI Act Article 43; Colorado SB 205 Section 6-1-1706(3)) | 0.1.0 |
| [bias-evaluation](skills/bias-evaluation/SKILL.md) | Fairness and bias evaluation operationalization across NYC LL144 four-fifths rule, EU AI Act Article 10(4), Colorado SB 205, Singapore MAS Veritas, ISO/IEC 42001 A.7.4, and NIST AI RMF MEASURE 2.11 | 0.1.0 |
| [post-market-monitoring](skills/post-market-monitoring/SKILL.md) | Post-market monitoring plan (EU AI Act Article 72, ISO/IEC 42001:2023 Clause 9.1, NIST MANAGE 4.1 / 4.2, UK ATRS Section Risks) | 0.1.0 |
| [human-oversight](skills/human-oversight/SKILL.md) | Human-oversight design (EU AI Act Article 14, ISO/IEC 42001:2023 Annex A controls A.9.2 / A.9.3 / A.9.4, NIST AI RMF MANAGE 2.3) | 0.1.0 |

## Plugins

| Plugin | Output Artifact | Status |
|---|---|---|
| [audit-log-generator](plugins/audit-log-generator/) | ISO 42001-compliant audit log (JSON + Markdown) | 0.1.0 |
| [role-matrix-generator](plugins/role-matrix-generator/) | ISO 42001-compliant role and responsibility matrix (JSON + Markdown + CSV) | 0.1.0 |
| [risk-register-builder](plugins/risk-register-builder/) | ISO 42001 and NIST AI RMF-compliant AI risk register (JSON + Markdown + CSV) | 0.1.0 |
| [soa-generator](plugins/soa-generator/) | ISO 42001-compliant Statement of Applicability (JSON + Markdown + CSV) | 0.1.0 |
| [aisia-runner](plugins/aisia-runner/) | ISO 42001 and NIST AI RMF-compliant AI System Impact Assessment (JSON + Markdown) | 0.1.0 |
| [nonconformity-tracker](plugins/nonconformity-tracker/) | ISO 42001 Clause 10.2 and NIST MANAGE 4.2 nonconformity and corrective-action records (JSON + Markdown) | 0.1.0 |
| [management-review-packager](plugins/management-review-packager/) | ISO 42001 Clause 9.3.2 management review input package (JSON + Markdown) | 0.1.0 |
| [internal-audit-planner](plugins/internal-audit-planner/) | ISO 42001 Clause 9.2 internal audit programme + schedule + criteria + impartiality assessment (JSON + Markdown + CSV) | 0.1.0 |
| [metrics-collector](plugins/metrics-collector/) | NIST AI RMF MEASURE 2.x metrics + AI 600-1 overlay with threshold-breach routing (JSON + Markdown + CSV) | 0.1.0 |
| [gap-assessment](plugins/gap-assessment/) | Framework gap assessment for ISO 42001, NIST AI RMF, or EU AI Act (JSON + Markdown + CSV) | 0.1.0 |
| [data-register-builder](plugins/data-register-builder/) | ISO 42001 A.7 and EU AI Act Article 10 data register (JSON + Markdown + CSV) | 0.1.0 |
| [applicability-checker](plugins/applicability-checker/) | EU AI Act applicability by target date + system classification (JSON + Markdown) | 0.1.0 |
| [high-risk-classifier](plugins/high-risk-classifier/) | EU AI Act Article 5, 6, Annex I, Annex III risk-tier classification (JSON + Markdown) | 0.1.0 |
| [uk-atrs-recorder](plugins/uk-atrs-recorder/) | UK Algorithmic Transparency Recording Standard record, Tier 1 and Tier 2 (JSON + Markdown + CSV) | 0.1.0 |
| [colorado-ai-act-compliance](plugins/colorado-ai-act-compliance/) | Colorado SB 205 developer and deployer compliance record (JSON + Markdown + CSV) | 0.1.0 |
| [nyc-ll144-audit-packager](plugins/nyc-ll144-audit-packager/) | NYC Local Law 144 bias audit public-disclosure and candidate-notice bundle (JSON + Markdown + CSV) | 0.1.0 |
| [crosswalk-matrix-builder](plugins/crosswalk-matrix-builder/) | Cross-framework coverage, gap, or matrix query result (JSON + Markdown + CSV) | 0.1.0 |
| [singapore-magf-assessor](plugins/singapore-magf-assessor/) | Singapore MAGF 2e pillar assessment with MAS FEAT layering for financial services (JSON + Markdown + CSV) | 0.1.0 |
| [ai-system-inventory-maintainer](plugins/ai-system-inventory-maintainer/) | Validated, versioned AI system inventory with per-system regulatory applicability and cross-framework references (JSON + Markdown + CSV) | 0.1.0 |
| [incident-reporting](plugins/incident-reporting/) | Regulatory-deadline-aware external incident reports for EU AI Act Article 73, Colorado SB 205 Sections 6-1-1702(7) / 6-1-1703(7), and NYC LL144 candidate complaints (JSON + Markdown + CSV) | 0.1.0 |
| [supplier-vendor-assessor](plugins/supplier-vendor-assessor/) | ISO 42001 A.10, EU AI Act Article 25, and NYC LL144 Section 5-300 supplier and vendor assessment record (JSON + Markdown + CSV) | 0.1.0 |
| [evidence-bundle-packager](plugins/evidence-bundle-packager/) | Deterministic, optionally HMAC-SHA256 signed evidence bundle of plugin artifacts for audits, attestations, and regulatory submissions (JSON + Markdown + CSV) | 0.1.0 |
| [certification-readiness](plugins/certification-readiness/) | Consumer plugin. Graduated readiness verdict against a target certification with evidence completeness, gaps, blockers, and curated remediations (JSON + Markdown + CSV) | 0.1.0 |
| [post-market-monitoring](plugins/post-market-monitoring/) | EU AI Act Article 72, ISO/IEC 42001:2023 Clause 9.1, NIST MANAGE 4.1 / 4.2 post-market monitoring plan with per-dimension rows, trigger catalogue, Chapter III alignment, continuous-improvement loop, and review schedule (JSON + Markdown + CSV) | 0.1.0 |
| [gpai-obligations-tracker](plugins/gpai-obligations-tracker/) | EU AI Act Articles 51 to 55 GPAI obligations: systemic-risk classification, universal Article 53 obligations, Article 54 authorised-representative check, Article 55 systemic-risk additional obligations, downstream-integrator posture (JSON + Markdown + CSV) | 0.1.0 |
| [human-oversight-designer](plugins/human-oversight-designer/) | EU AI Act Article 14, ISO/IEC 42001:2023 Annex A controls A.9.2 / A.9.3 / A.9.4, and NIST AI RMF MANAGE 2.3 dedicated human-oversight design artifact with ability coverage, override capability, biometric dual-assignment verification per Article 14(5), operator training assessment, automation bias mitigations, and assigned oversight personnel (JSON + Markdown + CSV) | 0.1.0 |
| [robustness-evaluator](plugins/robustness-evaluator/) | Point-in-time robustness evaluation record for EU AI Act Article 15, ISO/IEC 42001 Annex A Control A.6.2.4, and NIST AI RMF MEASURE 2.5 / 2.6 / 2.7 with adversarial-posture aggregation and lifecycle trend (JSON + Markdown + CSV) | 0.1.0 |
| [bias-evaluator](plugins/bias-evaluator/) | Standard fairness metrics per protected-attribute group with NYC LL144 four-fifths rule, EU AI Act Article 10(4), Colorado SB 205 reasonable-care, Singapore MAS Veritas, ISO 42001 A.7.4, and NIST MEASURE 2.11 jurisdictional rule application (JSON + Markdown + CSV) | 0.1.0 |

## Bundles

| Bundle | Objective | Status |
|---|---|---|
| [iso42001-cert-readiness](bundles/iso42001-cert-readiness/) | Pre-certification readiness check for ISO 42001 audit | stub |

## Runtime

For a ready-to-run agent that uses this catalogue, see [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw). One repo is the catalogue, the other is the runtime. They are versioned independently.

## Quality bar

Every skill and plugin in this repository is held to a certification-grade output standard, defined in [STYLE.md](STYLE.md). Skill outputs must be acceptable as audit evidence by a practicing ISO 42001 Lead Auditor or NIST AI RMF practitioner without correction.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Read [STYLE.md](STYLE.md) before writing any skill, plugin, or eval.

## Security

See [SECURITY.md](SECURITY.md) for the disclosure policy.
