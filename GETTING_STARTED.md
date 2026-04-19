# Getting Started with AIGovOps

Clone to first artifact in 10 minutes. This guide takes you from zero to a working AI Management System evidence package against a realistic scenario.

## Prerequisites

- Python 3.10 or newer.
- git.
- No framework-specific tools; the catalogue is pure Python.
- (Optional) Node.js if you want to run the markdown lint locally.

No LLM API key, no Hermes Agent installation, no destination accounts. The catalogue runs as pure Python. Add Hermes + MCP later when you want an agent to invoke these plugins autonomously.

## 10-minute quickstart

The recommended entry point is the unified `aigovops` CLI. It orchestrates every plugin against a single `organization.yaml` configuration file.

```bash
# 1. Clone
git clone https://github.com/ZOLAtheCodeX/aigovops
cd aigovops

# 2. Verify the environment
export PATH="$PWD/bin:$PATH"
aigovops doctor

# 3. Run the full AIMS pipeline against the example organization
aigovops run --org examples/organization.example.yaml --output /tmp/aigovops-run

# 4. Open the run summary
open /tmp/aigovops-run/run-summary.md      # macOS
xdg-open /tmp/aigovops-run/run-summary.md  # Linux
```

For the CLI subcommand reference and `organization.yaml` schema, see [cli/README.md](cli/README.md).

If you prefer the legacy hand-rolled demo (useful as a worked example of direct plugin invocation), run:

```bash
python3 examples/demo-scenario/run_demo.py
open examples/demo-scenario/outputs/summary.md  # macOS
xdg-open examples/demo-scenario/outputs/summary.md  # Linux
```

The demo runs all 11 plugins against a realistic scenario (an HR AI system called `ResumeScreen`) and produces 18+ artifacts: audit log entry, role matrix, risk register, Statement of Applicability, AISIA, nonconformity register, management review input package, metrics report, gap assessment, plus JSON and CSV renderings.

`outputs/summary.md` indexes every artifact with the composite AIMS state: risk register row count, SoA status counts, AISIA coverage, nonconformity status, KPI breach count, gap-assessment coverage score.

## What you just produced

The demo produces every primary artifact type in the AIGovOps vocabulary:

| Artifact | Framework | Plugin | Purpose |
|---|---|---|---|
| Audit log entry | ISO 42001 Clause 9.1, 7.5.2 | `audit-log-generator` | Records governance events with clause + Annex A mappings |
| Role matrix | ISO 42001 Clause 5.3, Annex A A.3.2 | `role-matrix-generator` | RACI per AI-governance decision category |
| Risk register | ISO 42001 Clause 6.1.2; NIST MAP 4.1, MANAGE 1.2 | `risk-register-builder` | Structured risks with scoring, owner, treatment |
| Statement of Applicability | ISO 42001 Clause 6.1.3 | `soa-generator` | All 38 Annex A controls with status and justification |
| AISIA | ISO 42001 Clause 6.1.4, Annex A A.5; NIST MAP 1.1, 3.1, 3.2, 5.1 | `aisia-runner` | AI System Impact Assessment across impact dimensions |
| Nonconformity register | ISO 42001 Clause 10.2; NIST MANAGE 4.2 | `nonconformity-tracker` | Corrective-action lifecycle records |
| Management review package | ISO 42001 Clause 9.3.2 | `management-review-packager` | Nine-category Clause 9.3.2 input package |
| Metrics report | NIST MEASURE 2.x; ISO 42001 Clause 9.1 | `metrics-collector` | KPI records with threshold breach detection |
| Gap assessment | ISO 42001, NIST, EU AI Act | `gap-assessment` | Coverage classification per target framework |
| Data register | ISO 42001 Annex A A.7; EU AI Act Article 10 | `data-register-builder` | Dataset register with provenance and quality checks |
| Applicability report | EU AI Act | `applicability-checker` | What EU AI Act provisions apply at a target date |

Every artifact carries framework citations in the canonical format defined by [STYLE.md](STYLE.md).

## Running against your own data

The demo inputs are in `examples/demo-scenario/inputs/`. Replace them with your own:

1. **`ai_system_inventory.json`**: list of AI systems in AIMS scope.
2. **`risks.json`**: risks identified through stakeholder consultation (use `risk-register-builder` to validate).
3. **`org_chart.json`**: organizational roles and reporting lines.
4. **`role_assignments.json`**: explicit RACI (see `plugins/role-matrix-generator/README.md`).
5. **`authority_register.json`**: role to authority-basis mapping (board resolutions, delegation policies).
6. **`stakeholders.json`**: groups affected by the AI system's outputs (for AISIA).
7. **`impact_assessments.json`**: pre-populated AISIA sections.
8. **`measurements.json`**: trustworthy-AI measurements from your MLOps pipeline.
9. **`thresholds.json`**: organizational thresholds for metric breach detection.
10. **`governance_decisions.json`**: recent governance events to log.

Then re-run `python3 examples/demo-scenario/run_demo.py`.

## Common next steps

### Use a single plugin

```python
from plugins.audit_log_generator import plugin

entry = plugin.generate_audit_log({
    "system_name": "YourSystem",
    "purpose": "Your intended use",
    "risk_tier": "limited",
    "data_processed": ["input1", "input2"],
    "deployment_context": "Internal tool",
    "governance_decisions": ["Deployed on 2026-04-18."],
    "responsible_parties": ["AI Governance Officer"],
})
print(plugin.render_markdown(entry))
```

Every plugin has a `README.md` with input schema, example invocation, and output structure.

### Pick a framework

AIGovOps covers three frameworks. Each has its own SKILL.md:

- **[skills/iso42001/SKILL.md](skills/iso42001/SKILL.md)**: ISO/IEC 42001:2023 AI Management System standard. Certification-grade. Start here if you're pursuing ISO 42001 certification.
- **[skills/nist-ai-rmf/SKILL.md](skills/nist-ai-rmf/SKILL.md)**: NIST AI RMF 1.0 (voluntary). Start here if you need US-facing alignment without certification overhead.
- **[skills/eu-ai-act/SKILL.md](skills/eu-ai-act/SKILL.md)**: EU AI Act (Regulation (EU) 2024/1689). Required for any AI system within EU territorial scope.

The skills cross-reference each other; most plugins support multi-framework `dual` mode where rows carry both ISO and NIST citations (or ISO and EU AI Act).

### Validate your skill outputs

Every skill has an eval harness at `evals/<skill-name>/test_cases.yaml`. The test cases are validated by practitioners against the published framework text (see `docs/lead-implementer-review.md`). Use them as a quality reference when authoring new skills.

### Automate with AIGovClaw

When you're ready to have an agent run these workflows autonomously, clone [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw) and run `./install.sh`. AIGovClaw is the Hermes Agent configuration package that registers AIGovOps plugins as tools, installs the governance persona, and wires the workflows.

## Learn the architecture

- **[plugins/README.md](plugins/README.md)**: the plugin-author contract. Read this before writing a new plugin.
- **[AGENTS.md](AGENTS.md)**: rules for AI agents working on this repo (Claude Code, Codex CLI, Jules, Cursor, and others). Read this before letting any agent modify the catalogue.
- **[STYLE.md](STYLE.md)**: canonical quality standard. No em-dashes, no emojis, no hedging; citation formats specified exactly.
- **[docs/security-posture.md](docs/security-posture.md)**: trust boundaries, attack surface, and defensive posture.
- **[docs/new-skill-walkthrough.md](docs/new-skill-walkthrough.md)**: step-by-step guide to adding a new skill (or operationalizing a new framework).

## Testing

Every plugin has a standalone test file:

```bash
# Run a single plugin's tests
python3 plugins/audit-log-generator/tests/test_plugin.py

# Run all plugin tests
for d in plugins/*/tests/test_plugin.py; do python3 "$d"; done

# Run integration tests (cross-plugin data flow)
python3 tests/integration/test_plugin_chain.py

# Run the consistency audit (structural checks across the catalogue)
python3 tests/audit/consistency_audit.py
```

CI runs all of these on every push; see `.github/workflows/ci.yml`.

## Getting help

- **Skill or plugin questions**: open an issue using the [skill-bug template](.github/ISSUE_TEMPLATE/skill-bug.md).
- **Framework updates**: open an issue using the [framework-update template](.github/ISSUE_TEMPLATE/framework-update.md).
- **Security concerns**: see [SECURITY.md](SECURITY.md) for responsible-disclosure procedure.
- **Contribution questions**: see [CONTRIBUTING.md](CONTRIBUTING.md).

## What's next

If you've run the demo and read through at least one SKILL.md, you're ready to:

1. Substitute your own organizational data for the demo inputs.
2. Review the outputs with your Lead Implementer or compliance team.
3. Identify gaps (the `gap-assessment` plugin makes this concrete).
4. Package the outputs into a deterministic evidence bundle (the `evidence-bundle-packager` plugin).
5. Assess certification readiness against a target (ISO 42001 Stage 1 or 2, EU AI Act Article 43 internal control, Colorado SB 205 safe-harbor, and more) using the `certification-readiness` plugin. This is the final step in a full governance cycle: it consumes the bundle and returns a graduated ready-with-high-confidence, ready-with-conditions, partially-ready, or not-ready verdict with specific remediations for every gap.
6. Move toward AIGovClaw + Hermes when you want background automation.
