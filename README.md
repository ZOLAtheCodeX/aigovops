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

## Skills

| Skill | Framework | Status |
|---|---|---|
| [iso42001](skills/iso42001/SKILL.md) | ISO/IEC 42001:2023 | 0.2.0 |
| [nist-ai-rmf](skills/nist-ai-rmf/SKILL.md) | NIST AI RMF 1.0 | 0.2.0 |
| [eu-ai-act](skills/eu-ai-act/SKILL.md) | EU AI Act (Regulation (EU) 2024/1689) | 0.2.0 |

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
| [metrics-collector](plugins/metrics-collector/) | NIST AI RMF MEASURE 2.x metrics + AI 600-1 overlay with threshold-breach routing (JSON + Markdown + CSV) | 0.1.0 |
| [gap-assessment](plugins/gap-assessment/) | Framework gap assessment for ISO 42001, NIST AI RMF, or EU AI Act (JSON + Markdown + CSV) | 0.1.0 |
| [data-register-builder](plugins/data-register-builder/) | ISO 42001 A.7 and EU AI Act Article 10 data register (JSON + Markdown + CSV) | 0.1.0 |
| [applicability-checker](plugins/applicability-checker/) | EU AI Act applicability by target date + system classification (JSON + Markdown) | 0.1.0 |
| [high-risk-classifier](plugins/high-risk-classifier/) | EU AI Act Article 5, 6, Annex I, Annex III risk-tier classification (JSON + Markdown) | 0.1.0 |

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
