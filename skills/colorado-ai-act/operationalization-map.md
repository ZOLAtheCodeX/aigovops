# Colorado SB 205 operationalization map

Cross-framework mapping from Colorado SB 205 (Senate Bill 24-205) requirements to AIGovOps artifact types and the plugins that produce them. Read [SKILL.md](SKILL.md) first for scope and definitions.

## SB 205 to AIGovOps artifact mapping

| SB 205 provision | Requirement | AIGovOps artifact | Plugin | Mode |
|---|---|---|---|---|
| Section 6-1-1701(3) | Consequential-decision domain scope | compliance-record | `colorado-ai-act-compliance` | default |
| Section 6-1-1701(9) | High-risk definition | compliance-record (is_high_risk field) | `colorado-ai-act-compliance` | default |
| Section 6-1-1702(1) | Developer duty of reasonable care | compliance-record obligation row | `colorado-ai-act-compliance` | default |
| Section 6-1-1702(2) | Developer documentation to deployers | documentation checklist | `colorado-ai-act-compliance` | default |
| Section 6-1-1702(2)(c) | Training-data governance documentation | data-register row | `data-register-builder` | future `framework: colorado-sb-205` |
| Section 6-1-1702(3) | Developer public statement | audit-log entry | `audit-log-generator` | future `framework: colorado-sb-205` |
| Section 6-1-1702(4) | Developer disclosure to AG and deployers | nonconformity record plus audit-log entry | `nonconformity-tracker`, `audit-log-generator` | future `framework: colorado-sb-205` |
| Section 6-1-1703(1) | Deployer duty of reasonable care | compliance-record obligation row | `colorado-ai-act-compliance` | default |
| Section 6-1-1703(2) | Deployer risk management policy and program | risk-register plus SoA | `risk-register-builder`, `soa-generator` | future `framework: colorado-sb-205` |
| Section 6-1-1703(3) | Deployer impact assessment | AISIA section | `aisia-runner` (Colorado addendum); `colorado-ai-act-compliance` (checklist) | future `framework: colorado-sb-205` |
| Section 6-1-1703(4)(a) | Consumer notice | audit-log entry | `audit-log-generator` | future `framework: colorado-sb-205` |
| Section 6-1-1703(4)(b) | Adverse-decision explanation | audit-log entry | `audit-log-generator` | future `framework: colorado-sb-205` |
| Section 6-1-1703(4)(c) | Consumer appeal for human review | audit-log entry | `audit-log-generator` | future `framework: colorado-sb-205` |
| Section 6-1-1703(5) | Deployer public statement | audit-log entry | `audit-log-generator` | future `framework: colorado-sb-205` |
| Section 6-1-1703(6) | Deployer disclosure to AG | nonconformity record | `nonconformity-tracker` | future `framework: colorado-sb-205` |
| Section 6-1-1706 | AG enforcement | N/A (regulator-facing) | none | N/A |
| Section 6-1-1706(4) | Affirmative defense: recognized AI risk management framework | gap-assessment plus SoA plus audit-log evidence bundle | `gap-assessment`, `soa-generator`, `audit-log-generator` | `framework: iso42001` or `framework: nist` |

## SB 205 to ISO/IEC 42001:2023 crosswalk

| SB 205 provision | ISO 42001 clause or control | Notes |
|---|---|---|
| Section 6-1-1702(1) developer reasonable care | Clause 5.1 leadership; Clause 6.1 risk assessment; Annex A Control A.4.2 | Reasonable care maps onto AIMS governance and risk-treatment duties. |
| Section 6-1-1702(2) developer documentation | Clause 7.5 documented information; Annex A Control A.4.6 documentation; Control A.7.2 system information | Developer-to-deployer package aligns with AIMS system documentation. |
| Section 6-1-1702(2)(c) data governance | Annex A Control A.7.3 data governance; Control A.7.4 data quality | Training-data governance is an AIMS core control. |
| Section 6-1-1702(3) public statement | Annex A Control A.3.2 public commitment | AIMS public commitment statement satisfies the narrower SB 205 scope. |
| Section 6-1-1703(1) deployer reasonable care | Clause 5.1; Clause 6.1; Clause 8.1 | Deployer reasonable care maps onto AIMS operating controls. |
| Section 6-1-1703(2) risk management policy and program | Clause 6.1 planning; Clause 8.2 AI system impact assessment; Clause 9 evaluation | AIMS risk-management cycle meets SB 205 annual-review cadence. |
| Section 6-1-1703(3) impact assessment | Clause 8.2 AI system impact assessment; Annex A Control A.5.3 | The AIMS AISIA schema, suitably augmented, meets SB 205 impact assessment content requirements. |
| Section 6-1-1703(4)(a) consumer notice | Annex A Control A.8.2 transparency to users | AIMS transparency control meets consumer-notice requirement. |
| Section 6-1-1703(4)(b) adverse-decision explanation | Annex A Control A.8.2; Clause 7.4 communication | Adverse-decision explanation is a transparency-plus-communication obligation. |
| Section 6-1-1703(4)(c) consumer appeal | Annex A Control A.6.2.8 human oversight; Annex A Control A.9.2 user complaints | Appeal-for-human-review maps onto AIMS human-oversight and complaints controls. |
| Section 6-1-1703(6) disclosure to AG | Clause 10.2 nonconformity and corrective action; Annex A Control A.10.4 incident response | AIMS nonconformity process handles the disclosure workflow. |
| Section 6-1-1706(4) affirmative defense | Entire AIMS | Substantive AIMS adherence is the designated-framework pathway. |

## SB 205 to NIST AI RMF 1.0 crosswalk

| SB 205 provision | NIST AI RMF subcategory | Notes |
|---|---|---|
| Section 6-1-1702(1) developer reasonable care | GOVERN 1.1, GOVERN 4.1, MAP 3.5, MANAGE 4.1 | GOVERN and MANAGE functions map onto developer duty. |
| Section 6-1-1702(2) developer documentation | MAP 4.1, MEASURE 1.3, MEASURE 2.1 | Documentation package matches AI RMF documentation expectations. |
| Section 6-1-1702(2)(c) data governance | MAP 2.3, MAP 4.1, MEASURE 2.11 | Training-data governance is an AI RMF data quality and bias concern. |
| Section 6-1-1702(3) public statement | GOVERN 4.1 public accountability, GOVERN 6.1 | Public statement maps onto accountability and disclosure. |
| Section 6-1-1703(1) deployer reasonable care | GOVERN 1.1, MAP 4.1, MANAGE 1.3 | Deployer reasonable care maps onto deployment-time governance. |
| Section 6-1-1703(2) risk management policy and program | GOVERN 1.1, MAP 2.1, MANAGE 1.3 | Policy and program align with AI RMF MANAGE function. |
| Section 6-1-1703(3) impact assessment | MAP 2.3, MAP 5.1, MAP 5.2, MEASURE 2.11 | Impact assessment content aligns with MAP subcategories. |
| Section 6-1-1703(4)(a) consumer notice | GOVERN 5.1, MEASURE 3.3 | Transparency to affected parties. |
| Section 6-1-1703(4)(b) adverse-decision explanation | MEASURE 2.8 explainability, MEASURE 2.9 interpretability | Explanation maps onto interpretability measurement. |
| Section 6-1-1703(4)(c) consumer appeal | GOVERN 5.2, MANAGE 4.1 | Appeal-for-human-review maps onto feedback and response. |
| Section 6-1-1703(6) disclosure to AG | MANAGE 4.1, MANAGE 4.2 incident response | Disclosure is an incident-handling subtype. |
| Section 6-1-1706(4) affirmative defense | Entire AI RMF | Substantive AI RMF adherence is the designated-framework pathway. |

## SB 205 to EU AI Act structural parallel

| SB 205 provision | EU AI Act parallel | Notes |
|---|---|---|
| Section 6-1-1701(9) high-risk definition | Article 6(2) plus Annex III | Colorado high-risk is narrower (consumer-protection framing; decision-influence test) than EU high-risk (eight Annex III categories plus product-safety route). |
| Section 6-1-1702 developer | Article 16 provider obligations | Colorado developer duty is a narrower, discrimination-focused subset of Article 16. |
| Section 6-1-1703(3) impact assessment | Article 27 Fundamental Rights Impact Assessment | Both require pre-deployment impact assessment; scope differs (algorithmic discrimination vs. fundamental rights). |
| Section 6-1-1703(4) consumer notice and appeal | Article 26(11) consumer information; Article 86 right to explanation | Colorado consumer rights are narrower and anchored in the Colorado Consumer Protection Act. |
| Section 6-1-1706 AG enforcement | Articles 99-101 penalties | Colorado has no fine tier comparable to EU penalties; remedies are state consumer-protection remedies. |
| Section 6-1-1706(4) affirmative defense | Article 40 harmonised standards presumption of conformity | Functionally similar: substantive adherence to a designated framework shifts the enforcement posture. |

## Leverage points for dual-regime organizations

Organizations already operating under ISO 42001 or NIST AI RMF have significant leverage on Colorado compliance:

1. **Risk management.** ISO Clause 6.1 and AI RMF MAP-MEASURE-MANAGE produce the policy and program required by section 6-1-1703(2).
2. **Impact assessment.** ISO Clause 8.2 (AISIA) with a Colorado addendum covering section 6-1-1703(3) content items satisfies the impact-assessment duty.
3. **Documentation.** ISO Clause 7.5 and AI RMF MAP 4.1 documentation conventions cover the developer documentation duty in section 6-1-1702(2).
4. **Nonconformity and incident reporting.** ISO Clause 10.2 and AI RMF MANAGE 4.2 workflows handle the disclosure duties in section 6-1-1702(4) and 6-1-1703(6).

The affirmative defense in section 6-1-1706(4) recognizes this leverage explicitly. Substantive adherence evidence should be compiled through the `gap-assessment`, `soa-generator`, and `audit-log-generator` plugins in the framework corresponding to the organization's AIMS or AI RMF profile.
