---
name: evidence-bundle
version: 0.1.0
description: >
  Evidence-bundle operationalization skill. Packages plugin-emitted
  governance artifacts (audit logs, risk registers, SoAs, AISIAs,
  nonconformity records, management-review packages, metrics reports,
  internal-audit plans) into a deterministic, cryptographically-signed
  delivery unit that auditors, attestation bodies, and regulators
  consume. Maps to ISO/IEC 42001:2023 Clause 7.5.3 (retention of
  documented information), NIST AI RMF 1.0 MANAGE 4.2 (continual-
  improvement measurement feedback captured), EU AI Act Articles 11
  (technical documentation), 12 (logging), and 19 (retention), and UK
  ATRS Section Impact assessment.
frameworks:
  - ISO/IEC 42001:2023
  - NIST AI RMF 1.0
  - EU AI Act (Regulation (EU) 2024/1689)
  - UK Algorithmic Transparency Recording Standard
tags:
  - ai-governance
  - evidence-bundle
  - audit-evidence
  - documented-information
  - iso42001
  - nist-ai-rmf
  - eu-ai-act
  - uk-atrs
  - retention
  - signing
author: AIGovOps Contributors
license: MIT
---

## Overview

The evidence bundle is what auditors actually consume. Running systems produce artifacts; auditors read packaged artifacts. The gap between those two is where ISO 42001 Clause 7.5.3 retention defects, EU AI Act Article 11 Annex IV completeness defects, and regulatory-submission rejection happen. This skill and its paired `evidence-bundle-packager` plugin close that gap by turning a directory of plugin outputs into a deterministic, optionally-signed bundle with a canonical layout, a manifest with SHA-256 per file, an aggregated citation summary, a provenance chain of plugin-to-plugin consumption, and HMAC-SHA256 signatures that let a verifier detect tampering.

The skill is framework-agnostic in the sense that it can be loaded by any agent runtime that reads SKILL.md (Hermes Agent, Claude Code, Codex CLI, Cursor, Jules). The runtime invokes the `evidence-bundle-packager` plugin to produce the bundle. The authoritative runtime for AIGovOps is [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw).

The plugin does not invent artifact content. It reads the artifacts written by upstream plugins as-is, computes cryptographic digests, copies them into a canonical layout, aggregates citations, infers provenance edges from well-known upstream-to-downstream consumption relationships, and optionally HMAC-signs the manifest and per-artifact digests. Every structural determination is deterministic; every content-level gap surfaces as a warning in the bundle report.

## Scope

**In scope.** Evidence packaging for the AIGovOps plugin catalogue. Any artifact emitted by the registered plugins (`audit-log-generator`, `risk-register-builder`, `soa-generator`, `aisia-runner`, `nonconformity-tracker`, `management-review-packager`, `internal-audit-planner`, `metrics-collector`, `gap-assessment`, `data-register-builder`, `applicability-checker`, `high-risk-classifier`, `uk-atrs-recorder`, `colorado-ai-act-compliance`, `nyc-ll144-audit-packager`, `crosswalk-matrix-builder`, `singapore-magf-assessor`, `ai-system-inventory-maintainer`) is classified, hashed, and manifested. Unknown-plugin files are included anyway under `artifacts/unknown-plugin/` and flagged.

**Out of scope.** Legal advice on evidence-retention periods for a specific organization or jurisdiction. Certification issuance. Audit conclusions. Discovery of artifacts outside the provided `source_dir`. Remote-URL fetches: the plugin reads local paths only. Encryption of the bundle contents (HMAC is integrity, not confidentiality). Clock synchronization: `generated_at` and `signed_at` are recorded in UTC, ISO 8601, seconds precision; correctness depends on the host clock.

**Operating assumption.** Upstream plugins have already produced their artifacts under a single source directory. The organization has selected a signing posture (`hmac-sha256` with an HMAC key supplied via environment variable, or `none`). The reviewer has named the bundle recipient category (`internal-audit`, `external-auditor`, `regulator`, `stakeholder`, `sponsor`).

## Framework Reference

The evidence bundle is grounded in five framework anchors.

**ISO/IEC 42001:2023, Clause 7.5.3 (Control of documented information).** Documented information required by the AIMS and by the standard shall be controlled to ensure availability, suitability, and protection from loss of confidentiality, improper use, or loss of integrity. The bundle's SHA-256 per file and HMAC signatures implement "protection from loss of integrity" in a verifier-detectable form. Retention and disposition decisions remain organizational; the bundle is the retention artifact.

**NIST AI RMF 1.0, MANAGE 4.2.** Measurable continuous-improvement activities are integrated into AI system updates and include regular engagement with interested parties, including relevant AI actors. The bundle is the packaged evidence of the measurable activities across a reporting period. The citation-summary and coverage-counts outputs quantify the measurement footprint.

**EU AI Act (Regulation (EU) 2024/1689), Article 11.** Providers of high-risk AI systems shall draw up and keep up to date the technical documentation set described in Annex IV. The bundle is the packaging mechanism for the Article 11 + Annex IV set when the provider is an AIGovOps user. `include_source_crosswalk=True` attaches the framework crosswalk data files so submitters can demonstrate cross-framework correspondence without external look-up.

**EU AI Act, Article 12 (Record-keeping) and Article 19 (Log retention).** Article 12 requires automatic logging of events over the system lifetime; Article 19 requires providers to keep logs for a minimum of six months unless Union or Member State law or, where applicable, Union data-protection law requires otherwise. The bundle captures and timestamps the point-in-time evidence state; organizational retention is documented via the scope's reporting period.

**UK Algorithmic Transparency Recording Standard, Section Impact assessment.** The ATRS template expects a reviewable documentation record, not just data. The bundle is the reviewable record for public-sector deployments.

**Source links.**

- ISO/IEC 42001:2023 Clause 7.5.3 is purchased from the ISO store; no open URL.
- NIST AI RMF 1.0: https://www.nist.gov/itl/ai-risk-management-framework.
- EU AI Act: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202401689.
- UK ATRS: https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies.

## Operationalizable Controls

The plugin output maps to specific framework clauses, controls, subcategories, and articles. See `operationalization-map.md` in this directory for the full mapping.

| Output component | ISO/IEC 42001:2023 | NIST AI RMF 1.0 | EU AI Act | UK ATRS |
|---|---|---|---|---|
| MANIFEST.json with SHA-256 per file | Clause 7.5.3 | MANAGE 4.2 | Article 11 + Annex IV | Section Impact assessment |
| citation-summary.md aggregated citations | Clause 7.5.1 | MANAGE 4.2 | Article 11, Paragraph 1(a)(b) | Section Tool description |
| provenance-chain.json plugin consumption edges | Clause 7.5.3 | MANAGE 4.2 | Article 11, Paragraph 1(c) | Section Data |
| signatures.json HMAC over digests | Clause 7.5.3 | MANAGE 4.2 | Article 12, Paragraph 1 | Section Governance |
| README.md auditor-facing overview | Clause 9.2 (audit readiness) | MEASURE 3.3 | Article 19 | Section Impact assessment |
| artifacts/ canonical directory layout | Clause 7.5.2 | MANAGE 4.2 | Article 11 + Annex IV | Section Tool details |
| crosswalk/ data files | Annex A, Control A.2.3 | GOVERN 1.1 | Article 40 (harmonised standards) | Section Governance |

## Output Standards

**Canonical shape.** Every run produces a bundle-report dict with `timestamp`, `agent_signature`, `bundle_id`, `bundle_path`, `scope`, `manifest`, `signatures`, `provenance`, `citation_groups`, `coverage_counts`, `warnings`, `summary`, and `reviewed_by`. Field names are stable across versions to support adapter-layer integration with GRC platforms, structured workspace tools, and regulatory-submission portals. The bundle on disk follows the layout documented in the plugin README.

**Citation formats.** ISO citations use `ISO/IEC 42001:2023, Clause X.X.X` or `ISO/IEC 42001:2023, Annex A, Control A.X.Y`. NIST uses `<FUNCTION> <Subcategory>`. EU AI Act uses `EU AI Act, Article XX` with optional paragraph reference. UK ATRS uses `UK ATRS, Section <name>`. Colorado uses `Colorado SB 205, Section 6-1-1701(3)`. Every citation in bundle output matches STYLE.md prefixes; plugin tests enforce this invariant.

**Determinism.** Bundle bytes are identical for identical inputs except for fields that reference absolute time (`generated_at`, `signed_at`). SHA-256 over file contents is deterministic. HMAC inputs are deterministic. Every dict in MANIFEST.json, provenance-chain.json, and signatures.json is serialized with sorted keys. Artifact lists are sorted by path. Citation lists are sorted and deduplicated within each framework.

**Signing posture.** Default algorithm is `hmac-sha256`. The key is supplied via an environment variable (default `AIGOVOPS_BUNDLE_SIGNING_KEY`). When the key is not set, the plugin downgrades to `"none"` and emits a warning. Downgrade is a content gap, not a structural error: the bundle still produces, but signatures.json records `"algorithm": "none"` and omits HMAC fields. The bundle remains verifiable for presence and SHA-256 integrity.

**Markdown and CSV renderings.** `render_markdown` produces sections `# Bundle overview`, `## Scope`, `## Artifact list`, `## Citation summary`, `## Provenance`, `## Signatures`, `## Warnings`. `render_csv` produces a one-row-per-artifact table with SHA-256 for spreadsheet ingestion. Neither renderer emits em-dashes, emojis, or hedging language. Plugin tests enforce the prohibitions.

## Limitations

The plugin does not fetch remote URLs. Source artifacts must be present on local disk.

The plugin does not verify that artifact references inside JSON (`risk_register_ref`, `aisia_ref`, `soa_ref`) resolve to real files. Reference resolution is a separate concern; the plugin's integrity guarantee covers the bytes in `source_dir`, not the semantic-link graph inside them.

HMAC-SHA256 is integrity only, not confidentiality. A compliant auditor with the HMAC key can detect tampering; anyone with read access to the bundle can read every artifact. For confidentiality, encrypt the bundle separately at rest or in transit.

The plugin does not rotate signing keys. Key rotation is an organizational responsibility. When keys rotate, re-pack the bundle with the new key and retire the prior bundle per Clause 7.5.3 disposition.

The plugin does not interpret retention periods. The reporting period in `scope` is descriptive. Organizational retention policy must document minimum-retention durations; EU AI Act Article 19 imposes a six-month floor for high-risk-system logs and is not enforced in code.

Legal disclaimer. This skill and its paired plugin produce audit-preparation artifacts grounded in the cited frameworks. They do not constitute legal advice on evidence-retention duration, chain-of-custody admissibility, or the sufficiency of HMAC-SHA256 versus digital signatures for a specific regulatory submission. Consult qualified counsel for jurisdiction-specific and submission-specific determinations.
