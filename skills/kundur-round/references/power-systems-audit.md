# Power-System Audit Module

Internal reference of `kundur-round`; it is loaded only by the publication or
manuscript route, never through skill discovery.

Perform a forensic domain review. Establish whether the model, experiment, and
claim mean the same thing before evaluating prose quality.

Apply [the project research adapter](research-skill-adapter.md)
before reviewing; it supplies the repository's evidence hierarchy and mandatory
power-system checks.

## Establish the review frame

1. Identify the manuscript or pre-draft claim sheet, supplement if any, target
   venue and paper type if known, and available model, code, data, and
   experiment records.
2. Read repository instructions and the project's declared evidence authority.
   Treat sealed results, formal verdicts, and canonical ledgers as authoritative
   over draft prose and skill output.
3. Extract the headline claims from the title, abstract, contribution list,
   results, figures, and conclusion.
4. State access limits before judging an item that requires unavailable
   equations, artifacts, or source data.
5. Keep plant-specific vocabulary, evidence paths, and project state in the
   project adapter rather than duplicating them here.

Complete this stage only when every proposed headline claim has an explicit
review target and the evidence hierarchy is recorded. Mark presentation checks
as not yet applicable during a pre-draft feed review.

## Audit the physical and mathematical model

Apply every relevant check in
[technical-audit.md](technical-audit.md). Trace definitions
through equations, implementation descriptions, tables, and captions. Recompute
short derivations when this can confirm a suspected error.

Complete this stage only when the system boundary, operating point, units,
signs, controller timing, actuator path, limits, and claimed stability or
frequency quantities are either verified or reported as findings.

## Audit the experiment and inference

Apply every relevant check in
[experimental-and-statistical-audit.md](experimental-and-statistical-audit.md).
Match each contribution to a test, estimand, comparison, uncertainty statement,
and validity condition. Preserve negative runs, invalid rounds, exclusions,
missing cases, and boundary conditions in the assessment.

Complete this stage only when every contribution has a verdict of supported,
qualified, unsupported, or uncheckable and every reported comparison has a
defined unit of analysis.

## Audit claim boundaries

Apply [claim-boundaries.md](claim-boundaries.md) to the
title, abstract, introduction, contribution bullets, figure captions, and
conclusion. Check cross-section consistency after reviewing the evidence-bearing
sections.

Complete this stage only when every headline claim has one evidence-matched
wording recommendation and prohibited scope expansions are identified.

## Report findings

Use these severities:

- `BLOCKER`: a false or unsupported headline result, invalid evidence used as
  support, material model or equation error, broken comparison, or missing
  information that prevents scientific evaluation.
- `MAJOR`: a result may remain usable after substantial qualification,
  reanalysis, or restructuring.
- `MINOR`: a local ambiguity, notation defect, or reporting omission with a
  bounded fix.

List concrete findings before general commentary. For each finding provide:

```text
ID | Severity | Manuscript location | Claim or object
Problem | Evidence inspected | Scientific consequence | Required repair
```

Then provide:

1. claim-boundary table;
2. unresolved access or verification limits;
3. domain verdict: `BLOCK`, `MAJOR REVISION`, `MINOR REVISION`, or
   `DOMAIN PASS`;
4. the smallest ordered repair plan.

Return `DOMAIN PASS` only when every headline claim, load-bearing equation,
primary endpoint, baseline comparison, and scope statement has been accounted
for. A domain pass is not a language, citation, or journal-compliance pass.
