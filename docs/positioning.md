# AIGovOps positioning

**Status:** active. Reflects the OSS-first commitment confirmed 2026-04-18.

## One-line positioning

AIGovOps is open-source infrastructure for AI governance operationalization. Not a product. Not a platform. A shared set of plugins, skills, and a runtime that any practitioner or organization can pick up and use, modify, or embed, under the MIT license.

## The OSS commitment

AIGovOps and AIGovClaw remain MIT-licensed and free forever. The code is the common good; the operationalization knowledge baked into it is what the field has been missing. Vendors of proprietary GRC platforms have mapped frameworks for years; they have not operationalized them in code. AIGovOps does.

This is the explicit commitment:

- Every plugin, skill, workflow, and adapter lives in the public repos at MIT.
- No paid tier of the engine. No paid tier of the hub. No paid adapters.
- No feature gating by license, by seat count, or by organization size.
- No tracking, no telemetry, no sign-up wall.
- No "open core" split where serious features live behind a paywall.

If an organization forks AIGovOps and builds a commercial product on top of it, that is allowed by the license and welcome by the project. The moat is the operationalization and the governance rigor, not the code distribution.

## The three surfaces (all open source)

| Surface | Purpose | Status |
|---|---|---|
| Engine (`aigovops` repo) | 12 plugins that produce governance artifacts; 3 skills that carry framework text; evals and audits. Python, stdlib-only. | released v0.1 |
| Runtime (`aigovclaw` repo) | Hermes Agent config that invokes the engine as tools. Jules dispatcher for background maintenance. MCP server exposing plugins to MCP-capable clients. | released v0.1 |
| Hub (`aigovclaw/hub/`) | Single-file HTML dashboard that reads the local evidence store. Local-only, no backend, no auth. | v0 landed 2026-04-18 |

## The adapter layer is configuration, not code you buy

AIGovClaw ships an MCP router. Organizations configure which artifact types route to which MCP servers (Notion, Linear, Google Drive, GitHub, Gmail, and any future MCP-capable GRC connector). AIGovClaw never handles destination credentials. Organizations already on VerifyWise, Vanta, Drata, OneTrust, ServiceNow GRC, or Archer connect via whatever MCP tools those vendors publish, if and when they publish them.

Fork-and-build is fine. Vendor-agnostic is the principle.

## How the project sustains itself

Compliance infrastructure that goes unmaintained is worse than no infrastructure. AIGovOps needs sustainable funding so it can keep pace with ISO 42001 amendments, NIST AI RMF updates, EU AI Act delegated acts, and whatever frameworks emerge next. The approach below monetizes around the project, not by extracting value from it.

| Path | What it is | Fit |
|---|---|---|
| Training and certification | Cohort and async courses on operationalizing ISO 42001, NIST AI RMF, EU AI Act. AIGovOps is the teaching artifact. Lead Implementer credential anchors pricing. | Primary |
| Consulting engagements | Bespoke operationalization work for organizations that want a practitioner-guided implementation. AIGovOps is the portfolio; the billable hours are the revenue. | Primary |
| Sponsored development | GitHub Sponsors and Open Collective tiers. Organizations sponsor specific framework overlays (FedRAMP AI, Singapore MAS, Canada AIDA, UK AISI). Code stays MIT. | Near-term |
| OSS grant funding | OpenSSF Alpha-Omega, Sloan Foundation, Mozilla Technology Fund, Ford Foundation NetGain. AI governance infrastructure is actively grant-funded right now. | Near-term |
| Commissioned attestations | Third-party practitioner attestation that an organization's AIGovOps run is evidence-grade. Not selling the tool; selling the signature under Lead Implementer credential. | Mid-term |
| Foundation stipend | Contribute to Linux Foundation AI and Data or CNCF AI WG. Foundation takes neutral governance; maintainer receives a stipend. | Mid-term |
| Book and speaking | "Operationalizing AI Governance" as a book. Conference keynotes. The project becomes the reference implementation named throughout. | Deferred until patterns battle-tested |
| Plugin bounty board | Algora or Gitcoin. Users post bounties for frameworks the core team hasn't prioritized. Code stays MIT. | Optional |

None of these paths require the code to be closed, gated, or paywalled. They require the maintainer to be credentialed and visible.

## How to support the project

- **Use it.** Run it against your organization's data. Open issues when the operationalization gaps appear. Every real-world use case sharpens the next release.
- **Sponsor it.** GitHub Sponsors tiers fund specific framework overlays. Sponsors are named in release notes unless they request otherwise.
- **Contribute.** Plugins, skills, adapter configs, evals. The plugin-author contract in `plugins/README.md` defines the bar. Certification-grade by design.
- **Hire us.** If you need operationalization work done inside your organization, commercial consulting is available and the project benefits from real-world cases.

## Why the engine is the moat, not the revenue

The architecture was always adapter-friendly. Every plugin emits a structured dict with stable field names, `agent_signature`, timestamp, citations, warnings. That is the contract. Any downstream system can consume it. Any upstream orchestrator can invoke it. The value compounds through:

1. **Operationalization depth.** Not "ISO 42001 mapped to controls" but "ISO 42001 Clause 6.1.3 emits this SoA row against this input, with these citations, these warnings, this agent signature."
2. **Framework coverage.** ISO 42001, NIST AI RMF with AI 600-1 GenAI overlay, EU AI Act with Articles 5/6/50 and Annex I/III. The three most-referenced AI governance frameworks in one place.
3. **Evidence rigor.** Every artifact survives auditor scrutiny. Every citation matches published text. Every warning points the human at the next action.
4. **Autonomy with audit.** The AIGovClaw runtime invokes plugins under declared safety properties. Jules dispatcher runs background maintenance under ISO 42001 Clause 9.1 audit-log coverage. Human approves every merge.

This is what the GRC vendors have not done. They have surfaces. We operationalize the substance. Both layers have value. Ours is the open layer.

## Priority order (unchanged; OSS-first does not slow the roadmap)

1. MCP server (shipped). Universal adapter. Any MCP-capable client ships us for free.
2. Hub v0 (shipped 2026-04-18). Local static dashboard, single-file HTML.
3. First real Jules run against a stale-check-safe playbook (next).
4. Notion reference adapter (configuration, not code).
5. Framework overlays driven by sponsor requests and grant scope.
6. Hub v1 with React + Tailwind + shadcn/ui (later, once hub v0 informs the layout).

## Decisions locked in

1. Hub stays local-only for v1. No hosted SaaS. If teams later want multi-user hosted, that is a separate fork or a separate project, not this one.
2. All adapters are OSS. The MCP router pattern removes the need for us to own destination-specific code.
3. No authentication, no telemetry, no account system in this project.
4. Governance artifacts stay under the organization's control. AIGovOps never pulls organizational data out of the user's environment.

## Non-goals

- Rebuilding a full GRC platform. Vendors have spent years on this. Do not compete on breadth of ISO 27001, SOC 2, GDPR controls. Own AI governance specifically.
- Replacing the auditor. AIGovOps produces audit evidence, not audit opinions. Clause 9.2 internal audit and Clause 9.3 management review still require qualified humans.
- Building a new framework. Every citation maps to published text from ISO, NIST, or the EU AI Act. No novel standards.
- Becoming a SaaS. The runtime is code you clone and run. Hosted operation is out of scope.

## Success criteria at the 12-month mark

- 1,000 GitHub stars on `aigovops` (OSS adoption signal).
- 5 sponsored framework overlays shipped.
- 1 OSS grant awarded.
- 3 practitioners independently running AIGovOps against real organizational data and publishing case studies.
- 1 training cohort delivered.

Last updated: 2026-04-18.
