---
round: R357
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R357 plan - exact physical joint-target feasibility

**Opened**: 2026-08-07
**Driver**: Determine whether any of R356's ten relaxed-optimal exposed cases
retain the unchanged two-percent joint target under the future policy's exact
three-edge power, ramp, and energy limits.
**Parent**: Q-0095; CLM-0930; R356; R352 development pairs; R341 point models

## TL;DR

Freeze one independently certified physical-feasibility analysis over the same
sixteen exposed development cases. Add the unchanged three-edge node-power and
node-ramp limits to the R356 cone problem. Omit state-of-charge rows only after
proving their worst possible twenty-five-step change is smaller than the
available bound margin for each case, and reconstruct the exact efficiency
path afterward. Read no holdout, run no simulator or training, and do not
change the two-percent target.

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0095 [opened R357] Do any exposed R356 candidates retain the unchanged joint target under the exact three-edge physical limits?

## Recently Closed (last 3)

- Q-0094 closed-negative @ R356, by CLM-0930 - Does the matched neighbour-local deterministic baseline leave material, neighbour-observable, and physically feasible residual headroom?
- Q-0093 closed-positive @ R352, by CLM-0925 - Does a tuned endpoint-local three-edge deterministic controller retain differential-synchronization value on an untouched disturbance-shape bank?
- Q-0092 closed-positive @ R351, by CLM-0920 - Can one deterministic three-edge controller execute from endpoint-only neighbour information through the future policy's exact physical governor?

## Methodology

**Lane**: evidence. R357 opens and may close Q-0095, creates a formal
claim-bearing classification, and changes no protected parent artifact.

### Frozen study object

- exactly the sixteen already exposed R356 development cases, including the
  six accepted relaxed-infeasible cases as negative controls and the ten
  accepted relaxed-optimal candidates;
- the R341 linear response maps and R352 selected-local base commands used by
  R356;
- twenty-five samples, three independent edge coordinates, and an unchanged
  minimum improvement fraction of `0.02` for both endpoints;
- `FeedbackLimits()` with the unchanged node power, node ramp, sample period,
  energy capacity, efficiencies, and state-of-charge interval.

No R356 result status is used as a positive label. Case identity fields are
reported for audit only and never become a deployed feature.

### Frozen R356 parent

- plan: `12fb0ef7467e3b37939461c4faaccb0bb9311f5b41cabf8c3bb9043a8f1d2799`;
- rehearsal: `d015b51e9de6601a05730d36e31f8092d4998368cd1fc0c6d5dd14389f8cc57f`;
- seal: `2fa030a04633fc944128914d55be1f96da61ca115e00f852909be401e7e1a184`;
- attempt: `9dd3126615d52816f301cf6bb8f64eb4603324eb0f84dec2862e925669fe40eb`;
- analysis: `9a4334c4575cd803114e52c4ed2279efe6defa979734b08e3bc28de0e37332b1`;
- manifest: `4cf10f40c52f56861fa122ede3ff91138ed73cec2c555d0885d0b20d3072e71d`;
- verdict: `bb2cc97a79d5efd709552349979930f8741d239255f82aa19c8dc9545226f50d`;
- feed: `d09e38e70ce46d44e20e3215ac07c0db3c6a9e9fd440a48ce18d04e6371ae0f4`;
- claim: `4e27df5b7feb7f2c365a5196cb9f459a4b4b7b69e06869533bc3c703399e2053`;
- closed question: `749923cbc1f4c3b501b453e0fffa1018c1f00631d5e433eb4bc4ec78eb493ab8`.

### Exact physical cone object

Use edge actions scaled by node ramp. Represent the common-coordinate absolute
error by nonnegative epigraph variables and the differential-coordinate
squared-error bound by one second-order cone. Add two-sided linear inequalities
for every node-power and initial/subsequent node-ramp limit after mapping the
three edge coordinates through the frozen incidence matrix.

For each case, derive a worst-path state-of-charge change from horizon, sample
period, system base, node-power bound, energy capacity, and the less favourable
efficiency direction. State-of-charge rows may be absent from the cone only
when this bound is strictly smaller than the minimum initial margin to either
limit. Regardless of redundancy, reconstruct the returned witness with the
exact piecewise charge/discharge update and include its maximum violation in
the acceptance decision.

CVXOPT 1.3.3 runs serially with absolute, relative, and feasibility tolerances
`1e-10`, maximum iterations `100`, and an acceptance tolerance of `1e-8`.
An optimal status is accepted only when all solver, endpoint, physical, cone,
and direct reconstruction diagnostics are finite and within tolerance. A
primal-infeasible status is accepted only when its certificate residual is
finite and within tolerance. All other exits fail closed.

### Authorized implementation

- Add one reusable public feasibility seam under `probes/`, one stable
  create-only execution adapter under `scripts/`, and focused public-interface
  tests under `tests/`.
- The public seam accepts one complete case and returns status, acceptance, a
  feasible witness when present, the energy-bound proof, and independent
  endpoint and physical diagnostics.
- Tests use worked one-step feasible and infeasible examples, a physical-limit
  counterexample, an energy-bound rejection, and bank classification. Each
  red-green slice runs only its focused test.
- Before seal, run focused R357 tests, R356 regression tests, preflight, and
  the formal adapter's same-path rehearsal.

## Outcomes

- `PHYSICAL-HEADROOM-FOUND`: all sixteen exits are accepted and at least one is
  optimal under the complete physical contract. This supports only a bounded
  exposed linear-response physical-opportunity statement and permits a
  separately registered neighbour-observability question.
- `NO-PHYSICAL-HEADROOM`: all sixteen exits are accepted primal-infeasible.
  Stop the unchanged two-percent selective-residual route.
- `ANALYSIS-INVALID`: any case is missing, any exit is unaccepted, any source,
  parent, identity, package, or seal check drifts, or any independent
  reconstruction fails. Preserve outputs and do not retry.

No branch authorizes holdout reading, physical execution, ANDES, neural
training, distributed runtime, EVAL, target reduction, stability, safety,
topology, deployment, or paper-title validation.

## Formal launch contract

- `formal_entry`: `python scripts/run_r357_physical_joint_endpoint_feasibility.py analyse --expected-seal-sha256 <sha256>`.
- `rehearsal_command`: `python scripts/run_r357_physical_joint_endpoint_feasibility.py rehearsal`.
- `rehearsal_scope`: execute the formal pre-attempt verification path over all
  frozen parent inputs, package closure, installed solver, sixteen exact case
  identities, energy-bound checks, analytic smoke cases, and output absence
  without creating a formal attempt or result.
- `rehearsal_checks`: sixteen development cases; six R356 negative controls;
  ten relaxed-optimal candidates; zero holdout reads; accepted synthetic
  feasible, physical-infeasible, and endpoint-infeasible statuses; source and
  parent equality; result and attempt absent; ANDES and training absent.
- `worker_processes`: 1; `native_threads_per_process`: 1;
  `wsl_python_processes`: 0; all are hard caps.
- `capacity_evidence`: R356 solved the relaxed sixteen-case bank serially in
  less than one minute; R357 adds only linear physical rows and remains a
  one-process offline cone analysis expected to finish within one minute.
- `host_process_budget`: one Windows Python process;
  `other_reserved_processes_at_plan`: zero. Any live conflicting process or
  missing dependency returns `HOLD` before seal.
- completion is one create-only `analysis.json` plus `manifest.json` and
  sidecars, or one create-only `failure.json` plus sidecar; retry is forbidden.

## Asset protection contract

R341/R352/R353/R354/R355/R356 plans, questions, claims, sources, seals,
attempts, results, feeds, verdicts, thresholds, models, traces, and manifests
remain byte-unchanged. Add only Q-0095, R357 plan, probe, execution adapter,
focused tests, rehearsal, seal, formal results, and required closeout
artifacts. Do not edit another manuscript line or push publicly.

## Cross-references

- Q-0095
- CLM-0930
- R356 independent relaxed feasibility result
- R352 matched neighbour-local deterministic parent
- R341 point models
