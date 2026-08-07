---
round: R347
state: aborted
manuscript_line: decoupling-marl-model-first
opened: '2026-08-06'
closed: '2026-08-06'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'sealed analysis invalid: relative slack repaired the feasibility stage,
  but one minimum-norm solve diverged and failed the frozen validity gate; retry forbidden'
superseded_note: null
---
# R347 plan - scale-stable residual-headroom analysis

**Opened**: 2026-08-06
**Driver**: Answer Q-0091 under the unchanged R345 scientific contract after
one metadata-only diagnostic localized its invalidity to absolute slack
scaling.
**Parent**: CLM-0910; Q-0091; aborted R345/R346

## TL;DR

Repeat the complete create-only R345 offline analysis once under a fresh seal.
Change only the feasibility relaxation coordinates from absolute endpoint
units to dimensionless relative shortfalls. Preserve every input, physical
limit, 2% target, local-information boundary, estimator, statistic, subgroup,
decision rule, and no-training boundary. A positive result can authorize only
one separately sealed non-learning physical residual intervention.

## Snapshot at plan-time (oracle as of 2026-08-06)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0091 [opened R344] Does the frozen deterministic bridge leave material, observable, and physically usable residual headroom before neural training?

## Recently Closed (last 3)

- Q-0090 closed-positive @ R344, by CLM-0910 — Can the fresh-qualified predictor support a deterministic physical bridge before any distributed or learning experiment?
- Q-0089 closed-positive @ R341, by CLM-0900 — Does the selected predictor preserve its registered waveform envelope on an untouched operating-point bank?
- Q-0087 closed-partial @ R339, by CLM-0890 — Which location-dependent input dynamics explain the upstream-load mismatch before any bridge repair?

## Methodology

**Lane**: evidence. R347 reads the protected R344 outcome records and may
dispose Q-0091, so the complete prospective seal, attempt, result, audit, and
publication lifecycle applies.

**Frozen parent chain**:

- R345 scientific contract payload SHA-256
  `6492c9a8b087eabcd41222b3bb246c167936e1e82f8de33b5de3a6daf41fd1ab`;
- R345 seal SHA-256
  `47f1b287316f1475725a2c844f470016058ec06f5759d1d743829c74afbc04f4`;
- R345 failure SHA-256
  `8a519fb736151ea793f18cff2b0d08de65d810dd8f49425104cd9f68de08c9a3`;
- R346 diagnostic seal SHA-256
  `d5863b23b8c827fdd56782e09ca76a69af7046c1b5b2e4a7b123a4dc1fc5cb5a`;
- R346 diagnostic SHA-256
  `8d3e9482b55167622b81f0e574b29a968d427fa944afe65ddc7383f51c1b3d41`;
- R346 manifest SHA-256
  `1964cfcfed8a78a413067e726102ae4ac2b20cbc78375230e327e8315965ad70`.

R346 is used only for its `RELAXATION-INVALID` engineering diagnosis. Its
per-case target statuses, iteration counts, residuals, and objective values
cannot enter R347 thresholds, case handling, estimator, statistics, or
scientific interpretation.

**Unchanged scientific contract**: verify the same R344 seal, formal
execution, formal analysis, formal manifest, all 32 guarded trace hashes, and
the same R341 point-model hash frozen by R345. Recover exactly sixteen paired
scenarios, 32 records, 25 samples, two operating points, four disturbance
locations, and both signs. Use the same zero-common three-edge residual, the
same optimistic linear response, the same scenario-coordinate innovation
envelope, and the same node power, ramp, energy, efficiency, and state-of-
charge limits.

For each scenario, require a valid minimum-L2 edge sequence that reduces both
frozen endpoints by at least 2%. Fit the same deterministic standardized
ordinary least-squares map independently per edge with leave-one-scenario-out
folds. Its features contain only that edge's two endpoint physical-frequency
deviations, previous achieved power, and previous commanded power; point,
location, sign, scenario identity, joint coordinates, future values, and
oracle endpoints remain forbidden. Project held-out predictions to the same
physical set before scoring.

For oracle and local candidates, nominal and mismatch-bounded endpoints must
each show at least 2% paired mean improvement, a one-sided 95% Student-t upper
bound below zero, and directional mean improvement at both points, all four
locations, and both signs. Include every scenario.

**Single numerical repair**: represent each feasibility slack as a relative
fraction of its scenario's positive baseline endpoint. The endpoint constraint
is `target + baseline * relative_slack - candidate >= 0`; initialize both
relative slacks at exactly `0.02`; minimize their squared dimensionless norm.
This is algebraically identical to the R345 absolute slack, changes no target
or feasible set, and removes the endpoint-unit scaling from the optimizer.
Only when the valid relative-slack optimum meets both exact frozen targets may
the unchanged minimum-norm solve run. Synthetic tests must show the result is
invariant across a four-order output-scale change and still separates a valid
unreachable target from optimizer failure.

**Execution and persistence**: implementation and synthetic tests precede the
seal. Execute sixteen oracle jobs and sixteen local projection jobs with at
most sixteen single-thread Windows workers in one reused process pool. Write a
create-only attempt before reading cases. Persist a metadata-only oracle
diagnostic before any invalidity stop, then create the complete analysis and
manifest only if every optimizer is valid. No retry, overwrite, tuning, case
drop, threshold change, alternate estimator, simulator, reward, policy,
distributed runtime, EVAL, or training is permitted.

**Execution readiness**: RUN-READY. R344 measured valid whole-host capacity up
to 32 single-thread processes; each R345/R346 wave had only sixteen ready jobs
and ended in about four seconds. R347 retains sixteen workers and one native
numerical thread per worker. Expected completion remains within the quick-run
five-minute envelope, with event-driven terminal observation and no resizing
after sealing.

**Engineering seam**: public scale-stable solver plus adapter `prepare` and
`analyse`. Tests freeze scale invariance, reachable/unreachable separation,
source closure, create-only persistence, sixteen-worker budget, unchanged
scientific contract fields, and absence of simulation, training, EVAL, reward,
or distributed commands.

## Gate

`RESIDUAL-PROBE-ELIGIBLE` requires every source/integrity guard, every valid
oracle target solve and physical-headroom guard, and both oracle and held-out
local candidates to pass the unchanged nominal, mismatch-bounded, paired, and
subgroup gates for both endpoints. It authorizes only one separately sealed
non-learning physical residual intervention.

Otherwise return `NO-TRAINING`, with failed gates retained. A valid target
infeasibility is scientific negative evidence; optimizer failure, corrupt
input, source drift, or invalid projection is `ANALYSIS-INVALID` and cannot be
interpreted scientifically. Every branch keeps training, distributed runtime,
and EVAL unauthorized. R347 has one attempt and no repair or retry.

## 资产保护契约

R341/R344/R345/R346 sources, seals, attempts, failures, diagnostics, traces,
manifests, controller, thresholds, and paper evidence stay byte-unchanged. Add
only the R347 plan, scale-stable probe, stable adapter, targeted tests, seal,
create-only results, feed, claim/question disposition, verdict, and line
navigation reconciliation. No public push.

## Cross-references

- CLM-0910
- Q-0091
- R345 `ANALYSIS-INVALID`
- R346 `RELAXATION-INVALID`
