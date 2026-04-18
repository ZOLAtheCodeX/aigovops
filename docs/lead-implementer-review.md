# Lead Implementer Review Record

**Validation complete: 2026-04-18.**

Validated by Zola Valashiya (ISO/IEC 42001 Lead Implementer; NIST AI RMF practitioner; AIGP; CIPT). Content graduated from `-draft` to released: iso42001 skill at 0.2.0, nist-ai-rmf skill at 0.2.0. Eval test cases for both skills marked `status: validated`.

This document is retained as a historical record of the items reviewed in the validation pass. Future framework revisions that introduce new uncertainty would be tracked in a new validation pass document, not here.

## How to use this document

1. Work through the items in the order presented (ISO 42001 first, then NIST AI RMF, then cross-cutting). Each section starts with the highest-leverage validations first.
2. For every item: consult the published standard text, determine whether the claim is correct, and apply one of:
   - **Confirmed**: the claim is correct. Remove the `[verify]` marker from the source file and the row in this document.
   - **Corrected**: the claim is wrong. Fix the file and remove the marker. Note the correction in the commit message.
   - **Deferred**: the claim needs more research than this pass allows. Leave the marker and move to the next item.
3. When all ISO 42001 items are resolved, bump `skills/iso42001/SKILL.md` version from `0.2.0-draft` to `0.2.0`. Same for NIST and for the eval stubs when their expected outputs have been validated.
4. Record the validation pass in the audit log via the aigovclaw audit-log workflow, citing the skill(s) validated and your Lead Implementer credential reference.

---

## ISO/IEC 42001:2023 review queue

### High-priority (affect SoA generation and Phase 3 plugin mappings)

| # | File | Line | Claim to verify | Notes |
|---|---|---|---|---|
| 1 | `skills/iso42001/operationalization-map.md` | 188 | A.6 category structure has two sub-categories (A.6.1 objectives, A.6.2 life-cycle) with approximately ten controls | Verify split and count |
| 2 | `skills/iso42001/operationalization-map.md` | 196 | A.6.1.4 exists as a distinct control (author was not certain whether A.6.1 has 3 or 4 controls) | Resolve A.6.1 sub-count |
| 3 | `skills/iso42001/operationalization-map.md` | 142+ | Every Annex A control ID in the map (A.2.2 through A.10.4) matches the published standard | Spot-check each category; flag any renumbering |
| 4 | `skills/iso42001/SKILL.md` | 436 | A.6.2.6 operational monitoring and A.6.2.8 log recording IDs | Verify |
| 5 | `skills/iso42001/SKILL.md` | 437 | A.7.5 data provenance control ID | Verify |
| 6 | `skills/iso42001/SKILL.md` | 438 | A.8.3 external reporting control ID | Verify |
| 7 | `plugins/soa-generator/plugin.py` | DEFAULT_ANNEX_A_CONTROLS | 38-control default list with titles | Compare each ID and title against standard text; SoA is audit-facing so errors are expensive here |

### Medium-priority (affect skill body prose; correctable in place without workflow impact)

| # | File | Claim to verify | Notes |
|---|---|---|---|
| 8 | `skills/iso42001/SKILL.md` (throughout) | Clause citation format matches STYLE.md exactly on every occurrence | Tests enforce prefix; verify clause numbering accuracy |
| 9 | All `evals/iso42001/*.yaml` expected_outputs | Expected output references to specific Annex A controls match the control IDs validated above | After ID validation above, these follow |
| 10 | `plugins/role-matrix-generator/plugin.py` `_ENABLING_CITATIONS` | Each decision category's enabling Clause citation is correct (5.2 for policy, 6.1.3 for risk treatment, 6.1.4 for AISIA, 8.3 for implementation, 10.2 for nonconformity, 9.2.2 for audit programme, A.8.3 for external reporting) | Verify |

### Low-priority (content quality, not structural correctness)

| # | Scope | Notes |
|---|---|---|
| 11 | Cross-walk annotations in the NIST map's Notes column | Confirm iso42001 cross-references are accurate at the clause level |

---

## NIST AI RMF 1.0 review queue

All 22 `[verify]` markers in the NIST map flag subcategory IDs that are best-recall from NIST AI RMF 1.0 Core but have not been standard-text-verified. The function names (GOVERN, MAP, MEASURE, MANAGE) and top-level category structure (GOVERN 1 through GOVERN 6, MAP 1 through 5, and so on) are not flagged because they are stable.

### Subcategory IDs to confirm

**GOVERN function:**

- GOVERN 1.6, GOVERN 1.7 (third-party, decommissioning)
- GOVERN 3.1, GOVERN 3.2 (workforce diversity, training)
- GOVERN 5.2 (external feedback incorporation)
- GOVERN 6.2 (third-party contingency)

**MAP function:**

- MAP 1.6 (system requirements elicitation)
- MAP 3.4 (operator proficiency processes)
- MAP 5.2 (engagement cadence)

**MEASURE function:**

- MEASURE 1.2, MEASURE 1.3 (metric appropriateness review, expert selection)
- MEASURE 2.9, MEASURE 2.10, MEASURE 2.11, MEASURE 2.12, MEASURE 2.13 (privacy, fairness, environmental, computational-efficiency, measurement-methodology review)
- MEASURE 3.3 (affected-party feedback)
- MEASURE 4.3 (measurement outcomes incorporated into processes)

**MANAGE function:**

- MANAGE 2.4 (superseded/rogue/unknown AI systems)
- MANAGE 3.1, MANAGE 3.2 (third-party sources, pre-trained models)
- MANAGE 4.3 (incident communication)

### Verification process for NIST

1. Download or reference NIST AI RMF 1.0 Core (https://www.nist.gov/itl/ai-risk-management-framework).
2. For each flagged subcategory: confirm the ID exists, confirm the theme statement matches, confirm the operationalizability class (A/H/J) and leverage ranking are defensible given the subcategory's intent.
3. For MEASURE 2.9 and 2.10 specifically (privacy and fairness): the `metrics-collector` plugin default catalog cites these heavily. Errors here propagate to the metrics pipeline.

---

## Plugin `agent_signature` version-bump policy

After a validation pass, the plugin version should be bumped only if the plugin's output format changed. Citation corrections alone do not require a version bump unless they change the field structure or the set of possible values. Examples:

- Renaming a control from A.6.1.4 to A.6.1.3 in `DEFAULT_ANNEX_A_CONTROLS`: no bump (content change, structure identical).
- Adding a new field to `SoA-row` output: bump to 0.2.0.
- Removing a deprecated field: bump to 0.2.0.

## Tracking

Resolved items should be removed from this document in the commit that resolves them. When all sections are empty (or contain only "deferred" entries), the catalogue is in a released state and skill versions drop their `-draft` suffix.
