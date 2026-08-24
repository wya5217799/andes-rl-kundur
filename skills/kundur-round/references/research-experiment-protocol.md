# Research and Experiment Gates

Use these gates for scientific decisions from direction selection through claim
formation. They are decision gates, not mandatory stages: enter the gate that
owns the current question and stop when it returns.

## Set proportional load

- **Exploratory:** reversible advice, offline work, or a tunable pilot with no
  formal evidence or claim consequence. Use one compact pre-check and one
  compact post-check.
- **Formal:** a frozen comparison, physical or simulator execution, training,
  protected evidence, or a claim-bearing result. Keep the five gates distinct
  and follow the project's prospective authorization and provenance rules.
- **Publication:** an accepted result is being turned into an argument,
  manuscript, venue decision, or package. Enter the paper-writing protocol.

If the active project defines its own loads, use its names and thresholds. A
global route never creates a project round or evidence status.

## Gate 1: Direction

Decide whether the question or candidate direction merits future work.

- Use `research` for one bounded primary-source question or official fact.
- Use `deep-research` for a literature landscape, nearest-work map, competing
  method families, or survey-grade synthesis.
- Use `idea-evaluator` as an adversarial adviser on one candidate direction.
  Its score is not a formal project verdict.
- Use a bounded Academic Research Suite Socratic or research-architecture mode
  only when question refinement or methodology design is the deliverable.

During an active experiment, external research is still eligible when it
answers a prospective decision or an identified external-context gap. Return
it as advice, a candidate mechanism, or a successor-study constraint. It does
not modify a frozen plan or become experimental evidence.

**Return:** one answerable question or candidate decision, its evidence basis,
and the next prospective test or stop.

## Gate 2: Design

Decide whether the proposed study can identify the intended conclusion.

Settle the hypothesis, study object, information and action conditions,
comparators, endpoints, unit of analysis, uncertainty, exclusions, and
kill-or-pivot rule. Before freezing a comparison, apply
[comparison-identifiability-gate.md](comparison-identifiability-gate.md).

A project-native planner owns the executable contract. Academic Research Suite
`experiment-agent plan`, paper templates, or figure planning may expose missing
variables, confounds, evidence needs, or data fields, but the project must adopt
their useful parts prospectively.

For a formal or high-consequence study, or when the user requests a loophole
search, run the Design red-team in
[review-bundles.md](review-bundles.md) before freeze. Keep exploratory pilots on
the compact path unless their consequence changes.

**Return:** a prospective study contract whose planned observations can
distinguish pass, qualify, fail, and invalid.

## Gate 3: Readiness

Decide whether the authorized design is ready to launch, resize, or monitor.

Use project-native preflight and execution tools. Load
[execution-readiness.md](execution-readiness.md) for a non-quick launch, worker or resource-budget
freeze, resize, long-run monitor, utilization diagnosis, ETA, observation
cadence, or artifact-cost decision. Its `RUN-READY`, `MEASURE-FIRST`, or `HOLD`
card is a supporting return to the authorized runner; this navigator does not
repeat its capacity policy.

A frozen active attempt remains monitor-only. A missing or non-permitting
required readiness return stops launch or resize.

**Return:** an authorized execution contract plus every required preflight and
readiness result.

## Gate 4: Result

Decide whether completed outputs are valid, reproducible, and interpretable.

Start from final project-native machine-readable results and validity records.
Bind findings to authoritative artifacts, run the project-declared domain
audit, and preserve invalid or incomplete outcomes as such. Add Academic
Research Suite `experiment-agent validate` only when a distinct statistical
interpretation or reproducibility report can change the gate decision.

Classify each evidence input as `planned`, `observed-unverified`, or `verified`.
If provenance is missing or inputs conflict, isolate the affected finding and
return a blocker; do not promote it into a claim in the same pass.

These are scientific integrity checks even when no manuscript exists. Generic
review, progress logs, scorecards, or successful execution do not replace the
project's validity decision.

For a claim-bearing or disputed result, use the Result challenge in
[review-bundles.md](review-bundles.md) to combine distinct evidence, domain,
statistical, reproducibility, and alternative-explanation returns.

**Return:** validity status, material findings, uncertainty, anomalies, and
unresolved blockers, each tied to its authority.

## Gate 5: Claim

Decide the strongest conclusion the accepted evidence permits.

Use the executed estimand, comparison-identifiability result, evidence audit,
and domain audit. Add bounded external research for unresolved context and a
bounded adversarial review for alternative explanations. Use
`idea-evaluator` only for a successor direction, not to re-grade the completed
study.

Return:

```text
Allowed claim:
Required qualification:
Stay-out claims:
Evidence locator:
Unresolved external context:
Next eligible route:
```

Passing this gate opens evidence-bound argument or manuscript work. It does not
require that writing begin immediately.

## Cross-stage writing support

- Before execution, use an argument skeleton or figure plan to reveal missing
  evidence, not to pre-announce results.
- During a frozen run, draft only stable Methods or system descriptions from
  the frozen contract. Define figure structure from predeclared metrics without
  outcome-driven selection.
- After formal analysis, evidence and domain audits may run on a result feed or
  claim sheet before any manuscript exists.
- Draft Results, headline contributions, Abstract, and title only after the
  Result and Claim gates return accepted inputs.

## Engineering boundary

When implementation blocks a scientific gate, record:

```text
Scientific acceptance criterion:
Implementation dependency:
Authorized write scope:
Engineering deliverable:
Verification:
Return gate:
```

Use a directly applicable engineering capability only when implementation is
authorized. Return its verified artifact to the scientific owner; code success
does not authorize execution or settle the scientific question.

## Completion

Finish when the current gate has one owner, one checked return, one decision,
and one next eligible route. Gate completion does not authorize that route;
do not advance merely because a later skill is available.
