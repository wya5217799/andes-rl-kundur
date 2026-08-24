# Evidence-audit schema

Use one row per atomic claim.

| Field | Required content |
|---|---|
| `claim_id` | Stable audit-local ID such as `E-001` |
| `location` | File, section, line or LaTeX anchor |
| `verbatim_claim` | Exact manuscript wording |
| `claim_type` | numeric, comparative, causal, mechanism, robustness, safety, generalization, novelty, deployment |
| `scope` | Plant, topology, operating points, disturbances, seeds, controller family, time window |
| `canonical_source` | Project-relative path |
| `locator` | JSON Pointer, row/column, claim ID, verdict section, or figure field |
| `source_status` | current, superseded, invalid, exploratory, or other project status |
| `transformation` | Identity or explicit formula from source to manuscript |
| `verification` | Recomputed value or qualitative support check |
| `audit_status` | VERIFIED, QUALIFIED, UNSUPPORTED, CONFLICTED, UNCHECKABLE |
| `safe_wording` | Evidence-matched replacement sentence |
| `severity` | BLOCKER, MAJOR, MINOR |

## Atomicity test

Split a sentence when its clauses require different:

- evidence sources;
- validity states;
- operating envelopes;
- comparison arms;
- inference levels.

A claim with one supported clause and one unsupported clause is not `VERIFIED`.

## Numeric transformation record

Write transformations in a reproducible form, for example:

```text
100 * (treatment - baseline) / baseline
paired median over scenario_id, then percentile bootstrap over scenarios
mean across three independently trained seeds after per-seed scenario mean
```

Record units before and after the transformation. State the sign convention for
metrics where lower is better.

## Evidence sufficiency

Evidence must establish all of:

1. identity of the evaluated condition;
2. validity of the source run;
3. value or qualitative pattern;
4. uncertainty or boundary needed by the wording;
5. population over which the claim is made.

A file containing the same number is a candidate locator, not sufficient
support by itself.
