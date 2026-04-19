# AIGovOS import analysis

**Purpose:** extract UX insights from the archived AIGovOS repo to inform Hub v2 build. No code porting, analysis only.

**Source:** https://github.com/ZOLAtheCodeX/AIGovOS (pushed 2026-03-04; analysis via `gh api` on 2026-04-18).

**Status:** AIGovOS is re-architected as MCP-first AIGovOps plugins + AIGovClaw runtime + Hub. The FastAPI + Postgres + Supabase Auth + multi-tenant backend is out of scope for OSS-local-only Hub v2.

## 1. Screen inventory

The frontend ships 50 page modules wired through `App.tsx` under a single authenticated `AppLayout`. Deduplicated by entity, the functional surface groups into 19 distinct workspaces.

| Screen | Purpose | Main surfaces | Primary actions | Backend |
|---|---|---|---|---|
| Dashboard (`/dashboard`) | KPIs + activity feed. | Risk severity (PieChart), control status (BarChart), risk tier, 8-item activity feed. | Refetch, toggle widget visibility. | `api.dashboard.*`. |
| Certification (`/certification`) | ISO 42001 clause-by-clause workflow. | Overall progress %, current clause, readiness score, per-clause guidance/artifacts/validation. | Initialize, select track (Fast/Standard/Guided), generate artifacts, validate, advance. | `/api/v1/aims/*`. |
| Tasks (`/tasks`) | Action queue. | Task list. | CRUD. | `api.tasks.*`. |
| Compliance (`/compliance`) | CASCADE engine output: applicable obligations. | Conditional cards keyed by governanceMode, modelType, domain, jurisdiction, biometric. | Toggle inputs to re-evaluate. | `cascade_service.py`. |
| Register System (`/register`) | Cascade intake wizard. | Multi-step form: project + entity + agentic config. | Capture and persist. | `cascade_service.py`. |
| Walkthrough (`/walkthrough`) | Guided cascade tour. | Step panels. | Navigate. | static. |
| Ask AI (`/ask`) | Conversational query against graph + RAG. | Chat, citations. | Submit, follow citations. | `graph_rag.py`, `ai_service.py`. |
| Knowledge Graph (`/knowledge-graph`) | Force-directed entity + regulatory graph. | `react-force-graph-2d/3d`, legend, filter chips. | Pan/zoom, filter, drill. | `graph_service.py`. |
| AI Systems (`/ai-systems`) | System inventory. | Table, risk tier, EU AI Act category, lifecycle, owner. | CRUD + link. | `ai_system.py`. |
| Documents (`/documents`) | RAG corpus. | List, chunk previews. | Upload, ingest, re-embed. | `ingestion_service.py`. |
| Vendors, Models | Vendor + model registries. | Tables, lineage. | CRUD. | `vendor_assessment.py`, `models.py`. |
| Risks (`/risks`) | Risk register. | Severity, treatment, linked controls. | CRUD + link. | `risk.py`, `risk_analyzer.py`. |
| Controls (`/controls`) | Control library with linkages. | Status (designed/implemented/operating/needs_improvement), linked risks/evidence. | CRUD + status + link. | `control.py`, `linking_service.py`. |
| Evidence (`/evidence`) | Evidence repo with control mappings. | Items, freshness, linked controls. | Upload, attach, evaluate. | `evidence.py`, `evidence_evaluator.py`. |
| Assessments (`/assessments`) | Assessment workflow. | List, stepper. | Run, advance, generate. | `assessment_workflow.py`. |
| Reports (`/reports`) | Report generator + viewer. | Templates, generated PDF/HTML. | Generate, view, export. | `reporting.py`. |
| Policies, Training, Audit, Incidents, Legal Defensibility, Bulk, Analysis, Graph | Standard CRUD or composite per domain. | Per-entity. | CRUD + linking. | per-domain. |

Auth surfaces (`/login`, `/signup`, `/forgot-password`, `/auth/callback`) are out of scope for Hub v2.

## 2. Component library inventory

`frontend/src/components/ui/` is a shadcn/ui-derived primitive set with governance-specific extensions. Top components worth porting in spirit (not code) to Hub v2:

1. `button.tsx` - shadcn button with `class-variance-authority` variants.
2. `button-loading.tsx` - inline spinner + disabled state during async; eliminates double-submit.
3. `card.tsx` - structured `Card / CardHeader / CardTitle / CardDescription / CardContent`.
4. `badge.tsx` - status pill with severity color tokens; used for risk tier and control status.
5. shadcn primitives wrapped from Radix: `tabs`, `dropdown-menu`, `select`, `checkbox`, `switch`, `progress`, `scroll-area`, `separator`, `sheet`, `collapsible`, `label`, `textarea`, `input`.
6. `form-input.tsx`, `form-select.tsx`, `form-textarea.tsx` - `react-hook-form` + zod-aware wrappers (label, control, error, helper).
7. `wizard-stepper.tsx` - multi-step form scaffold used by Cascade intake and Clause 4 wizard. Per-step validation, blocked forward nav.
8. `page-header.tsx` - canonical title + description + action slot used on every list page.
9. `page-loader.tsx` (`PageLoader` + `ErrorState`) - standard loading and error shells for query-driven pages.
10. `page-transition.tsx` - framer-motion fade-slide-in route transition.
11. `empty-state.tsx` - empty-list scaffold with icon + heading + description + CTA.
12. `skeleton-loader.tsx`, `skeleton-card.tsx` - shimmer skeletons matched to card layouts.
13. `auto-save-indicator.tsx` - inline pill ("Saving...", "Saved", "Error") for long forms.
14. `ai-suggestion-card.tsx` - dedicated card style for AI-generated proposals with explicit Accept / Reject. Worth porting verbatim because the UX recurs in every plugin.
15. `help-panel.tsx` - slide-out markdown help; lets each screen surface guidance without overloading the main column.
16. `rating-scale.tsx` - 1-5 control for likelihood/impact and maturity.
17. `checkbox-card.tsx` - large clickable card behaving as a checkbox; framework selection.
18. `error-boundary.tsx` - per-route boundary with retry CTA.
19. `dashboard/DashboardSettings.tsx` - widget visibility toggles persisted via `useDashboardConfig`. The model is "user picks what they care about", not "admin configures".
20. `layout/AppLayout.tsx` - the only layout: collapsible sidebar with grouped navigation, sticky topbar, persisted collapsed state.

Notable absent primitive: no data table (lists are bespoke per page; gap Hub v2 should fix with a single shadcn `DataTable`).

## 3. Navigation hierarchy

Single sidebar, five labeled groups, no breadcrumbs, no top-level tabs. Modals are sparing; most flows are full-page routes with wizards instead.

```text
Sidebar (collapsible, persisted)
├── (ungrouped)
│   ├── Dashboard
│   ├── Certification
│   └── Tasks
├── CASCADE
│   ├── Compliance
│   ├── Register System
│   └── Walkthroughs
├── DISCOVERY
│   ├── Ask AI
│   ├── Knowledge Graph
│   ├── AI Systems
│   ├── Documents
│   ├── Vendors
│   └── Model Inventory
├── ASSURANCE
│   ├── Risk Management
│   ├── Controls
│   ├── Evidence Center
│   ├── Assessments
│   └── Reporting
└── GOVERNANCE
    ├── Legal Defensibility
    ├── Policies
    ├── Training Registry
    └── Incidents

Topbar: mobile menu, spacer, user avatar + role badge, logout.
Settings appears at sidebar bottom only for admin role.
```

The four group labels (CASCADE, DISCOVERY, ASSURANCE, GOVERNANCE) are the most transferable IA decision in the entire repo. They correspond to practitioner mental model: figure out what applies, inventory what you have, prove it works, govern it over time.

## 4. Information architecture insights

1. **Sidebar groups by practitioner verb, not by framework.** Frameworks become entity attributes (Control has `eu_ai_act_category`, Risk has `nist_function`). Right choice for a multi-framework tool.
2. **"Register System" lives in CASCADE, not DISCOVERY.** Onboarding triggers regulatory analysis. The wizard captures posture and the cascade engine immediately shows applicable obligations, coupling discovery to applicability in one motion.
3. **Evidence is its own first-class workspace, not a tab on Controls.** Auditors ask "show me your evidence", not "show me your controls".
4. **AIMS Certification is a nested `CertificationLayout`, not a sidebar peer.** Inside `/certification` the practitioner gets a focused 3-step per-clause workflow (Guidance -> Artifacts -> Validation) without sidebar distractions. Strongest workflow in the app and the closest analogue to `certification-readiness`.
5. **Cross-framework links live in entity attributes plus the Knowledge Graph, not a dedicated "Crosswalk" page.** Postgres adjacency works without Neo4j, so visualization is not critical-path.
6. **`AskAI` is a peer to inventory, not a buried chat widget.** Query is expected as a primary modality.
7. **Dashboard is configurable per-user.** No "admin dashboard"; every practitioner curates their own.
8. **Forms are page routes, not modals.** `*FormPage` convention: URL carries intent, back button works, deep links work, autosave is feasible.

## 5. Backend-to-plugin mapping

The brief names five conceptual sub-agents. The actual repo exposes them through a mix of `backend/app/services/agents/` (operational) and `backend/aims/agents/clause_*.py` (certification). The actual code agents are: `prompt_analyzer`, `risk_analyzer`, `evidence_evaluator`, plus the seven clause agents.

| AIGovOS sub-agent | Closest code | AIGovOps plugin | Coverage |
|---|---|---|---|
| Regulatory Relevance Assessor | `cascade_service.py` + `cascade_schema.yaml` | `applicability-checker` + framework-monitor | **Fully replicated**. Framework-monitor extends with detection of new obligations. |
| Risk-to-Requirement Mapper | `linking_service.py` + `risk_analyzer.py` | `crosswalk-matrix-builder` | **Partially replicated**. AIGovOS enforced the link as a DB FK with bi-directional UI. Hub v2 needs the bi-directional view. |
| Gap Analyzer | `clause_*.py` + `evidence_evaluator.py` | `gap-assessment` | **Fully replicated**. AIGovOS additionally produced narrative gap text via LLM; AIGovOps defers narrative to the practitioner. |
| Cross-Framework Synthesizer | `graph_rag.py` + `graph_service.py` | `crosswalk-matrix-builder` (matrix query) | **Partially replicated**. AIGovOps gives matrix lookups; AIGovOS gave a force-directed visual. |
| Evidence Sufficiency Evaluator | `evidence_evaluator.py` | `certification-readiness` (shipped this session) | **Fully replicated**. AIGovOS scored per-evidence-item; AIGovOps aggregates to clause-level readiness. |

Net assessment: zero net-new agent capability is required for Hub v2. The matrix visualization (graph form of crosswalk data) is the only capability gap and it is a UI feature, not a plugin gap.

## 6. Database schema review

19 schema files. Maps cleanly to AIGovOps artifact types with three exceptions.

| AIGovOS entity | AIGovOps artifact / plugin |
|---|---|
| `organizations`, `users` | dropped (single-tenant local) |
| `ai_systems` | `ai-system-registry` artifact |
| `risks`, `risk_controls` | `risk-register` artifact |
| `controls`, `control_requirements`, `ai_system_controls` | `control-library` artifact + matrix rows |
| `evidence`, `control_evidence` | `evidence-store` artifact |
| `policies`, `policy_controls` | `policy-library` artifact |
| `assessments` | `assessment-record` artifact |
| `incidents` | `incident-register` artifact |
| `aims_*` (instances, clause_progress, artifacts, timeline_analysis, audit_log) | covered by `certification-readiness` plugin output |
| `audit_logs` | local journal (out of scope) |
| `cascade_evaluations`, `compliance_metrics` | `applicability-checker` snapshots |
| `documents`, `document_chunks` | `evidence-store` (RAG corpus is just evidence with embeddings) |
| `reports` | `report-generator` (future plugin) |
| `models`, `model_versions` | **No counterpart.** Candidate `model-registry` artifact. |
| `vendors` | **No counterpart.** Candidate `vendor-assessment` plugin. |
| `datasets`, `training_runs` | **No counterpart.** Required by EU AI Act Annex IV and ISO 42001 Clause 8.3. Candidate `training-lineage` artifact. |
| `financial_action_*` | **No counterpart.** Niche; defer. |
| `tasks` | local todo (out of scope) |

Three artifact gaps to consider for the next plugin batch: model registry, vendor assessment, training-data lineage. None are blockers for Hub v2.

## 7. Cascade schema

`cascade_schema.yaml` (1.0) plus `REGULATORY_CASCADE.md` together encode a rule engine. Inputs are project + entity configuration enums (governance mode, model type, autonomy tier, jurisdiction, domain, biometric, OSS license). Outputs are UI cards to show, UI tabs to surface, regulatory obligations that apply, and alerts. Rules are `if all { conditions } then { show_cards, show_tabs, alerts, obligations }`.

What it models well: conditional cascading from project posture to applicable obligations (agentic + payments triggers approval-checkpoint requirements; jurisdiction=EU triggers full AI Act; biometric=true triggers BIPA). It documents known UI/regulation deltas (Article 51 vs 53(2), Colorado AI Act effective date drift, NY RAISE Act not represented).

Relationship to `crosswalk-matrix-builder`: complementary, not redundant. Crosswalk answers "which controls satisfy which framework requirements"; cascade answers "which framework requirements apply to me in the first place". A complete Hub flow runs cascade first (applicability) then crosswalk (coverage). The schema format itself (YAML, declarative `if/then/else` rules) is portable and a candidate input format for `applicability-checker` if that plugin becomes rule-driven rather than checklist-driven.

## 8. Design language

Tailwind config layered on top of `frontend/src/styles/design-tokens.css`. Concrete facts:

**Primary color palette (extracted hex):**

- Primary (Deep Slate Blue): `#f0f4f8`, `#d9e2ec`, `#bcccdc`, `#9fb3c8`, `#829ab1`, `#627d98`, `#486581`, `#334e68`, `#243b53`, `#102a43`, `#0a1929` (50 through 950)
- Success (Teal Green): `#effcf6` ... `#27ab83` (500) ... `#014d40` (900)
- Warning (Warm Amber): `#fffbea` ... `#f0b429` (500) ... `#8d2b0b` (900)
- Danger (Refined Red): `#ffeeee` ... `#ba2525` (500) ... `#610404` (900)
- Info (Cool Blue): `#e6f6ff` ... `#0967d2` (500) ... `#002159` (900)
- Neutral (Warm Gray): `#ffffff` ... `#868e96` (500) ... `#0d0f12` (950)

**Typography stack:**

- Display: `Plus Jakarta Sans, SF Pro Display, -apple-system, sans-serif`
- Body: `Source Sans 3, SF Pro Text, -apple-system, sans-serif`
- Mono: `JetBrains Mono, SF Mono, Fira Code, Consolas, monospace`

Modular scale at 1.2 ratio: `--text-xs: 0.694rem` through `--text-4xl: 2.488rem`. Five weights (300-700).

**Component conventions:** 4px base spacing unit. Border radius `--radius: 0.5rem` default. Subtle layered shadows (`xs` to `2xl`) plus `--shadow-focus`. Restrained animations: 200ms `fade-in-up`, `scale-in`, `slide-in-right`; longer 1.5-2s `shimmer`, `pulse-soft`, `step-pulse` for skeletons. Dark mode is fully tokenized and class-gated (`.dark`).

**Comparison to Hub v1:**

- Hub v1: deep slate `#0f1419` background, burnt orange `#d97757` accent, JetBrains Mono + Crimson Pro.
- AIGovOS: deep slate-blue `#102a43`/`#0a1929` for darks, no orange accent (uses info blue and danger red as loudest colors), Plus Jakarta Sans + Source Sans 3 + JetBrains Mono.

Divergence: AIGovOS is tonally cooler and more enterprise (Linear/Notion-adjacent); Hub v1 is warmer and more editorial (Crimson Pro is a serif, burnt orange a strong accent). The mono font is the only point of agreement. For Hub v2, the AIGovOS warm-gray neutrals + slate-blue primary are a defensible "certification-grade" palette and pair well with Hub v1's burnt orange used sparingly as a single accent. JetBrains Mono is the obvious carryover.

## 9. Workflows / user journeys

Top five end-to-end:

1. **Onboard a new AI system.** Register System -> wizard captures project + entity + agentic config -> cascade runs -> Compliance dashboard shows triggered obligations. Plugins: `applicability-checker`, then write to `ai-system-registry`.
2. **Run an ISO 42001 certification cycle.** Certification -> Intake Wizard (Fast/Standard/Guided) -> Dashboard with progress + readiness -> open Clause 4 -> 3-step workspace -> generate scope + context analysis -> validate -> Complete Clause -> repeat for 5-10. Plugins: `gap-assessment` per clause, `certification-readiness` for score.
3. **Build risk-to-control coverage and prove it.** AI Systems -> select -> create Risk -> link Control -> attach Evidence -> sufficiency score -> low-coverage rows surface in Reporting. Plugins: `crosswalk-matrix-builder`, `certification-readiness`.
4. **Investigate cross-framework relationships.** Knowledge Graph -> filter regulatory nodes -> click EU AI Act Article 14 -> see linked NIST AI RMF GOVERN and ISO 42001 Clause 7.4 -> create a control mapped to all three. Plugin: `crosswalk-matrix-builder` matrix query as a graph.
5. **Respond to an incident.** Incidents -> log -> link to AI System -> reassess related Risks -> update Controls -> Audit. No plugin strictly required; candidate for a future `incident-response`.

## 10. Porting priority recommendation

Rank-ordered, top 10:

1. **Four-group sidebar IA (CASCADE, DISCOVERY, ASSURANCE, GOVERNANCE).** Single best decision in the repo. Practitioner-verb groups beat framework groups for multi-framework tools.
2. **3-step clause workflow (Guidance, Artifacts, Validation).** Maps directly onto `certification-readiness` output.
3. **Cascade intake wizard pattern.** Capturing project posture once and letting downstream views filter accordingly beats re-prompting on each page.
4. **`AISuggestionCard` Accept/Reject UX.** Universal template for surfacing plugin proposals.
5. **`page-header` + `page-loader` + `empty-state` triad.** Cheap to port, high consistency payoff.
6. **`wizard-stepper` component.** Reused by Cascade intake and Clause 4. Hub v2 needs it for `applicability-checker` and `gap-assessment` flows.
7. **Per-user dashboard widget toggling.** Solo-practitioner posture means the dashboard belongs to the operator.
8. **Evidence as a top-level workspace, not a tab on Controls.** Audit reality.
9. **Knowledge Graph view powered by crosswalk-matrix data.** The single capability gap between AIGovOps plugins and AIGovOS UX. `react-force-graph-2d` is the obvious dep.
10. **`design-tokens.css` pattern (HSL CSS variables + Tailwind extends).** Dark mode and theming come for free.

**Do not port:** FastAPI backend, Postgres schemas, Supabase Auth, multi-tenant tables (OSS-local-only); Neo4j; Vendors / Financial Actions / Training pages (no plugin); Walkthrough (HelpPanel suffices); Reports (no plugin); Bulk Operations (CSV button instead).

## Decision matrix: port / reference / drop

| AIGovOS element | Verdict | Rationale |
|---|---|---|
| Four-group sidebar IA | **Port** | Best IA decision; practitioner-verb grouping. |
| AppLayout (collapsible sidebar, persisted state) | **Port** | Right baseline. |
| 3-step clause workflow | **Port** | Maps to `certification-readiness`. |
| Cascade intake wizard | **Port** | Drives `applicability-checker`. |
| WizardStepper component | **Port** | Reused across flows. |
| AISuggestionCard | **Port** | Universal plugin-output UX. |
| PageHeader / PageLoader / ErrorState / EmptyState | **Port** | Consistency primitives. |
| Form input/select/textarea wrappers | **Port** | RHF + zod stack. |
| AutoSaveIndicator | **Port** | Practitioner trust during long forms. |
| HelpPanel slide-out | **Port** | Replaces Walkthrough route. |
| Per-user dashboard config | **Port** | Solo-practitioner fit. |
| Knowledge Graph (regulatory) | **Port** | Crosswalk visualization gap. |
| design-tokens.css HSL pattern | **Port** | Theming + dark mode. |
| Plus Jakarta Sans + Source Sans 3 | **Reference** | Pair against Hub v1 Crimson Pro decision. |
| Slate-blue primary palette | **Reference** | Compare to Hub v1 burnt orange accent. |
| AIMS clause agent architecture | **Reference** | AIGovOps plugin model already covers this. |
| `cascade_schema.yaml` rule format | **Reference** | Candidate input format for `applicability-checker`. |
| AskAI page | **Reference** | Hub v2 may surface this through Hermes Agent directly. |
| Knowledge Graph Neo4j backing | **Drop** | Postgres adjacency is enough. |
| Reports / ReportGenerator pages | **Drop (for now)** | No corresponding plugin yet. |
| Vendors page | **Drop (for now)** | No corresponding plugin yet. |
| Models page | **Drop (for now)** | Conflated with AI Systems for v2. |
| Training Registry page | **Drop (for now)** | No corresponding plugin yet. |
| Financial Actions Policy | **Drop** | Too niche for v2. |
| Bulk Operations page | **Drop** | CSV button on each list. |
| Walkthrough page | **Drop** | HelpPanel per screen. |
| FastAPI backend | **Drop** | OSS-local-only posture. |
| Supabase Auth + multi-tenant tables | **Drop** | Single-operator posture. |
| Audit Logs page | **Drop (for now)** | Local journal sufficient. |

## Recommendation for Hub v2 scope

Hub v2 should ship with:

- The four-group sidebar (CASCADE, DISCOVERY, ASSURANCE, GOVERNANCE) plus an ungrouped Dashboard / Tasks / Certification at the top.
- One screen per existing AIGovOps plugin output, plus four artifact-browser screens (AI Systems, Risks, Controls, Evidence).
- The Cascade intake wizard as the single onboarding flow that feeds `applicability-checker`.
- The 3-step clause workspace pattern reused for `certification-readiness` output.
- A regulatory Knowledge Graph view powered by `crosswalk-matrix-builder` data.
- The shadcn primitive set + AIGovOS extensions (PageHeader, PageLoader, EmptyState, WizardStepper, AISuggestionCard, AutoSaveIndicator, HelpPanel).
- Tokenized design system (HSL variables in CSS, Tailwind consuming them) carrying forward Hub v1's burnt orange as a single accent and adopting AIGovOS warm-gray neutrals + JetBrains Mono.
- Per-user dashboard widget toggling.

Defer: vendors, models, training, reports, financial actions, bulk operations, walkthrough, audit, multi-tenant or auth. None block the v2 certification pivot.
