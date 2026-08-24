# Evidence Audit Module

Internal reference of `kundur-round`; it is loaded only by the publication or
manuscript route, never through skill discovery.

Treat the audit as a stage-neutral derivative verification view. Keep the
project's declared ledger, sealed artifacts, and formal verdicts as the source
of truth whether or not manuscript prose exists yet.

Apply [the project research adapter](research-skill-adapter.md)
before auditing; it owns evidence precedence and manuscript scope.

## Declare authority and scope

1. Identify the manuscript, experiment feed, or claim-sheet files and the
   statements included in the audit.
2. Record the project's evidence authority and precedence order.
3. Read repository instructions, the active manuscript-line decision record,
   and any formal validity or exclusion rules.
4. Define material claims as numerical, comparative, causal, mechanistic,
   robustness, safety, generalization, novelty, or deployment statements.
5. Keep project vocabulary, paths, and state in the project adapter rather
   than duplicating them here.

Complete this stage only when the audit can distinguish canonical evidence from
notes, intermediate runs, manuscript prose, and prior review output.

## Build a deterministic inventory

Run the bundled inventory script before semantic review:

```powershell
python memory\tools\inventory_manuscript.py `
  paper\main.tex `
  --project-root . `
  --authority-file paper\manuscript-line\LINE.md `
  --format markdown
```

The script inventories line locations, numeric tokens, CLM and round references,
and high-risk claim language. It verifies referenced CLM and round paths when the
project exposes the expected ledger, and can compare manuscript claim IDs with
an active line or other authority file. It does not decide whether a matching
number proves a sentence.

Complete this stage only when every source file in scope was scanned and
the inventory reports no unreadable inputs.

## Bind every material claim

Split compound sentences so one row carries one scientific assertion. For every
claim, record:

- exact manuscript location and wording;
- claim type and population or operating envelope;
- canonical evidence path and precise locator;
- transformation from source value to manuscript value;
- formal status, validity, exclusions, and supersession;
- support status and evidence-matched replacement wording.

Use the schema in
[audit-schema.md](audit-schema.md). Bind evidence to a
path plus a stable locator such as JSON Pointer, table row and column, figure
source field, claim ID, or verdict section.

Complete this stage only when every material inventory item is bound or marked
`UNCHECKABLE` with the missing artifact named.

## Verify the bindings

1. Recompute derived percentages, differences, ratios, intervals, counts, and
   aggregations from the canonical source when feasible.
2. Check scenario, seed, controller, topology, disturbance, metric, time window,
   unit, sign, and comparison direction.
3. Inspect the final verdict and guard result before accepting a directional
   estimate.
4. Trace figures and tables to their generating data or deterministic script.
5. Check title, abstract, contributions, captions, discussion, and conclusion
   for stronger restatements of the verified Results claim.

Use these statuses:

- `VERIFIED`: wording, value, conditions, and validity match canonical evidence.
- `QUALIFIED`: evidence supports a narrower statement.
- `UNSUPPORTED`: the available evidence cannot support the assertion.
- `CONFLICTED`: authoritative artifacts disagree or the cited result is invalid
  or superseded.
- `UNCHECKABLE`: a named required artifact or locator is unavailable.

Complete this stage only when each material claim has one status and every
numeric claim has an independently checked source transformation.

## Report the audit

Lead with `BLOCKER` findings, then `MAJOR`, then `MINOR`. For each finding give
the manuscript location, exact evidence locator, discrepancy, consequence, and
smallest safe repair.

Return:

1. audit coverage and authority declaration;
2. complete claim-evidence table;
3. cross-section drift findings;
4. unresolved artifacts;
5. decision: `FAIL`, `CONDITIONAL PASS`, or `PASS`.

Return `PASS` only when every material claim is `VERIFIED`, or a transparent
limitation is intentionally `QUALIFIED`, and no canonical conflict remains.
Preserve the table as a review artifact, not a replacement project ledger.
