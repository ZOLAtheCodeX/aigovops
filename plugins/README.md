# Plugins

This directory contains AIGovOps plugins. A plugin is an executable unit (Python, shell, or other runtime) that produces a concrete governance artifact: an audit log entry, a Statement of Applicability row, a risk register entry, a gap assessment, or similar output.

Plugins differ from skills in execution semantics. A skill is loaded as knowledge by an agent. A plugin is invoked as code, either by an agent or directly by a user.

## Plugin index

| Plugin | Output Artifact | Status |
|---|---|---|
| [audit-log-generator](audit-log-generator/) | ISO 42001-compliant audit log (JSON + human-readable) | stub |

## Plugin requirements

Every plugin must:

1. Live in a kebab-case directory under `plugins/`.
2. Contain a README.md describing inputs, outputs, and example invocation.
3. Produce deterministic output for deterministic input. Document any non-determinism in the README.
4. Use the citation formats defined in [STYLE.md](../STYLE.md) for any framework references in output.
5. Raise a clear error on missing or malformed input rather than producing degraded output.
6. Be registered in the plugin index above and in the repository [README.md](../README.md).

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full plugin submission checklist.
