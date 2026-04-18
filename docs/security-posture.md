# AIGovOps Security Posture

Defines the trust boundaries, attack surface, and defensive posture for the AIGovOps catalogue and the AIGovClaw runtime. Intended for security reviewers evaluating the project before adoption and for contributors adding new plugins or adapters.

## Scope

This document covers:

- The aigovops catalogue (skills, plugins, bundles, evals, docs).
- The aigovclaw runtime (tool registry, adapters, workflows, install.sh).
- The seam between them (how aigovclaw loads aigovops artifacts).

Out of scope:

- Hermes Agent security (reported to Nous Research; see SECURITY.md).
- LLM provider security (reported to the provider; see SECURITY.md).
- User-operated external systems (GRC platforms, MCP servers, data engineering pipelines).

## Trust boundaries

### Boundary 1: between aigovops and aigovclaw

aigovops contains data and pure-Python plugins. It has no runtime dependencies on aigovclaw. aigovclaw loads aigovops artifacts at install time via rsync and at runtime via filesystem-path `importlib` loading.

**Trust model:** aigovclaw treats aigovops as trusted input. A malicious aigovops plugin could execute arbitrary code when loaded. Mitigations:

- aigovops is MIT-licensed and fully open-source; contributions go through PR review per `CONTRIBUTING.md` and `AGENTS.md` quality gates.
- `install.sh` pins to a specific aigovops ref in production deployments (recommended; current script clones `main` and is suitable for development).
- The consistency audit at `tests/audit/consistency_audit.py` catches structural drift in plugins that might indicate tampering (unexpected function names, malformed citations).

**Not mitigated:** aigovclaw does not sandbox plugin execution. A compromised plugin has the full privileges of the Hermes worker process.

### Boundary 2: between aigovclaw and the Hermes harness

aigovclaw is a configuration package for the Hermes Agent. The Hermes harness enforces permissions, iteration budgets, and tool-invocation validation per the harness paradigm.

**Trust model:** aigovclaw trusts Hermes to enforce the permission posture declared in `config/hermes.yaml`. aigovclaw declares its tools as read-only, concurrency-safe, and non-destructive; Hermes is relied upon to honor those declarations.

**Defense in depth:** even if Hermes fails to enforce permissions, the plugins themselves have no filesystem-write or network-access code paths. The worst-case failure is that the plugin reads more input than it should, which is bounded by what the harness passes in.

### Boundary 3: between aigovclaw and external destinations (MCP servers)

AIGovClaw pushes artifacts to external destinations via MCP servers (per `aigovclaw/adapters/README.md`). The MCP servers authenticate against destination APIs using their own configuration.

**Trust model:** aigovclaw never handles destination credentials. Credentials live in the MCP server's configuration (typically OS keychain, environment variables, or the user's secret manager). aigovclaw's adapter config (`config/adapters.yaml`) contains only MCP-server identifiers and routing rules.

**Audit trail:** every MCP push emits an audit-log entry citing `ISO/IEC 42001:2023, Clause 7.5.3` (distribution of documented information). The entry names the MCP server and the tool invoked; credentials never appear in log content.

### Boundary 4: between AIGovClaw and the user's AI systems

AIGovClaw reads inputs that describe AI systems under governance: AI system inventories, risk registers, measurement data, incident logs. It produces governance artifacts grounded in those inputs.

**Trust model:** AIGovClaw trusts that the inputs describe real AI systems accurately. A user providing falsified inputs gets falsified outputs; this is not AIGovClaw's threat model.

**Not in scope:** AIGovClaw does not verify AI system existence, identity, or behavior. Governance is meaningful only when the inputs are accurate; input falsification is an organizational-governance failure, not a technical one.

## Attack surface

### Input-path attacks

Every plugin validates its inputs structurally (`_validate` functions raising `ValueError` on malformed dicts, unknown enums, missing required fields). The tool registry layer in aigovclaw adds schema validation before invocation. Risks:

- **Malicious input data:** a user-provided input could be crafted to trigger unexpected plugin behavior. Mitigations: plugins are deterministic and side-effect-free; every field is typed-checked; no string-templating into subprocess calls or SQL; no filesystem writes.
- **Resource exhaustion:** an extremely large inventory or risk list could cause excessive memory use. Mitigations: plugins do not cache across invocations; the harness's iteration budget caps total work. Organizational mitigation: throttle input sizes at the workflow layer.

### Output-path attacks

Plugin outputs are consumed by downstream workflows, adapters, and eventually external destinations. Risks:

- **Stored XSS via Markdown injection:** plugin outputs include user-provided strings rendered into Markdown. Mitigations: the renderers escape pipe characters in table cells; table-embedded user strings are truncated to reasonable lengths. Outputs are not intended for browser rendering without a sanitization pass.
- **JSON injection into destination systems:** MCP server APIs consume structured JSON. Mitigations: the MCP router passes values as dict entries, not as string-interpolated payloads; destination systems handle escaping themselves.

### Runtime attacks

- **Plugin loader path traversal:** `tools/aigovops_tools.py` loads plugin files by concatenating a plugins_path with a plugin-directory name. Mitigations: the `PLUGIN_TOOL_DEFS` list is hard-coded; plugin directory names are not derived from user input.
- **Tool-invocation injection:** a compromised LLM or agent could attempt to invoke a tool with inputs the harness rejected. Mitigations: `registry.py`'s `validate_inputs()` runs before `invoke()`; structurally-invalid inputs raise `ValueError` before the plugin sees them.

### Supply chain

- **aigovops dependencies:** plugins use only the Python standard library. Zero third-party runtime dependencies means zero supply-chain surface for plugins.
- **aigovclaw dependencies:** Hermes Agent is the only runtime dependency. `install.sh` verifies Hermes presence before proceeding. MCP servers are separate installable components with their own supply-chain considerations.
- **CI workflow dependencies:** `framework-monitor.yml` pins `requests==2.31.0` and `pyyaml==6.0.1`. CI-only pinning limits blast radius of a dependency compromise to the monitoring workflow.

## Defensive posture

### Declarative safety properties

Every plugin is registered as a Hermes tool with explicit safety declarations: `is_read_only=True`, `is_concurrency_safe=True`, `is_destructive=False`, `requires_human_approval=False`, `max_result_size_bytes=1_000_000`. The harness uses these to make permission and scheduling decisions without executing plugin code. A plugin that lies about its safety properties is a security bug; CI enforces the declarations through `tools/tests/test_registry.py`.

### Read-only plugin contract

All plugins are read-only. They take inputs, return outputs, and have no filesystem, network, or shared-state side effects. Persistence is the workflow layer's responsibility; adapter push is handled by the MCP router and ultimately by Hermes invoking MCP tools. Separating pure computation from side effects is the primary defense against plugin-initiated damage.

### Explicit refusal patterns

The AIGovClaw persona (`persona/SOUL.md`) declares behaviors refused regardless of instruction: no out-of-workspace filesystem writes, no unconfirmed shell execution, no third-party transmission without per-transmission authorization, no credential handling. These refusals are load-bearing; they are also enforced at the Hermes permission-posture level in `config/hermes.yaml`.

### Credentials

AIGovOps plugins never accept credentials as input. AIGovClaw workflows reference credentials by environment variable name, never by value. The MCP adapter pattern routes destination auth to the MCP server entirely, so aigovclaw never sees destination tokens.

### Auditability

Every governance event produces an `audit-log-entry` citing `ISO/IEC 42001:2023, Clause 7.5.2` (documented information). The audit log is immutable: corrections are new entries referencing the prior entry. Adapters emit distribution events citing Clause 7.5.3.

### Isolation

Hermes Agent (per the harness paradigm article) uses namespace isolation and optional read-only root filesystems. AIGovClaw's deployment inherits those defaults. Additional isolation (seccomp, AppArmor, container) is an operator choice and not prescribed here.

## Threat scenarios

### Scenario 1: Malicious plugin contribution

A contributor submits a plugin PR that includes a backdoor (network exfiltration, credential theft, arbitrary code execution on load).

**Defenses:** PR review per `CONTRIBUTING.md` and `AGENTS.md`; the consistency audit script catches structural drift; the plugin-author contract in `plugins/README.md` forbids any plugin from importing networking libraries or having filesystem side effects; tests must pass including no-em-dash and no-hedging assertions. Reviewers should reject any plugin PR that adds runtime dependencies or that includes suspicious import statements.

**Residual risk:** a determined attacker with reviewer access could merge a backdoor. Mitigation: require two reviewers on PRs that add or modify plugin code; consider adopting Dependabot and per-commit code-signing in beta.

### Scenario 2: Compromised MCP server

A user has configured AIGovClaw to route risk-register rows to a Notion MCP server that has been compromised, exfiltrating received data.

**Defenses:** this is outside AIGovClaw's threat model. The MCP server receives governance artifacts the user explicitly configured it to receive. If the MCP server is untrusted, the user should not configure AIGovClaw to push to it. Mitigation: document which artifact types contain sensitive data (the risk-register does; the SoA may; the gap-assessment is less sensitive) so users make informed routing choices.

### Scenario 3: Adversarial input

A user or upstream pipeline feeds malformed inputs to a plugin to trigger unexpected behavior.

**Defenses:** plugin input validation raises `ValueError` on structural problems before any business logic runs; the tool registry adds a second validation layer; the harness's iteration budget caps total invocation attempts.

**Residual risk:** an input that is structurally valid but semantically absurd (a risk register with 10,000 identical entries, for example) wastes compute without producing useful output. Mitigation: organizational threshold policy (documented in `AGENTS.md`) on input sizes.

### Scenario 4: LLM or agent manipulation

A jailbroken LLM inside Hermes attempts to invoke tools with unauthorized inputs.

**Defenses:** the harness enforces permission declarations before invoking tools. All AIGovOps tools are read-only; the worst case is an unauthorized read, which produces an output but does not modify state. Destructive operations (nonconformity closure with ineffective outcome, bypassing Clause 5.3 role matrix requirements) require human approval per `persona/SOUL.md`; the harness surfaces approval requests to the human review queue.

**Residual risk:** an unauthorized read of sensitive risk-register content could inform further attacks. Mitigation: organizational policy on what is read-safe; aigovclaw does not store credentials or user PII, so unauthorized reads are bounded by what the organization has chosen to put in the AIMS.

## Reporting vulnerabilities

See `SECURITY.md` for the disclosure policy and response SLA. Summary: use GitHub Security Advisories, expect acknowledgment within 72 hours, critical issues addressed within 14 days of confirmation.

## Review cadence

This document is reviewed annually and after any material change to the plugin contract, adapter architecture, or Hermes integration. The framework-monitor workflow does not probe this document; changes require explicit human review.

Last reviewed: 2026-04-18.
