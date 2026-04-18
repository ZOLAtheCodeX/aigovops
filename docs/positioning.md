# AIGovOps positioning

**Status:** draft for review. Not yet reflected in top-level README or marketing copy.

## One-line positioning

AIGovOps is the open-source engine for AI governance artifacts. AIGovClaw is the autonomous agent that runs it. Adapters connect both into the GRC platform the user already uses.

## The three surfaces

| Surface | Audience | Distribution | Business model |
|---|---|---|---|
| Engine (`aigovops`) | Python developers, compliance engineers, auditors validating outputs | PyPI, GitHub | MIT open source. Free forever. |
| Hub (`aigovclaw/hub`) | Solo practitioners, small governance teams without a GRC platform | Local install + optional hosted | Open source core. Optional hosted tier for teams. |
| Adapters (`aigovclaw/adapters/<target>`) | Organizations already on VerifyWise, Vanta, Drata, OneTrust, Notion, ServiceNow GRC, Archer | MCP server + per-target REST adapters | Open-source adapters for open GRCs. Paid adapters for closed-ecosystem enterprise GRCs. |

The plugin output contract already targets this split. Every plugin emits a structured dict with `agent_signature`, `timestamp`, `citations`, `warnings`, and stable field names. That is the adapter contract.

## Why this beats "extension only" or "standalone only"

**Extension only** (AIGovClaw as a plug-in to VerifyWise):
- Distribution advantage. Users stay where they work.
- Fatal flaw: platform risk. If VerifyWise pivots, is acquired, or builds native AI governance, the distribution evaporates. Tenant on someone else's land.
- Value capture compressed. Extensions tend to monetize as $5-20 per seat add-ons. Standalone AI governance platforms charge $50K-250K ACV. Same plugins, 100x pricing ceiling gap.

**Standalone only** (AIGovClaw as a new pane of glass):
- Full brand equity and pricing power.
- Fatal flaw: compliance leads will not adopt a 12th tool. Vanta did not win by building a new auditor workflow; they plugged into the existing evidence-request process.

**Dual-mode (proposed):**
- Same plugins power all three surfaces.
- Hub is the brand surface. Adapters are distribution. Engine is the moat.
- This is the Terraform / Prisma / LangChain pattern: OSS core is the lever, hosted and adapter layer is the business.

## What this changes in the current build

Almost nothing. The existing architecture was adapter-friendly by design. What we add:

```
aigovclaw/
  hub/                         NEW. Minimal web dashboard. Artifacts land here. Jules activity feed posts here. Humans triage action items.
  adapters/
    verifywise/                NEW. REST adapter. Write after MCP server is stable.
    vanta/                     NEW.
    notion/                    NEW. First candidate since user already uses Notion heavily.
    servicenow/                NEW. Later, enterprise.
  mcp_server/                  (being built in parallel) Universal MCP adapter. Any MCP-capable GRC can consume us.
```

## Priority order

1. MCP server (in flight). This is the universal adapter. Any MCP-capable client ships us for free.
2. Notion adapter. Proof-of-concept against a real API. Zola already uses Notion so dogfooding is trivial.
3. Hub v0. Minimal: a single-page HTML dashboard that reads `~/.hermes/memory/aigovclaw/` and renders a composite state. Not a web app. Just a static renderer run from the CLI.
4. VerifyWise adapter. Contingent on their API. Research their developer program before committing.
5. Vanta adapter. Their API is public, documented, and mature. Lower research cost, higher enterprise appeal.

## Decisions the user must make before Step 3

1. Hub hosting model: local-only for v1, or hosted SaaS from day one? Recommendation: local-only. Zero ops burden. Hosted comes later if teams ask for multi-user.
2. First paid adapter target: VerifyWise, Vanta, or ServiceNow GRC? Recommendation: Vanta. Mature API, enterprise buyer, AI governance is a gap in their product.
3. Monetization boundary: which adapters are paid versus open? Recommendation: all open-source GRC adapters are open source. Closed-ecosystem enterprise GRC adapters are paid. Aligns with user base economics.
4. Hub authentication: none for v1 (local-only), SSO for hosted? Recommendation: none for v1.

## Non-goals

- Rebuilding a full GRC platform. VerifyWise, Vanta, Drata, OneTrust have spent years on this. Do not compete on breadth of ISO 27001 / SOC 2 / GDPR controls. Own AI governance specifically.
- Replacing the auditor. AIGovOps produces audit evidence, not audit opinions. Clause 9.2 internal audit and Clause 9.3 management review still require qualified humans.
- Building a new standard. Every citation in every artifact maps to published text from ISO, NIST, or the EU AI Act. No novel framework.

## Success criteria for the positioning at the 12-month mark

- 500 GitHub stars on `aigovops` (OSS engine signal).
- 3 adapters in production use.
- 1 paid adapter customer.
- At least 1 GRC platform vendor referencing AIGovOps in their AI governance documentation (even if adversarially).

Last updated: 2026-04-18.
