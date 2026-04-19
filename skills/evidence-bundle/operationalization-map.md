# Evidence Bundle Operationalization Map

Working document for the `evidence-bundle` skill. Maps the bundle contents produced by `evidence-bundle-packager` to each framework's evidence-retention and documentation requirements.

## Bundle contents at a glance

Every packed bundle contains:

- `MANIFEST.json`: bundle schema version, bundle id, scope, artifact list with SHA-256 and size per file, included-plugin list, missing-plugin list, citations unique count.
- `citation-summary.md`: aggregated unique citations grouped by framework, plus coverage counts for the primary instruments.
- `provenance-chain.json`: plugin-to-plugin consumption edges (for example, `ai-system-inventory-maintainer -> risk-register-builder` via the `ai_system_inventory` field) inferred from known upstream relationships when both endpoints are present in the bundle.
- `signatures.json`: algorithm, manifest SHA-256, manifest HMAC, per-artifact HMACs, key id, signed_at timestamp.
- `README.md`: auditor-facing overview with who, what, how-to-verify, how-to-read, and legal notice.
- `artifacts/<plugin-name>/<filename>`: the plugin output files from `source_dir`, one subdirectory per classified plugin, one `unknown-plugin` subdirectory for unclassified files.
- `crosswalk/*.yaml`: copy of the nine crosswalk-matrix-builder data files when `include_source_crosswalk=True`.

## ISO/IEC 42001:2023 mapping

**Clause 7.5.3 (Control of documented information).** The standard requires documented information to be controlled for availability, suitability, and protection from loss of integrity, confidentiality, or improper use. The bundle implements integrity protection via SHA-256 per file and HMAC-SHA256 over the manifest and per-artifact digests. Availability is the bundle being written to the filesystem; auditor-facing README tells the consumer how to read and verify. Retention periods are the organization's responsibility; the bundle carries a scope-level reporting period that bounds the evidence window.

**Clause 7.5.1 (Creating documented information).** Each artifact in the bundle was created by an upstream plugin with an `agent_signature` field. The bundle preserves every `agent_signature` in the manifest artifact entry, so adapter-layer consumers can route by version.

**Clause 7.5.2 (Updating documented information).** When the bundle is re-packed after upstream re-runs, the deterministic hash and canonical layout make version-to-version comparison trivial. A new bundle with the same `bundle_id` but different content produces different SHA-256 digests; a consumer can diff MANIFEST.json pre/post.

**Clause 9.2 (Internal audit) and Clause 9.3.2 (Management review inputs).** The bundle is the evidence pack that auditors and management review committees consume. The citation-summary and coverage-counts give committees a one-glance view of framework coverage.

**Annex A, Control A.2.3 (Alignment with other organisational policies).** When `include_source_crosswalk=True`, the bundle carries the crosswalk data files that demonstrate alignment with NIST AI RMF, EU AI Act, UK ATRS, Colorado SB 205, NYC LL144, Singapore MAGF 2e, and California instruments.

## NIST AI RMF 1.0 mapping

**MANAGE 4.2 (Measurable continuous-improvement activities).** The bundle is the packaged output of the measurable activities for a reporting period. The `coverage_counts` block quantifies the measurement footprint in auditor-readable form.

**GOVERN 1.1 (Legal and regulatory requirements understood).** The crosswalk data files in the bundle show the mapping from organizational controls to every framework the organization is accountable to.

**MEASURE 3.3 (Measurements are evaluated for meaningful performance improvements).** When the bundle carries a `metrics-report.json` from the metrics-collector plugin, the SHA-256 digest anchors the metrics set for auditor review.

**MANAGE 4.1 (Post-deployment monitoring planned).** When nonconformity records and metrics reports are present, the bundle is the review pack that proves the monitoring plan executed.

## EU AI Act mapping

**Article 11 (Technical documentation) + Annex IV.** The bundle is the packaging mechanism for the Annex IV technical-documentation set when the AIGovOps user is a high-risk-system provider. The manifest lists every included artifact by path, plugin, type, and hash. The Annex IV content set is organizational; the bundle is how the content set is delivered and verified.

**Article 12 (Record-keeping).** Article 12 requires automatic logging of events over the system lifetime. The bundle's per-artifact SHA-256 and HMAC signatures demonstrate that the logs, once emitted, have not been altered. Source-system logging compliance is upstream of the bundle.

**Article 19 (Retention of logs for minimum 6 months).** The bundle timestamps the point-in-time state of the log set. Organizational retention policy must separately ensure the logs are retained for the required duration. The bundle's `scope.reporting_period_start` and `scope.reporting_period_end` describe the evidence window; continued retention of the bundle itself is an organizational decision.

**Article 40 (Harmonised standards presumption).** When harmonised standards are cited in the bundle (ISO/IEC 42001:2023 is a candidate), conformance to those standards gives rise to a presumption of conformity. The bundle's crosswalk data files make the standards-to-article mapping legible.

## UK ATRS mapping

**Section Impact assessment.** The bundle is the reviewable documentation record for public-sector deployments. When the source directory contains an `atrs-record.json` from `uk-atrs-recorder`, the plugin classifies it to that plugin and includes it under `artifacts/uk-atrs-recorder/`.

**Section Tool description and Section Owner and contact.** When the source directory contains `ai-system-inventory.json`, those fields are reachable inside that artifact. The bundle provides the integrity anchor.

**Section Governance.** The signatures.json file and the crosswalk data files together provide evidence of governance discipline.

## Colorado SB 205 mapping

**Section 6-1-1706(3) (Rebuttable presumption of reasonable care).** Conformance with NIST AI RMF 1.0 or ISO/IEC 42001:2023 creates a rebuttable presumption for a deployer defending against an attorney-general action. The bundle is the evidence pack demonstrating that conformance. The crosswalk data files include the `statutory-presumption` relationship rows that ground this pathway.

**Section 6-1-1706(4) (Affirmative-defense-on-cure pathway).** The bundle's point-in-time hash provides a dated anchor for cure-window compliance claims.

## NYC LL144 mapping

**NYC LL144 Final Rule, Section 5-303 (Record-keeping requirements).** When the source directory contains `nyc-ll144-audit-package.json` from `nyc-ll144-audit-packager`, the bundle includes it with hash integrity.

## Singapore MAGF 2e mapping

**Pillar Internal Governance Structures and Measures.** The bundle's README, signatures, and provenance chain are the governance-structure documentation deliverables.

**Pillar Operations Management.** The manifest list and per-artifact hashes are the operational-discipline evidence.

## Retention-requirement cross-reference

| Framework | Minimum retention | Bundle support |
|---|---|---|
| ISO/IEC 42001:2023, Clause 7.5.3 | Organization-defined, proportionate to purpose | Bundle is the retention artifact; integrity verified via SHA-256 + HMAC. |
| NIST AI RMF 1.0, MANAGE 4.2 | Organization-defined | Bundle anchors measurable activities per reporting period. |
| EU AI Act, Article 19 | 6 months minimum for high-risk-system logs, unless sector law requires longer | Bundle timestamps the evidence state; organizational retention policy enforces duration. |
| Colorado SB 205 | 3 years for developer record, 3 years for deployer impact assessment (per statute) | Bundle carries the relevant records with integrity anchor. |
| NYC LL144 Final Rule, Section 5-304 | 1 year (annual audit refresh) | Bundle anchors the annual audit package. |
| UK ATRS v2.0 | Organization-defined; public record updated on material change | Bundle anchors the Tier 1 and Tier 2 records. |

## Priority-ranked backlog

The plugin is Phase 3 minimum-viable implementation. Outstanding items, in operational-leverage order:

1. Add RSA-PSS signing as an alternative to HMAC-SHA256 for external-auditor recipients who require asymmetric verification.
2. Add a bundle-to-bundle diff command for version comparison across reporting periods.
3. Add a `verify_bundle --public-key` flow once asymmetric signing lands.
4. Add optional OCSP-style revocation checking for the signing key once key-management policy matures.
5. Add a streaming-pack mode for organizations with too many artifacts to fit in memory at once.
