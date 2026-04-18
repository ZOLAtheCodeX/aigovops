# AIGovOps Threat Model (STRIDE)

This document provides a STRIDE decomposition of the AIGovOps catalogue and the AIGovClaw runtime. It complements `docs/security-posture.md`, which establishes trust boundaries and defensive posture. Where the security-posture document defines the perimeter, this document enumerates per-component threats, maps each to a STRIDE category, and records the likelihood, impact, mitigation, and residual risk.

STRIDE categories used throughout:

- **S**poofing of identity
- **T**ampering with data
- **R**epudiation
- **I**nformation disclosure
- **D**enial of service
- **E**levation of privilege

Likelihood and impact use qualitative scales: Low, Medium, High. Ratings reflect the current codebase and the declared v1.0 deployment posture (single-operator, single-host, MIT-licensed open source, Python standard library only for plugins). Ratings assume the mitigations in Section 5 are in place. Residual risk reflects exposure after mitigations.

## 1. Scope and trust boundaries

### 1.1 Components in scope

This threat model covers nine components, grouped by repository and lifecycle:

| Component | Location | Lifecycle |
|---|---|---|
| Plugin code | `aigovops/plugins/<name>/plugin.py` | Authored at contribution time, loaded at runtime |
| Plugin inputs | Caller-provided dicts (organizational JSON) | Provided per-invocation |
| Tool registry | `aigovclaw/tools/registry.py` and `aigovclaw/tools/aigovops_tools.py` | Loaded at Hermes startup |
| Hermes runtime invocation | Hermes Agent harness executing registered tools | Per-invocation |
| Filesystem evidence store | `~/.hermes/memory/aigovclaw/<artifact>/` | Appended per artifact emission |
| Framework-monitor workflow | `.github/workflows/framework-monitor.yml` | Scheduled cron in GitHub Actions |
| Future MCP server | Planned exposure of plugins over Model Context Protocol | Out of current release, in scope for v1.0 |
| Future GRC adapter layer | Planned push adapters for VerifyWise, Vanta, Notion, and similar | Out of current release, in scope for v1.0 |
| Continuous integration | `.github/workflows/ci.yml` and `tests/audit/consistency_audit.py` | Per pull request and per main push |

### 1.2 Trust boundaries

Four trust boundaries separate the components. Each boundary is the locus of at least one STRIDE threat.

**Boundary A: Contributor to repository.** The boundary between a contributor's development environment and the `ZOLAtheCodeX/aigovops` or `ZOLAtheCodeX/aigovclaw` main branch. Crossed by pull requests. Enforced by PR review, CI, and branch protection.

**Boundary B: Repository to runtime host.** The boundary between the GitHub repository and the operator's host machine. Crossed by `install.sh` cloning the repository and rsyncing plugin modules into the aigovclaw workspace. Enforced by ref pinning (recommended) and by the operator's host integrity.

**Boundary C: Caller to plugin.** The boundary between Hermes tool dispatch and plugin module execution. Crossed by the registry's `invoke()` function passing a validated input dict into the plugin's `generate_<artifact>()` entry point. Enforced by two-layer input validation (registry, then plugin) and by the plugin contract's prohibition on side effects.

**Boundary D: Plugin output to destination.** The boundary between an emitted artifact dict and its final resting place (filesystem, MCP destination, GRC adapter endpoint, operator screen). Crossed by the evidence-store writer, by MCP router, or by adapter push. Enforced by the distribution audit entry citing `ISO/IEC 42001:2023, Clause 7.5.3` and by the declarative safety properties on the tool.

### 1.3 Out-of-scope components

Host OS, Hermes Agent internals, LLM provider infrastructure, MCP server implementations (as distinct from AIGovClaw's invocation of them), GRC destination systems, and the operator's credential store are out of scope. Section 7 enumerates these.

## 2. Assets being protected

Five asset classes warrant protection. Each is exposed to a distinct subset of STRIDE threats.

### 2.1 Evidence artifacts

Emitted by plugins and consumed by auditors. Includes audit-log entries, risk registers, Statements of Applicability, role matrices, AI System Impact Assessments, nonconformity records, management-review packages, metrics reports, gap assessments, data registers, EU AI Act applicability classifications, and high-risk tier classifications. Integrity is the dominant property: an auditor relies on the artifact as a faithful record of what the organization decided. Confidentiality is secondary; most artifacts are designed for auditor disclosure. Availability matters only at certification-audit checkpoints.

### 2.2 Framework text

ISO/IEC 42001:2023 clause references, NIST AI RMF subcategory identifiers, EU AI Act article citations, and the prose descriptions that accompany them in plugin README files. Framework text is public by nature. The protected property is the correctness of citations: a wrong article or clause reference invalidates downstream artifacts. The framework-monitor workflow guards against upstream drift invalidating cached citations.

### 2.3 Organizational inputs

Risk scoring data, role assignments, measurement data, incident logs, AI system inventories, control-applicability justifications. These describe the operator's AI management system. Confidentiality varies by organization. For healthcare providers the risk register entries may reference HIPAA-relevant systems; for public-sector operators the role-matrix names identified individuals. The threat model treats inputs as potentially sensitive and minimizes their persistence footprint.

### 2.4 Tool-invocation authority

The set of declarations in `tools/registry.py` that marks each plugin as `is_read_only=True`, `is_concurrency_safe=True`, `is_destructive=False`, and `requires_human_approval=False`. Hermes uses these declarations to make permission and scheduling decisions without executing plugin code. The declaration is a security contract: a plugin that lies about being read-only bypasses the harness's primary defense.

### 2.5 Code integrity

The plugin modules themselves, the registry, the workflows, the persona files (`aigovclaw/persona/SOUL.md`, `aigovclaw/persona/IDENTITY.md`), and the test suite. A tampered plugin module produces falsified artifacts that the harness cannot detect. Code integrity is defended at Boundary A (PR review, CI) and Boundary B (ref pinning).

## 3. STRIDE per component

Each subsection enumerates threats for one component. Ratings assume mitigations listed in Section 5 are in place.

### 3.1 Plugin code (`plugins/<name>/plugin.py`)

Plugins are pure-Python modules with zero runtime dependencies outside the standard library. They accept a dict, return a dict, and have no filesystem, network, or shared-state side effects. The threat surface is therefore narrow but consequential: a compromised plugin module can produce falsified governance artifacts that auditors rely on.

| Threat | STRIDE category | Component | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|---|---|
| Malicious plugin PR adds network-exfiltration code paths | Tampering, Information disclosure | Plugin code | Low | High | Two-reviewer requirement on plugin PRs, consistency audit at `tests/audit/consistency_audit.py`, contributor contract in `plugins/README.md` prohibiting networking libraries, CI enforcement of standard-library-only imports | Low |
| Malicious plugin PR introduces arbitrary code execution at load time (module-level side effects) | Elevation of privilege, Tampering | Plugin code | Low | High | Plugin contract requires module-level constants only; CI audit flags module-level function calls outside constant assignment | Low |
| Plugin falsely declares safety properties (claims `is_read_only` but writes to disk) | Spoofing, Elevation of privilege | Plugin code | Low | High | `tools/tests/test_registry.py` asserts declared properties match observed behavior; plugins have no filesystem-write code paths in the reference implementations | Low |
| Plugin emits non-deterministic output for deterministic input (breaks audit reproducibility) | Tampering, Repudiation | Plugin code | Medium | Medium | Plugin contract in `plugins/README.md` mandates determinism; tests assert fixed output for fixed input | Low |
| Plugin hallucinates content fields not present in input (invents risks, controls, owners) | Tampering | Plugin code | Medium | High | Anti-hallucination invariants in `plugins/README.md` Section "Anti-hallucination invariants"; warnings-not-errors pattern surfaces gaps; reviewers reject plugins that silently default | Low |
| Plugin raises `ValueError` on a well-formed input, blocking legitimate workflow | Denial of service | Plugin code | Medium | Low | Structural-vs-content split in `plugins/README.md` Section "Validation stance"; content gaps surface as warnings, not errors | Low |
| Plugin drops or truncates citations below the `STYLE.md` required format | Tampering, Repudiation | Plugin code | Low | High | Citation format test asserts the prefix on every emitted citation; `tests/audit/consistency_audit.py` catches structural drift | Low |
| Plugin imports a third-party library in a later commit, introducing supply-chain surface | Tampering, Elevation of privilege | Plugin code | Low | High | CI asserts plugins use standard library only; contributor contract prohibits third-party imports in plugins | Low |
| Plugin logic contains an integer-overflow or recursion error triggered by crafted input | Denial of service | Plugin code | Low | Medium | Input validation caps list sizes and enum ranges; Hermes iteration budget bounds total compute | Low |

### 3.2 Plugin inputs (organizational JSON: risks, role assignments, measurements)

Inputs are provided by the caller (a Hermes workflow, a user invoking the plugin directly, or an upstream pipeline). They are trusted as organizational assertions but are structurally validated before any business logic runs. The threat surface is dominated by input-driven attacks on the plugin and by the confidentiality of the input content itself.

| Threat | STRIDE category | Component | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|---|---|
| Caller provides structurally invalid input (missing required fields, wrong types) | Denial of service | Plugin inputs | High | Low | `_validate` functions raise `ValueError` before business logic; registry validates a second time | Low |
| Caller provides structurally valid but semantically falsified inputs (fake risk ratings, invented role assignments) | Tampering, Repudiation | Plugin inputs | Medium | High | Out of AIGovClaw's threat model; organizational governance must verify inputs; `agent_signature` and timestamp provide forensic traceability if falsification is later detected | Medium |
| Extremely large input (10,000-entry risk register) exhausts memory | Denial of service | Plugin inputs | Low | Medium | Harness iteration budget caps total compute; organizational throttle policy documented in `AGENTS.md` | Low |
| Input contains prompt-injection strings targeting downstream LLM consumers of the artifact | Elevation of privilege, Tampering | Plugin inputs | Medium | Medium | Plugins do not execute input content as instructions; Markdown renderers escape pipe characters in table cells; see Section 4.2 for cross-cutting LLM prompt-injection discussion | Medium |
| Input contains sensitive data (PII, PHI, trade secrets) that is then persisted to the evidence store | Information disclosure | Plugin inputs | Medium | Medium | Organizational data-classification policy governs what is fed to plugins; evidence-store filesystem permissions default to user-only (see Section 3.5); operator responsible for encryption at rest | Medium |
| Input contains path-like strings that downstream renderers or adapters interpret as filesystem paths | Tampering | Plugin inputs | Low | Medium | Plugins do not perform filesystem operations based on input content; renderers treat all string fields as opaque text; adapter-layer sanitization required before v1.0 (Section 6) | Low |
| Caller repeatedly sends near-identical large inputs to waste compute | Denial of service | Plugin inputs | Low | Low | Hermes rate limiting; harness iteration budget; plugins are CPU-bounded by input size | Low |

### 3.3 Tool registry (`aigovclaw/tools/registry.py`)

The registry exposes plugins as Hermes tools with declared safety properties. It is loaded once at Hermes startup and validates inputs before dispatching to `aigovops_tools.py`, which performs filesystem-path `importlib` loading of the plugin module. Threats here focus on the declaration-versus-behavior mismatch and on the dynamic-loading path.

| Threat | STRIDE category | Component | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|---|---|
| Registry entry declares `is_read_only=True` for a plugin that writes to disk (declaration-behavior mismatch) | Spoofing, Elevation of privilege | Tool registry | Low | High | `tools/tests/test_registry.py` cross-validates declarations against observed plugin behavior; plugin contract forbids filesystem writes | Low |
| Registry's `validate_inputs()` is bypassed by a caller invoking plugin directly via `importlib` | Elevation of privilege | Tool registry | Low | Medium | Plugin's own `_validate` runs regardless of caller path; defense in depth | Low |
| Plugin loader in `aigovops_tools.py` is induced to load a file outside the plugins directory (path traversal) | Elevation of privilege, Tampering | Tool registry | Low | High | `PLUGIN_TOOL_DEFS` list is hard-coded; plugin directory names are not derived from user input | Low |
| Registry's declarative properties are mutated at runtime by a compromised plugin | Tampering, Elevation of privilege | Tool registry | Low | High | Python module-level constants are not immutable by default; v1.0 should freeze the registry dict after load (Section 6) | Medium |
| Registry exposes a plugin that the operator did not intend to enable | Information disclosure, Elevation of privilege | Tool registry | Low | Medium | Explicit enumeration in `PLUGIN_TOOL_DEFS`; operator controls the list; install.sh does not auto-discover plugins | Low |
| Registry's input schema drifts from the plugin's actual `REQUIRED_INPUT_FIELDS` | Denial of service, Tampering | Tool registry | Medium | Low | Consistency audit at `tests/audit/consistency_audit.py` detects field-name drift; plugin test suite asserts required fields | Low |

### 3.4 Hermes runtime invocation (tool dispatch, approval gates)

Hermes is the runtime that executes tool invocations. AIGovClaw trusts Hermes to enforce permission posture declared in `config/hermes.yaml`. Threats here focus on the Hermes-AIGovClaw seam: incorrect approval-gate behavior, LLM manipulation leading to unauthorized invocation, and the effect of a compromised Hermes process on emitted artifacts.

| Threat | STRIDE category | Component | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|---|---|
| Jailbroken LLM instructs Hermes to invoke an AIGovOps tool with unauthorized inputs | Elevation of privilege, Tampering | Hermes runtime | Medium | Medium | All plugins are read-only; worst case is an unauthorized read that produces an artifact but modifies no state; destructive operations route to human approval per `persona/SOUL.md` | Medium |
| Hermes fails to enforce `requires_human_approval=True` on a destructive operation (for example, nonconformity closure with ineffective outcome) | Elevation of privilege | Hermes runtime | Low | High | Persona refusals in `persona/SOUL.md` act as a second layer; plugin itself surfaces warnings for judgment-required outcomes; Hermes upstream is responsible for the primary approval gate | Medium |
| Compromised Hermes process tampers with emitted artifact dict before it reaches the filesystem store | Tampering | Hermes runtime | Low | High | `agent_signature` and timestamp embedded by the plugin; post-emission tampering is detectable only if artifacts are signed (gap; Section 6) | Medium |
| Hermes iteration budget is exhausted by repeated invocations, blocking legitimate work | Denial of service | Hermes runtime | Low | Low | Budget is per-session and resets; operator can adjust in `config/hermes.yaml` | Low |
| Hermes logs expose plugin inputs or outputs containing sensitive data | Information disclosure | Hermes runtime | Medium | Medium | Hermes log verbosity is operator-configurable; operator responsible for log rotation and access control; AIGovOps plugins do not log independently | Medium |
| Hermes invokes a plugin under a user identity without producing an audit-log entry that attributes the invocation to the calling actor | Repudiation | Hermes runtime | Low | High | `audit-log-generator` plugin produces the audit entry; Hermes workflow invokes it as a companion step; v1.0 should enforce the companion-step pattern as a harness policy (Section 6) | Medium |
| Hermes approval queue is flooded with low-value requests, causing operator to approve by reflex (approval fatigue) | Spoofing (via social engineering), Elevation of privilege | Hermes runtime | Medium | Medium | Persona refusals minimize approval-request volume; most plugins never escalate; approval-gate rate limiting is a v1.0 gap (Section 6) | Medium |

### 3.5 Filesystem evidence store (`~/.hermes/memory/aigovclaw/<artifact>/`)

Emitted artifacts are written to the operator's home directory under Hermes memory. The store is append-oriented (new entries reference prior entries rather than replacing them) but not cryptographically append-only. Threats focus on post-emission tampering, unauthorized disclosure, and availability.

| Threat | STRIDE category | Component | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|---|---|
| Operator (or malware running under operator account) modifies an emitted audit-log entry after the fact | Tampering, Repudiation | Evidence store | Medium | High | Timestamp and `agent_signature` provide a baseline; immutable-log guarantees require append-only filesystem semantics or content signing (gap; Section 6) | High |
| Operator deletes an emitted artifact to hide a governance failure | Tampering, Repudiation | Evidence store | Medium | High | Auditor practice treats missing evidence as a finding; no cryptographic guarantee of completeness without hash chaining (gap; Section 6) | High |
| Another user on the host reads the evidence store and learns organizational risk data | Information disclosure | Evidence store | Low | Medium | Default filesystem permissions on `~/.hermes/` are user-only on macOS and Linux; operator responsible for maintaining permissions; multi-user host deployment is not recommended | Low |
| Disk fills up and prevents new artifact emission | Denial of service | Evidence store | Low | Medium | Plugins themselves do not write; write failure surfaces at the workflow layer with a clear error; operator responsible for disk monitoring | Low |
| Backup process copies evidence store to a destination with weaker access controls | Information disclosure | Evidence store | Medium | Medium | Operator's backup policy is out of scope for AIGovClaw; documented in security-posture as an organizational responsibility | Medium |
| Symlink inside the evidence store points to a file outside the store, causing writes to escape | Tampering, Elevation of privilege | Evidence store | Low | Medium | Plugins do not write directly; the workflow layer writes using fixed relative paths; v1.0 should add a symlink-rejection check on the writer (Section 6) | Low |
| Evidence store content is indexed by a background process (Spotlight, Recoll) and becomes searchable outside the intended audit context | Information disclosure | Evidence store | Medium | Low | Operator can exclude the directory from indexers; AIGovClaw does not enforce this | Medium |

### 3.6 Framework-monitor (GitHub Actions workflow)

`framework-monitor.yml` runs on a scheduled cron in GitHub Actions, fetches upstream standards text (ISO product pages, NIST publications, EU AI Act consolidated text), and raises an issue if the upstream has changed since the last observed hash. It is the only AIGovOps component that makes network calls. Threats focus on the CI environment and on upstream-source manipulation.

| Threat | STRIDE category | Component | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|---|---|
| Dependency pulled by the workflow (`requests==2.31.0`, `pyyaml==6.0.1`) has a known CVE or supply-chain compromise | Tampering, Elevation of privilege | Framework-monitor | Low | Medium | Pinned versions in workflow; Dependabot enabled on the repo; CI-only blast radius (no production code path touched) | Low |
| Upstream standards site is compromised and serves malicious content that the workflow fetches | Tampering | Framework-monitor | Low | Low | Workflow compares hashes only; it does not execute upstream content; falsified hash triggers an issue for human review | Low |
| Upstream site is unreachable, preventing monitoring for drift | Denial of service | Framework-monitor | Medium | Low | Workflow failure emits a notification; manual fetch remains available; drift detection is a monthly cadence, not minute-level | Low |
| Attacker with write access to the repo modifies the workflow to exfiltrate secrets | Information disclosure, Elevation of privilege | Framework-monitor | Low | High | Workflow has no repository secrets beyond `GITHUB_TOKEN`; branch protection on `main` requires PR review | Low |
| Workflow runs on a compromised runner image | Tampering, Elevation of privilege | Framework-monitor | Low | Medium | GitHub-hosted runners; AIGovOps does not self-host; operator can switch to self-hosted if policy requires | Low |
| Workflow output (auto-opened issues) reveals internal version identifiers that aid reconnaissance | Information disclosure | Framework-monitor | Low | Low | Issue content is public on a public repo; no internal identifiers are used | Low |

### 3.7 Future MCP server (exposes plugins as MCP tools to external clients)

A planned v1.0 component that exposes AIGovOps plugins over the Model Context Protocol so that external clients (other Claude Code sessions, IDE integrations, custom agents) can invoke them. The MCP server is not yet implemented. Threats are cataloged in advance so that the implementation is built with them in mind.

| Threat | STRIDE category | Component | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|---|---|
| Unauthenticated external client invokes plugins over MCP | Elevation of privilege, Information disclosure | MCP server | High (if deployed without auth) | High | v1.0 must ship with an explicit allowlist of authenticated clients; stdio-only transport by default; operator opts in to network transport (Section 6) | Medium |
| Authenticated client uses a valid token to invoke plugins with adversarial inputs | Tampering, Elevation of privilege | MCP server | Medium | Medium | Plugin input validation is identical whether invoked via registry or MCP; plugins are read-only | Low |
| MCP server logs plugin inputs or outputs to a file with weaker access controls than the evidence store | Information disclosure | MCP server | Medium | Medium | v1.0 spec must mandate that MCP logs honor the same permissions as the evidence store; log fields to exclude must be documented (Section 6) | Medium |
| MCP server receives a malformed protocol message that crashes the process | Denial of service | MCP server | Medium | Low | MCP protocol library handles framing; plugin invocations are isolated per message; process restart is operator-controlled | Low |
| MCP server advertises plugin capabilities that include ones the operator has not enabled | Spoofing, Information disclosure | MCP server | Low | Medium | v1.0 spec must require that advertised capabilities match an operator-maintained allowlist, not the full registry (Section 6) | Low |
| Client claims a tool invocation that never occurred, or denies one that did | Repudiation | MCP server | Medium | Medium | Every MCP-originated invocation produces an audit-log entry citing the client identifier; v1.0 spec must require this (Section 6) | Medium |

### 3.8 Future GRC adapter layer (pushes artifacts to VerifyWise, Vanta, Notion, etc.)

A planned v1.0 component that translates plugin output dicts into the schemas of GRC platforms and pushes them over MCP or direct API. The adapter layer is not yet implemented. Threats focus on credential handling (MCP mitigation applies) and on output sanitization before transmission.

| Threat | STRIDE category | Component | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|---|---|
| Adapter transmits an artifact containing a prompt-injection payload to a destination whose UI renders it into an LLM prompt | Elevation of privilege, Tampering | GRC adapter | Medium | Medium | v1.0 spec must require a sanitization pass before transmission: strip control characters, cap string lengths, escape Markdown metacharacters per destination's rendering rules (Section 6) | Medium |
| Adapter transmits an artifact to the wrong destination (routing misconfiguration) | Information disclosure | GRC adapter | Low | High | Adapter config in `config/adapters.yaml` is explicit per-artifact-type; operator reviews routing table; distribution audit entry citing `ISO/IEC 42001:2023, Clause 7.5.3` records the destination | Low |
| Adapter stores destination credentials in a config file | Information disclosure, Elevation of privilege | GRC adapter | Low | High | Credentials are never handled by AIGovClaw; MCP server owns them; documented in security-posture Boundary 3 | Low |
| Adapter silently drops an artifact transmission and the operator assumes it was delivered | Repudiation, Tampering | GRC adapter | Medium | High | Every adapter push emits either a success or failure audit-log entry; no silent drops; v1.0 spec must assert this invariant (Section 6) | Low |
| Adapter retries a failed push indefinitely, causing backpressure on the destination | Denial of service | GRC adapter | Low | Low | v1.0 spec must mandate bounded retry with exponential backoff; operator configurable (Section 6) | Low |
| Adapter exposes an artifact to a destination the organizational policy classifies as external sharing without approval | Elevation of privilege | GRC adapter | Low | High | Persona refusal in `persona/SOUL.md` requires per-transmission authorization for third-party destinations; v1.0 spec must preserve this in the adapter layer (Section 6) | Low |

### 3.9 Continuous integration (`.github/workflows/ci.yml` and audit)

CI runs on every PR and push to main. It executes the plugin test suite, the tools registry tests, the no-em-dash test, the no-hedging test, and the consistency audit. CI is the enforcement point for the style and structural contracts that underpin the other components' threat models.

| Threat | STRIDE category | Component | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|---|---|
| CI job is bypassed via admin force-merge on main | Tampering | CI | Low | High | Branch protection on main requires CI pass; operator policy prohibits admin bypass; monitored via repo settings audit | Low |
| CI runner is compromised and emits false pass | Tampering | CI | Low | High | GitHub-hosted runners; same residual as framework-monitor; operator can switch to self-hosted if policy requires | Low |
| A test is deleted in a PR and the deletion is not noticed in review | Tampering | CI | Medium | Medium | Test file count tracked in consistency audit; v1.0 should add explicit assertion that test counts are non-decreasing (Section 6) | Medium |
| CI consumes excessive minutes and is disabled to save cost | Denial of service | CI | Low | Medium | Test suite is standard-library-only and runs in seconds; no anticipated budget pressure | Low |

## 4. Cross-cutting threats

Threats that touch multiple components or that arise from properties of the system as a whole rather than any single component.

### 4.1 Supply chain (pip dependencies)

Plugins use the Python standard library exclusively. This is the strongest supply-chain posture available: zero third-party code, zero transitive dependencies, zero pip install surface at plugin-execution time. The only dependency-bearing component is the framework-monitor workflow, which pins `requests==2.31.0` and `pyyaml==6.0.1`. Its blast radius is limited to the CI runner because it touches no production code path.

Two residual supply-chain threats remain. First, the Python interpreter itself is an implicit dependency; an operator running a compromised Python build would execute compromised plugin code. AIGovClaw does not protect against this. Second, the operator's Hermes Agent installation has its own dependency graph; AIGovClaw inherits whatever supply-chain assurance Hermes provides and no more.

v1.0 should add SBOM generation in CI so that operators can audit the dependency set before deployment. See Section 6.

### 4.2 LLM prompt injection via organizational input fields

Plugin inputs include free-text fields: risk descriptions, owner names, justifications, incident narratives. A malicious or careless upstream pipeline can embed prompt-injection payloads in these fields. The artifact dict propagates these strings through the evidence store to downstream consumers. Any consumer that feeds an artifact back into an LLM prompt (for dashboards, summarization, or next-iteration governance planning) becomes the injection target.

AIGovOps mitigations:

- Plugins do not execute input content as instructions. They are data transformers, not interpreters.
- Markdown renderers escape pipe characters in table cells so a payload cannot break table structure.
- Renderers truncate excessively long strings so a payload cannot exhaust a downstream renderer.

AIGovOps non-mitigations:

- Plugins do not attempt to detect prompt-injection content. Detection is unreliable and the false-negative rate is too high to be a security boundary.
- The evidence store does not sanitize content on write. Storage is by design a faithful record of what the input contained.

Downstream responsibility:

- Any LLM-consuming downstream system must sanitize artifact content before feeding it to a model. This includes Hermes itself when it summarizes prior artifacts, and any GRC-platform integration that renders artifact content into an LLM-driven UI.
- v1.0 should document a sanitization pattern (delimiting, structured extraction, role separation) for downstream consumers. See Section 6.

Likelihood: Medium. Impact: Medium. Residual risk: Medium. The risk is bounded because AIGovOps itself does not act on input content, but a downstream consumer in the operator's deployment stack can be compromised if it does not sanitize.

### 4.3 Tampering with written audit evidence after the fact

The evidence store is a directory tree under `~/.hermes/memory/aigovclaw/`. Files are JSON and Markdown. There is no cryptographic guarantee that a file written at time T has not been modified at time T+1. An operator with write access to the directory (which is the default posture) can edit emitted artifacts.

This is the most significant gap in the current posture. Certification-grade audit evidence requires either:

1. Append-only filesystem semantics (copy-on-write filesystem with snapshot-based retention, or a WORM volume), or
2. Content signing (detached signatures over each artifact, with the signing key held by a separate key-management component), or
3. Hash chaining (each artifact embeds the hash of the prior artifact, producing a tamper-evident log).

Option 3 is the lowest-friction path for a v1.0 open-source release. It does not require key management infrastructure. It makes tampering detectable rather than preventing it.

The current mitigation is organizational: the operator is also the subject of the audit, and tampering is a disciplinary matter. This is not adequate for shared-custody deployments.

Likelihood: Medium. Impact: High. Residual risk: High pending implementation of hash chaining or signing in v1.0. See Section 6.

### 4.4 Abuse of `is_read_only=True` declarations

Every AIGovOps tool is declared `is_read_only=True`. This declaration is load-bearing: Hermes uses it to skip approval prompts, to allow concurrent execution, and to classify the tool as safe for autonomous use. The declaration is enforced by two mechanisms: (a) the plugin contract prohibits filesystem and network side effects, and (b) `tools/tests/test_registry.py` cross-validates declared properties.

The threat is that a future plugin violates the read-only contract without the registry declaration changing. Specifically:

- A plugin that calls out to a subprocess (for example, to invoke a native PDF renderer) is no longer read-only with respect to system state.
- A plugin that writes to a temp file for intermediate processing is no longer read-only with respect to the filesystem.
- A plugin that reads environment variables containing secrets is no longer read-only with respect to confidentiality.

The current CI audit catches `import` statements for networking libraries. It does not catch subprocess calls, tempfile creation, or environment-variable reads. A v1.0 hardening pass should expand the audit to cover these. See Section 6.

Likelihood: Low (new plugins are reviewed). Impact: High (a read-only declaration is a primary harness permission signal). Residual risk: Medium pending audit expansion.

### 4.5 Lead-implementer / auditor collusion

An ISO 42001 lead implementer deploying AIGovOps for their own organization has write access to the evidence store, read access to all framework text, and the authority to invoke any plugin. A lead implementer colluding with an external auditor can produce falsified audit evidence that AIGovOps cannot detect.

This is out of scope for a technical threat model. It is an organizational control failure and is addressed by the ISO 42001 standard itself through `ISO/IEC 42001:2023, Clause 9.2` (internal audit) and `Clause 5.3` (role segregation), both of which require independence between the implementer and the auditor.

AIGovOps documents this as out of scope in Section 7 and in `docs/security-posture.md`. The agent-signature and timestamp on every artifact provide forensic traceability if collusion is later suspected, but they do not prevent it.

### 4.6 Cross-tenant contamination (future multi-tenant deployment)

Current AIGovClaw is single-operator. A future multi-tenant deployment (one AIGovClaw serving multiple organizations through a shared Hermes instance) introduces cross-tenant threats: tenant A's inputs leaking into tenant B's artifacts through shared memory or filesystem namespaces, tenant A invoking tools with tenant B's identity through a compromised Hermes session.

Multi-tenancy is not in the v1.0 scope. The threat is cataloged to preempt accidental multi-tenant deployment. If an operator intends to serve multiple organizations, the recommended posture is one AIGovClaw instance per tenant with independent evidence stores and independent Hermes processes.

## 5. Mitigations already in place

This section enumerates mitigations that exist in the current codebase as of 2026-04-18. Each citation references a specific file or documented pattern.

### 5.1 Plugin-level input validation raising `ValueError`

Every plugin implements a `_validate` function that checks required fields, types, and enum values before business logic runs. Structural problems raise `ValueError` with a message naming the offending field. See the `REQUIRED_INPUT_FIELDS` tuple and `_validate` function in any `plugins/<name>/plugin.py`. This is the first layer of defense at Boundary C.

Test coverage: every plugin's `tests/test_plugin.py` includes one test per validation error path, asserting the correct exception type and message.

### 5.2 Warnings-not-errors pattern for content gaps

Content problems (missing owner, empty justification, referenced ID not found in inventory) surface as per-record `warnings` lists inside the output dict. They do not raise. This pattern is documented in `plugins/README.md` Section "Validation stance" and is enforced by plugin tests. The pattern prevents a halt-on-first-gap failure mode that would let an auditor infer the missing field rather than see all gaps at once.

### 5.3 No network calls in plugins

Plugins import only from the Python standard library. The CI audit at `tests/audit/consistency_audit.py` inspects plugin sources for imports from networking libraries (`requests`, `urllib.request`, `http.client`, `socket`, `ssl`) and flags any occurrence. The `framework-monitor.yml` workflow is the only component that makes network calls, and it runs only in CI.

### 5.4 Deterministic output

Plugins produce byte-identical output for byte-identical input. Tests assert this by running the plugin twice and comparing outputs. The determinism guarantee supports reproducible audits: an auditor can replay a prior invocation and confirm that the evidence was not altered.

### 5.5 `STYLE.md` enforcement

Prohibited content is enforced by explicit tests:

- No em-dashes (U+2014). Test: each plugin's test suite asserts `"\u2014"` does not appear in rendered output.
- No emojis. Test: the consistency audit inspects rendered output for non-BMP code points and flags them.
- No hedging language. Test: the audit scans for a curated hedging-phrase list (see `tests/audit/consistency_audit.py` for the canonical list) and flags matches.

The style rules are not cosmetic. They enforce a definite-determination posture in governance artifacts: an auditor reading "the organization might have considered" cannot rely on the statement; an auditor reading "the organization considered" can.

### 5.6 `agent_signature` on every artifact

Every emitted artifact dict includes an `agent_signature` field of the form `<plugin-name>/<semver>`. The signature identifies which plugin version produced the record. Version-aware adapters can route artifacts correctly across plugin upgrades. Forensic investigators can identify whether a specific artifact was produced by a known-good or known-compromised plugin version.

Limitation: the signature is a string field, not a cryptographic signature. It is evidence of origin under an honest-plugin assumption, not proof. v1.0 signing is addressed in Section 6.

### 5.7 Standard-library-only tests

Tests use `unittest` (standard library) and are runnable both under `pytest` and as standalone scripts. Zero test-time dependencies means the test suite cannot be compromised by a third-party test framework supply chain. An auditor replicating the test environment needs only a Python interpreter.

### 5.8 Plugin contract enforcement at review time

`plugins/README.md` defines the plugin-author contract: module-level constants, `generate_<artifact>()` entry point, `render_markdown` and `render_csv` rendering functions, validation split, anti-hallucination invariants, output dict shape, citation format. The contract is enforced through PR review (`CONTRIBUTING.md` and `AGENTS.md`) and through the consistency audit.

The audit catches: structural drift (functions renamed, required fields dropped), citation-format drift (missing ISO/NIST/EU prefix), presence of prohibited content (em-dashes, emojis), and missing required output fields (`timestamp`, `agent_signature`, `citations`, `warnings`, `summary`).

### 5.9 Declarative safety properties

Every plugin is registered with `is_read_only=True`, `is_concurrency_safe=True`, `is_destructive=False`, `requires_human_approval=False`, `max_result_size_bytes=1_000_000`. Hermes uses these to make permission and scheduling decisions without executing plugin code. `tools/tests/test_registry.py` cross-validates declarations against observed behavior. A plugin that declares itself read-only but writes to disk fails its own tests before reaching the registry.

### 5.10 Persona refusals

`aigovclaw/persona/SOUL.md` declares behaviors AIGovClaw refuses regardless of instruction: no out-of-workspace filesystem writes, no unconfirmed shell execution, no third-party transmission without per-transmission authorization, no credential handling. These refusals are enforced at the Hermes permission-posture level in `config/hermes.yaml` and at the plugin-contract level in `plugins/README.md`.

### 5.11 Auditability through paired audit-log entries

Every governance event (artifact emission, adapter push, approval decision) produces an audit-log entry citing `ISO/IEC 42001:2023, Clause 7.5.2` (documented information) or `Clause 7.5.3` (distribution). The entry names the plugin invoked, the inputs received, the outputs produced, and the timestamp. The audit log is the authoritative record.

### 5.12 MIT licensing and open review

The repository is MIT-licensed and publicly readable. Every contribution passes through PR review with at least one reviewer. The repo's branch protection requires CI pass on main. Open source is not a security property on its own, but it transforms an adversary's effort: a malicious change must survive public review rather than being merged silently.

## 6. Mitigations required before v1.0

Concrete gaps identified by the preceding sections. Each is stated as a definite action, not a hedged recommendation.

### 6.1 Schema-pin dependencies

Add a `requirements-dev.txt` with pinned versions for every development-time dependency (pytest if added, linters, type checkers). CI currently pins `requests==2.31.0` and `pyyaml==6.0.1` inside `framework-monitor.yml`; extract all pins into a central file. Add Dependabot configuration that opens PRs for version bumps with release-note context. Fail CI on any unpinned install.

### 6.2 SBOM generation in CI

Add a CI job that emits a CycloneDX or SPDX SBOM on every release tag. Publish the SBOM as a release asset. Operators downloading a release should be able to verify the dependency set offline before deploying. Use `cyclonedx-py` or equivalent, pinned.

### 6.3 Signing of emitted artifacts

Every plugin output dict carries `agent_signature` as a string. Upgrade this to a detached cryptographic signature over the canonical JSON serialization of the artifact. Sign with an operator-held Ed25519 key. Signature verification happens at evidence-store read time and at adapter transmission time. This converts `agent_signature` from weak origin evidence to strong origin evidence.

Key management is an operator responsibility. Document the recommended pattern: store the signing key in the OS keychain, rotate annually, countersign the prior key's revocation with the new key.

### 6.4 Append-only evidence log

Implement hash chaining in the evidence store. Every new artifact file embeds the SHA-256 of the prior artifact file in the same artifact directory. The first artifact embeds a genesis hash. Verification walks the chain from genesis forward and flags any break. Tampering with a historical artifact breaks the chain at that point forward.

Hash chaining does not prevent tampering; it makes tampering detectable. Combined with artifact signing (Section 6.3), it makes tampering infeasible without either the signing key or the operator's collusion.

### 6.5 MCP server allowlist

Before shipping an MCP server, implement an operator-managed allowlist of authenticated client identities. Default posture: stdio transport only, single-client (the operator's own Hermes instance). Operator opts in to network transport by editing `config/mcp.yaml` and adding client public keys. Reject unauthenticated connections at the protocol handshake.

Every MCP-originated invocation must produce an audit-log entry that names the client identifier. No silent invocations.

### 6.6 Adapter-layer output sanitization

Before shipping the GRC adapter layer, implement a sanitization pass on outbound artifact content. Per destination: strip ASCII control characters, cap string field lengths to the destination's known limits, escape Markdown metacharacters per the destination's rendering rules, reject fields containing null bytes or Unicode directionality overrides.

Document the sanitization contract in `aigovclaw/adapters/README.md`. Each adapter subclass overrides a `sanitize(artifact_dict, destination_profile) -> artifact_dict` method. Integration tests feed known prompt-injection payloads and assert they are neutralized.

### 6.7 Freeze the tool registry at load time

After `tools/registry.py` assembles the registry dict at Hermes startup, freeze it with `types.MappingProxyType` or a similar read-only wrapper. A compromised plugin should not be able to mutate sibling plugin declarations at runtime.

### 6.8 Expand the read-only audit

Extend `tests/audit/consistency_audit.py` to scan plugin sources for:

- `subprocess` imports or calls.
- `tempfile` imports or calls.
- `os.environ` reads and `os.getenv` calls.
- `open()` calls in write mode.
- `pathlib.Path.write_*` calls.

Any occurrence flags the plugin as non-read-only. The audit runs in CI and blocks merges that would silently break the `is_read_only=True` declaration.

### 6.9 Symlink-rejection check on the evidence-store writer

The workflow layer that writes artifact files should reject any target path whose directory resolves through a symlink to a location outside `~/.hermes/memory/aigovclaw/`. Use `os.path.realpath` and compare to the intended prefix. Fail the write with a clear error; do not follow the symlink.

### 6.10 Test-count monotonicity assertion

Add a CI check that compares the test count in the current commit to the test count on main. Deletions of tests require an explicit justification in the PR body. Prevents silent regression of test coverage.

### 6.11 Approval-gate rate limiting

In `aigovclaw/config/hermes.yaml` or its v1.0 successor, add a per-session ceiling on approval requests. If exceeded, additional approval requests queue for batched review rather than reflex-approval. Prevents approval fatigue.

### 6.12 Adapter retry policy

Implement bounded retry with exponential backoff in the adapter layer. Default: three retries, 1s/4s/16s backoff, then escalate to human review with a nonconformity record cited against `ISO/IEC 42001:2023, Clause 10.2`. No silent drops. No unbounded retries.

### 6.13 Downstream-sanitization guidance document

Add `docs/downstream-sanitization.md` describing the sanitization pattern any LLM-consuming downstream system should apply before feeding AIGovOps artifact content to a model. Cover: delimiting with unambiguous sentinels, structured extraction over free-text pasting, role-separation in system prompts, length caps, prohibited-character filters. This is guidance, not code; operators deploy their own downstream systems.

## 7. Out of scope

The following threats are out of scope for the current threat model. Each is listed with the rationale and the party responsible.

### 7.1 Host OS compromise

An operator running AIGovClaw on a compromised host has lost the game at a lower layer. Disk encryption, OS patching, endpoint detection, and user-account hygiene are the operator's responsibility. AIGovClaw's filesystem-permission defaults assume a single-user host and a non-compromised OS.

### 7.2 LLM model weights supply chain

Hermes Agent invokes an LLM provider's model. If the model weights have been poisoned at training time or backdoored at distribution time, no amount of input validation at the tool-registry layer protects against the resulting behavior. The LLM provider is responsible. The operator's choice of provider is a trust decision outside AIGovClaw's scope.

### 7.3 ISO auditor colluding with implementer

An ISO 42001 lead implementer with full access to the evidence store can collude with an external auditor to certify a non-compliant AI management system. This is an organizational control failure. `ISO/IEC 42001:2023, Clause 5.3` (role segregation) and `Clause 9.2` (internal audit independence) address it at the standard level. AIGovClaw's `agent_signature` and timestamp provide forensic evidence if collusion is later suspected; they do not prevent it.

### 7.4 Hermes Agent internal compromise

AIGovClaw trusts Hermes to enforce the permission posture declared in `config/hermes.yaml`. A vulnerability in Hermes that allows permission bypass is reported to the Hermes vendor (Nous Research) via the disclosure process in `SECURITY.md`. AIGovClaw's defense-in-depth (plugin-level validation, read-only plugins, no filesystem side effects) bounds the blast radius of a Hermes bypass but does not prevent the bypass itself.

### 7.5 LLM provider infrastructure

The LLM provider's data-handling practices, logging, and retention policies are outside AIGovClaw's scope. An operator with strict data-residency requirements selects a provider accordingly. AIGovClaw does not verify provider compliance.

### 7.6 Destination GRC platform compromise

If an operator configures AIGovClaw to push artifacts to a Notion workspace that has been compromised, the attacker receives governance artifacts the operator explicitly configured to send. This is outside AIGovClaw's threat model. Mitigation is documented in `docs/security-posture.md` Section 3, Scenario 2: operators should classify artifact sensitivity and make informed routing choices.

### 7.7 User-operated external systems

Data-engineering pipelines, upstream risk-intake forms, and organizational workflow tools that feed inputs into AIGovOps plugins are operated by the user. Their integrity is the user's responsibility. Falsified inputs produce falsified outputs; the threat is organizational, not technical.

### 7.8 Physical security of the host

AIGovClaw does not protect against physical access to the host machine. An attacker with console access can read the evidence store regardless of filesystem permissions. Disk encryption at rest (FileVault, LUKS) is the operator's responsibility.

### 7.9 Side-channel attacks on plugin execution

Timing, cache, power, and acoustic side channels against plugin execution are out of scope. Plugins process non-secret organizational data and emit non-secret artifacts; the adversary has no secret to extract through a side channel.

### 7.10 Adversary with GitHub organization-admin access

An adversary with admin rights to the `ZOLAtheCodeX` GitHub account can modify branch protection, bypass CI, and merge arbitrary content. This is a credential-compromise event handled at the GitHub account level (2FA, physical security key, recovery-code custody). It is out of scope for the AIGovClaw code-level threat model.

## 8. Review cadence and change log

This document is reviewed annually and after any of the following events:

- A new plugin is added to the catalogue.
- A new trust boundary is introduced (for example, when the MCP server ships).
- A STRIDE category exhibits a new exemplar threat not previously cataloged.
- A mitigation listed in Section 5 is removed or weakened.
- A mitigation listed in Section 6 is implemented (move to Section 5).

Changes to this document require PR review by two maintainers, one of whom must have security-review training (OSCP, CISSP, CCSP, or equivalent documented experience).

Framework citations in this document: `ISO/IEC 42001:2023, Clause 5.3`, `Clause 7.5.2`, `Clause 7.5.3`, `Clause 9.2`, `Clause 10.2`. NIST references: `GOVERN 1.1` implicit in the governance-role segregation discussion, `MANAGE 4.2` implicit in the nonconformity escalation discussion.

Last reviewed: 2026-04-18.
