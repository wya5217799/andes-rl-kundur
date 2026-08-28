# Editorial Decision Package

## Manuscript and Runtime Boundary

- **Title**: *Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning*
- **Mode**: `reviewer_full`
- **Contract**: `reviewer/reviewer_full/v2`
- **Manuscript SHA-256 (supplied)**: `A19922C9B3E330FEC5ABE682A9737A108B5ABA2782563898C7453589B2EE9277`
- **Criteria binding**: `criteria_binding_unavailable`
- **Calibration**: `NOT_CALIBRATED`

All five cards explicitly disclose `criteria_binding_unavailable`. This is therefore an explicitly unbound synthesis: it makes no formal venue-alignment claim. The scores and decision below are the mechanical result of the supplied runtime contract only. Confidence values remain uncalibrated, self-reported scope metadata and are not weights.

## Review Panel Provenance (#540/#740)

- **Typed artifact**: `panel_provenance.json`
- **Artifact SHA-256**: `B5EC3452AD349FE5421F6EAF05395F72AB5A4BBDBAB768317CBA74DC1332D0BC`
- **Panel ID**: `yang-md-rewrite-20260828-attempt-1`
- **Normalized manifest SHA-256**: `140b0ff8f4f6b3277c94151f13ec7dfa155ca4e457f3ffbe70728dbaf284f175`
- **Execution topology SHA-256**: `a1f8e1998cabc29c3dff3c103f2a38a00a0fb2a020fba5816012bf1ab240cb4d`
- **Fresh-context scope**: `within_panel_attempt_only`; this does not compare retries or prior rounds.

| Seat | Role ID | Actor type | Context ID | Peer outputs visible | Model family | Provider | Human reviewer ID |
|---|---|---|---|---|---|---|---|
| EIC | eic | model | `/root/ars_eic` | false | gpt-5 | openai | null |
| R1 | methodology | model | `/root/ars_methodology` | false | gpt-5 | openai | null |
| R2 | domain | model | `/root/ars_domain` | false | gpt-5 | openai | null |
| R3 | perspective | model | `/root/ars_perspective` | false | gpt-5 | openai | null |
| DA | da | model | `/root/ars_da` | false | gpt-5 | openai | null |

| Provenance axis | Status |
|---|---|
| Role-separated | true |
| Within-panel invocation-context separation | true |
| Blind to peer outputs | true |
| Model-family distinct | false |
| Provider distinct | false |
| Human-reviewer distinct | false |

- **Binary independence claim**: Not computed. Role separation is not independence.
- **Correlated-error disclosure**: All model-executed review seats used one model family; role separation does not remove correlated-error risk.
- **Provider disclosure**: All five seats used the OpenAI provider and the GPT-5 model family. The separate roles and contexts therefore do not remove same-family, same-provider correlated-error risk.

## Schema 13.2 Contract Audit

### Exact Card Scores

| Contract role | D1 | D2 | D3 | D4 | D5 | D6 |
|---|---|---|---|---|---|---|
| eic | not_assessed | not_assessed | not_assessed | not_assessed | warn | block (`repairable`) |
| methodology | warn | not_assessed | pass | not_assessed | not_assessed | not_assessed |
| domain | not_assessed | warn | not_assessed | not_assessed | not_assessed | not_assessed |
| perspective | not_assessed | not_assessed | not_assessed | warn | not_assessed | not_assessed |
| da | not_assessed | not_assessed | warn | not_assessed | not_assessed | not_assessed |

### Role-Scoped Eligible-Seat Matrix

| Dimension | Priority | Eligible assessed seats | Excluded values | Audit verdict |
|---|---|---|---|---|
| D1 methodology_rigor | mandatory | methodology=`warn` | all ineligible `not_assessed` values | warn |
| D2 domain_accuracy | mandatory | domain=`warn` | all ineligible `not_assessed` values | warn |
| D3 argumentative_coherence | mandatory | da=`warn`; methodology=`pass` | all ineligible `not_assessed` values | warn |
| D4 cross_disciplinary_relevance | high | perspective=`warn` | all ineligible `not_assessed` values | warn |
| D5 writing_and_structure | normal | eic=`warn` | all ineligible `not_assessed` values | warn |
| D6 venue_fit_and_contribution | mandatory | eic=`block` (`repairable`, not fatal) | all ineligible `not_assessed` values | block |

### Failure-Condition Evaluation

`F1` is false because no mandatory dimension has a fatal block; the only block, D6, is explicitly `repairable`. `F2` is true because the eligible EIC seat scores mandatory D6 `block`. For `F3`, majority is evaluated inside each dimension: D1, D2, and D6 each have one eligible owner seat at `warn` or worse and therefore satisfy majority, while D3 does not because its two eligible seats are `warn` and `pass` and both would be required. Three mandatory dimensions satisfy the atom, so the two-or-more dimension quantifier is true. `F4` is false because high-priority D4 is `warn`, not `block`. `F5` is true because at least one dimension is `warn` or worse. `F0` is false because not every dimension is `pass`.

```text
{condition_id: F1, fired: false}
{condition_id: F2, fired: true}
{condition_id: F3, fired: true}
{condition_id: F4, fired: false}
{condition_id: F5, fired: true}
{condition_id: F0, fired: false}
dimension_verdicts: [D1=warn, D2=warn, D3=warn, D4=warn, D5=warn, D6=block]
fired_conditions: [F2, F3, F5]
da_critical_adjudications: []
editorial_decision=major_revision
```

The selected condition is F2 because it has the highest severity among fired conditions. Its action is preserved without softening.

### DA Terminal Consistency

The DA card's `CRITICAL` table contains no IDs. Its sole numbered finding is `M1` under `MAJOR`, so no phantom `C1` is created. Accordingly, `da_critical_adjudications: []` is terminally consistent. The mechanical decision is not Accept, and there are no validated or unresolved DA CRITICAL IDs, so no `[DA-CRITICAL-VS-ACCEPT]` marker applies.

## Part 1: Editorial Decision Letter

Dear Authors,

Thank you for submitting *Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning*. Five role-separated seats reviewed the manuscript under the supplied contract. Their provenance is disclosed above; because every seat used the same GPT-5 family and OpenAI provider, the panel should not be described as independent.

### Decision: Major Revision

### Reviewer Summary

The cards did not provide free-form overall recommendation fields, so none is reconstructed.

| Reviewer | Role-scoped judgement | Confidence / scope disclosure | Main contribution to the decision |
|---|---|---|---|
| EIC | D5=`warn`; D6=`block` (`repairable`) | Per-finding 4–5; `NOT_CALIBRATED`; no formal venue binding | Contribution positioning and decisive-threshold significance are materially unsupported but repairable. |
| R1 | D1=`warn`; D3=`pass` | Per-finding 5; `NOT_CALIBRATED` | Estimand/inference alignment, threshold robustness, and replay provenance require repair; bounded argument remains coherent. |
| R2 | D2=`warn` | Per-finding 4–5; `NOT_CALIBRATED`; closest-work norm unverified | Physical and claim boundaries are accurate; nearest-work positioning and one term need correction. |
| R3 | D4=`warn` | Per-finding 4–5; `NOT_CALIBRATED` | Adjacent-field interpretation of the action limits and deployment ladder need support. |
| DA | D3=`warn` | M1 confidence 4; `NOT_CALIBRATED` | Comparator and threshold dependence is the strongest rival explanation; no CRITICAL finding was issued. |

### Consensus and Duplicate-Finding Adjudication

#### Points of Agreement

- **[CONSENSUS-3, SC-4]** EIC W4, R1 W2, and R3 W1 agree that the 110% action-RMS and total-variation limits lack sufficient scientific/practical rationale and exceedance-margin reporting. R2 is silent, not opposed. DA M1 independently corroborates the concern but is not counted in the four-seat consensus denominator.
- **[CONSENSUS-3, SC-5]** The same three non-DA seats agree that the paper does not show how the headline qualification reversal behaves under plausible threshold changes. R2 is silent. DA M1 adds the stronger comparator-choice challenge.

#### Duplicate Clusters and Dissent

| Sub-claim | Source positions | Disposition | Editorial resolution |
|---|---|---|---|
| SC-1: title does not foreground the evaluation-design identity | EIC W1 raised (Minor, confidence 5); R1/R2/R3 not mentioned | Single-reviewer finding | Retain as a suggested framing revision; silence is not consensus. |
| SC-2: `Delta_geo` is not explicitly defined | EIC W2 raised (Minor, confidence 5); R1/R2/R3 not mentioned | Single-reviewer finding | Retain separately from R1's broader estimand/inference concern; the two findings are related but not identical. |
| SC-3: closest-work comparison is insufficient | EIC W3 raised (Major, confidence 4); R2 W1 agrees the problem exists but rates it Minor (confidence 4, field norm unverified); R1/R3 not mentioned | **[SPLIT: severity]** | EIC's Major rating controls the D6 editorial gate because the manuscript identifies evaluation design, rather than a new algorithm, as its contribution. R2's lower D2 severity and unverified-norm boundary remain visible; they are not overwritten or treated as venue evidence. |
| SC-4: 110% action-limit rationale and margins are missing | EIC W4, R1 W2, and R3 W1 raised/corroborated (all Major); R2 not mentioned; DA M1 corroborates | **[CONSENSUS-3]** plus DA corroboration | Consolidate the shared core into one required revision while retaining every source anchor and remedy nuance. |
| SC-5: threshold/comparator robustness is not demonstrated | EIC W4, R1 W2, and R3 W1 raise threshold sensitivity; DA M1 additionally requires comparator sensitivity | **[CONSENSUS-3]**; DA remedy is stronger | Preserve the common threshold-sensitivity issue and explicitly preserve the DA's comparator-mismatch alternative; do not mislabel DA M1 as CRITICAL. |
| SC-6: the 103% frequency-quantity threshold lacks a stated rationale | EIC W4 raised (Major, confidence 4); R1/R2/R3 not mentioned | Single-reviewer finding | Carry it within the threshold-justification revision without promoting silence to agreement. |
| SC-7: Table II's mean-log effect and rank-based test/interval target are not aligned | R1 W1 raised (Major, confidence 5); EIC/R2/R3 not mentioned | Single-reviewer finding | Retain as an independent required methodology revision. |
| SC-8: paper-facing artifacts do not support independent replay | R1 W3 raised (Major, confidence 5); EIC/R2/R3 not mentioned | Single-reviewer finding | Retain as an independent required reproducibility revision. |
| SC-9: “open-loop” misdescribes the zero-action sensitivity bank | R2 W2 raised (Minor, confidence 5); EIC/R1/R3 not mentioned | Single-reviewer finding | Retain as a suggested terminology correction. |
| SC-10: deployment exclusions are not connected to likely failure modes | R3 W2 raised (Minor, confidence 4); EIC/R1/R2 not mentioned | Single-reviewer finding | Retain as a suggested limitations/evidence-ladder revision. |

No existence or direction conflict was found beyond the SC-3 severity split. Differences in how far the threshold remedy should extend are preserved: EIC/R1/R3 share rationale, margins, and threshold-sensitivity concerns, while DA M1 additionally foregrounds comparator choice and decision risk.

### Decision Rationale

The contract mechanically yields Major Revision. Mandatory D6 is `block` and explicitly repairable, firing F2; D1, D2, D3, D4, and D5 are warnings rather than fatal failures. This rules out Accept or Minor Revision under the supplied precedence while also ruling out Reject: no mandatory dimension carries a fatal block, and the EIC states that substantial repositioning or stronger substantiation could repair D6.

The principal decision drivers are two D6 issues. First, the paper presents evaluation design as its contribution but does not yet compare that design closely enough with the nearest VSG/MARL and safe-control work. EIC W3 rates this Major, whereas R2 W1 rates the same positioning problem Minor and marks the field norm unverified. The severity split is resolved for editorial purposes in favor of the D6 owner, while R2's narrower domain judgement remains on record and is not turned into a venue claim. Second, EIC W4, R1 W2, and R3 W1 independently identify the missing rationale, margins, and sensitivity for limits that determine the 0/208 complete-contract result; DA M1 adds comparator dependence as the strongest rival explanation.

R1 also identifies two independent Major methodology/reproducibility omissions: the mismatch between the reported mean-log effect and rank-based inference, and missing paper-facing replay provenance. The remaining title, notation, terminology, and deployment-ladder findings are bounded Minor items. The manuscript's disciplined separation of evidence banks, horizons, and claim limits supports revision rather than rejection. Because criteria binding is unavailable, this decision is contract-relative and not a formal venue-alignment judgement.

### Blocking Issues (immutable source order)

| Transport ref | Blocking issue | Source reviewer(s) | Evidence anchor | Resolving roadmap item |
|---|---|---|---|---|
| R1 | The evaluation-design originality case lacks a direct closest-work comparison. | EIC W3; R2 W1 (lower-severity corroboration) | absence: Introduction and Discussion — expected direct closest-work comparison; EIC checked §I paragraphs 2–7, §V paragraphs 1–3, and `references.bib`; R2 checked Sections I, III-B, and V | R1 |
| R2 | The empirical thresholds that drive the qualification reversal lack rationale, margins, and robustness evidence. | EIC W4; R1 W2; R3 W1; DA M1 | absence: §II-C, §IV-B, Fig. 3, and §V — expected threshold rationale, action-stress margins, and sensitivity | R2 |

## Part 2: Revision Roadmap

Rows follow the first source occurrence of each distinct finding. Later duplicates are consolidated into the earliest matching row; their severities, anchors, and remedy differences remain visible in the source field and the adjudication table. `R<n>` and `S<n>` are transport references, not work ranks.

### Required Revisions (Must Fix)

| Transport ref | Revision item | Sub-claim(s) | Transported severity | Evidence anchor | Confidence | Source | Obligation class | Cost scope | Bounded consequence |
|---|---|---|---|---|---|---|---|---|---|
| R1 | Add a direct nearest-work comparison that separates inherited controller/learner elements from the evaluation safeguards claimed as new. | SC-3 | Major (EIC W3); R2 W1's Minor severity dissent retained | absence: Introduction and Discussion — expected a direct closest-work comparison for the evaluation-design contribution | 4 — EIC field-adjacent editorial scope; 4 — R2 domain scope, original articles not independently reopened | EIC W3; R2 W1 | must_fix | section: Introduction/Discussion | D6 remains blocked if originality and significance are not substantiated |
| R2 | Explain the provenance and decision purpose of the 103%/110% limits; report action-RMS and total-variation ratios or margins; show qualification sensitivity over a declared threshold range; and answer the DA's comparator-choice challenge without converting empirical guards into safety claims. | SC-4, SC-5, SC-6 | Major (all driving findings) | absence: §II-C, §IV-B, Fig. 3, and §V — expected threshold rationale, exceedance margins/distributions, and threshold/comparator sensitivity | EIC 4; R1 5; R3 5; DA 4 | EIC W4; R1 W2; R3 W1; DA M1 | must_fix | re_analysis: complete-contract guard results and interpretation | D6 block and D1/D3/D4 warnings remain unresolved without a defensible threshold-significance argument |
| R3 | Name the target estimand for each source contrast and pair it with a compatible test and confidence interval, keeping raw and Holm-adjusted results distinct. | SC-7 | Major | absence: Table II and source-effects analysis — expected an explicit inferential target with compatible confidence interval for every contrast; checked Eq. (7), §III-B, Table II, §IV-C, and §V | 5 — direct audit of estimands, test route, and table fields | R1 W1 | must_fix | re_analysis: source-effect estimands and Table II | D1 remains warned while precision and decision boundaries are not assessable on a matching inferential scale |
| R4 | Add a reproducibility statement and archival pointer covering versioned code, environment, case/parameter artifacts, frozen checkpoints, manifests, and figure/table regeneration scripts, or state access restrictions and preservation plan. | SC-8 | Major | absence: methods and end matter — expected executable artifact provenance, software versions, and code/data/checkpoint availability sufficient for independent replay; checked Sections II–III, Results, Conclusion, and end matter | 5 — direct paper-facing provenance inspection | R1 W3 | must_fix | section: Methods/end matter and archival pointer | D1 remains warned while independent replay is unsupported by the paper-facing provenance |

### Required Item Details

**R1: Substantiate the evaluation-design contribution**
- **Problem**: The closest-work comparison does not show which controller/learner elements are inherited and which evaluation safeguards form the claimed contribution.
- **Source**: EIC W3; R2 W1, with lower transported severity and `[FIELD-NORM UNVERIFIED]` retained.
- **Requirement**: Compare the named nearest VSG/MARL and safe-control studies on plant, adaptive variables, information access, evaluation object, comparator, evidence-bank separation, guards, horizons, and claim scope, using verified original sources.
- **Acceptance criteria**: The manuscript contains a source-verified nearest-work comparison and one bounded sentence identifying the evaluation contribution without claiming algorithm novelty or formal venue alignment.

**R2: Establish the meaning and robustness of the empirical guard limits**
- **Problem**: The 103%/110% thresholds drive the qualification result, but their rationale, exceedance margins, and sensitivity are not reported; DA M1 also identifies comparator dependence.
- **Source**: EIC W4; R1 W2; R3 W1; DA M1.
- **Requirement**: State threshold provenance and decision risk, report action-ratio margins/distributions, add a declared threshold-sensitivity analysis, and directly address comparator sensitivity while retaining the empirical-not-safety boundary.
- **Acceptance criteria**: A reader can see why each limit was selected, how far each learned block lies from the action limits, whether the 0/208 result changes across the declared threshold analysis, and what remains comparator-specific.

**R3: Align source-effect estimates and inference**
- **Problem**: The geometric mean-log effect and Wilcoxon rank-shift route do not have an explicitly aligned estimand and interval.
- **Source**: R1 W1.
- **Requirement**: Define the estimand and use matching estimation, testing, and interval reporting for every contrast.
- **Acceptance criteria**: Each Table II contrast names one target estimand, reports a compatible estimate and confidence interval, and keeps raw and Holm-adjusted decisions distinct.

**R4: Supply paper-facing replay provenance**
- **Problem**: The paper does not identify the versioned executable artifacts needed to replay the corrected conversion, training cells, and guard audit.
- **Source**: R1 W3.
- **Requirement**: Add the versioned artifact and access information requested in R1 W3, including restrictions and preservation plan if access cannot be public.
- **Acceptance criteria**: The paper points to frozen code, environment, case/parameter, checkpoint, evaluation-manifest, and regeneration artifacts, or explicitly documents each unavailable element and its preservation/access status.

### Suggested Revisions (Should Fix)

| Transport ref | Revision item | Sub-claim(s) | Transported severity | Evidence anchor | Confidence | Source | Obligation class | Cost scope | Bounded consequence |
|---|---|---|---|---|---|---|---|---|---|
| S1 | Foreground the evaluation-design identity in the title or a clarifying subtitle. | SC-1 | Minor | text: Title and §I paragraph 2 — controller-design wording versus “The present contribution is instead an evaluation design” | 5 — publication-framing expertise | EIC W1 | should_fix | sentence: title/subtitle | D5 framing warning remains |
| S2 | Define `Delta_geo` algebraically and state its positive-direction convention at first use. | SC-2 | Minor | absence: Table II and §III-B — expected explicit definition and percentage transformation | 5 — source-level notation audit | EIC W2 | should_fix | sentence: Table II note or adjacent prose | D5 notation warning remains |
| S3 | Replace “open-loop sensitivity bank” with “zero-adaptive-action sensitivity bank” or an equivalent physically accurate term. | SC-9 | Minor | text: §I paragraph 4 — “A separate open-loop sensitivity bank…” | 5 — power-system control terminology expertise | R2 W2 | should_fix | sentence: terminology occurrences | D2 terminology warning remains |
| S4 | Connect delay, loss, quantization, EMT, and HIL exclusions to the observations and guard metrics each future evidence stage would test. | SC-10 | Minor | text: §V lines 0615–0621 — deployment exclusions and ideal synchronous communication | 4 — cyber-physical deployment expertise | R3 W2 | should_fix | section: limitations/future evidence ladder | D4 interpretation warning remains |

### Source-Traceability Checklist

- [ ] R1 — obligation `must_fix`: substantiate the evaluation-design contribution against nearest work.
- [ ] R2 — obligation `must_fix`: justify and stress-test the empirical guard limits and address comparator dependence.
- [ ] R3 — obligation `must_fix`: align source-effect estimands, tests, and intervals.
- [ ] R4 — obligation `must_fix`: add paper-facing replay provenance.
- [ ] S1 — obligation `should_fix`: clarify evaluation-design identity in the title surface.
- [ ] S2 — obligation `should_fix`: define `Delta_geo`.
- [ ] S3 — obligation `should_fix`: correct the “open-loop” terminology.
- [ ] S4 — obligation `should_fix`: add the deployment-oriented evidence ladder.

### Response Letter Instructions

Respond to every `R<n>` and `S<n>` item using `templates/revision_response_template.md`. Preserve the distinction between adopted changes, declined suggestions, and unresolved issues; do not treat the transport order as a work ranking.

## Closing

We encourage submission of a substantially revised manuscript. The revision should resolve the two D6 blockers and the required methodology/reproducibility items while preserving the manuscript's existing claim boundaries. The revised manuscript requires another round of review. This invitation is contract-relative and does not constitute a formal venue-alignment judgement because criteria binding is unavailable.
