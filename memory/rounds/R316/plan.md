---
round: R316
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R316 plan — prospective action-withdrawal guard repair

**Opened**: 2026-08-03
**Driver**: answer Q-0071 after CLM-0785 localized R315 invalidity to the
achieved-power zero-request guard.
**Parent**: CLM-0780; CLM-0785; Q-0071.

## TL;DR

Keep the R315 order-10 ERA family, development authority, input shapes,
scientific thresholds, comparison, EVAL profile, and 50-trace bank structure.
Change exactly one execution assumption before new data: when requested power
is zero, permit achieved-power numerical residue up to `1e-6` system p.u.;
request, command, external readback, and internal reference must still be zero
within `1e-12`. Validate on two new operating conditions. Stop at PASS, NO-GO,
or invalid; do not build a controller or agent.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-run render.py if a refreshed programme view is needed. -->

## Open Questions

- Q-0004 and Q-0026 remain unrelated and out of scope.
- Q-0071 remains open because R315 was formally invalid and supplied no
  admissible dynamic-model metric.

## Methodology

### Single-factor guard repair

- R315 is preserved as invalid. None of its physical outcomes enters model
  fitting, scientific thresholds, model order, shape selection, or R316
  analysis.
- The R315 cause-specific canary is used only to define the execution guard:
  for nonzero requested elements, achieved power must retain sign and remain
  within 5% of request; for zero requested elements, achieved power must have
  absolute magnitude `<= 1e-6` system p.u.
- The `1e-6` bound is 20,000 times below the smallest registered nonzero input
  sample (0.02 system p.u.). Request, command, external readback, and internal
  reference retain the unchanged `1e-12` equality tolerance, so the repair
  does not authorize command leakage or hidden action.
- All TDS, algebraic-residual, live M/D, line/generator status, limiter, SOC,
  saturation, topology, sidecar, provenance, and EVAL guards remain unchanged.

### Frozen model and new holdout

- Development authority remains R312 plus R313 HP1 only. R313 HP0, R314
  holdouts, R315 records, and R316 records are forbidden from fitting.
- Recover the same causal 25-step Markov tensor from five-step, 0.05-system-
  p.u. rectangular development responses. Fit order-10 ERA with 8 block rows,
  8 block columns, zero state, 0.2-s sampling, and a frozen 0.995 spectral-
  radius projection rule.
- `HS0`: simplex `OP0,OP1,HP1`, weights `0.25,0.25,0.50`; per-device
  M/D=`177.5/88.75`, tie scale=`1.10`, SOC=`0.41`.
- `HS1`: simplex `OP0,OP2,HP1`, weights `0.25,0.25,0.50`; per-device
  M/D=`202.5/101.25`, tie scale=`1.35`, SOC=`0.51`.
- Both points are distinct from R314 HQ0/HQ1 and R315 HR0/HR1.
- Each point runs one zero trace plus paired common and edge-0/1/2 inputs for
  impulse `[0.05]`, triangle `[0.02,0.04,0.05,0.04,0.02]`, and bipolar
  `[0.05,0.05,0,-0.05,-0.05]`, padded to 25 steps: 50 fresh records.

### Pre-registered scientific gates

Every forced record must meet all applicable bounds:

- parent-FIR versus physical total NRMSE `<= 0.15`;
- order-10 reduction versus parent-FIR total NRMSE `<= 0.10`;
- reduced versus physical total NRMSE `<= 0.15`;
- reduced versus physical global-peak-normalized maximum absolute residual
  `<= 0.20`;
- directly excited coordinate peak-magnitude relative error `<= 0.10` and peak
  timing error `<= 0.2 s`;
- realization spectral radius `<= 0.995 + 1e-10`;
- retained-cross versus matched cross-deleted aggregate physical cross-output
  SSE reduction `>= 20%`, observable cross energy, and win fraction `>= 75%`.

The measured mismatch envelope remains the conjunction of total NRMSE 0.15
and pointwise vector residual 0.20 on this small-signal bank only.

### EVAL and comparison identifiability

- After all 50 source records and sidecars verify, EVAL audits the 36 edge
  views with profile `vector_power`, 1.0-s registered input window, 10,000
  resamples, and seed `2026080316`. It remains diagnostic-only with
  `EXTERNAL_AUTHORITY_REQUIRED`.
- Reduced retained-cross versus matched cross-deleted remains `ALLOW`: the
  sole load-bearing difference is whether common/differential cross outputs
  are retained. Parent FIR versus ERA is `ALLOW` only for reduction fidelity.
- R315 versus R316 is `QUALIFY`: guard and holdout both change, and R315 is
  invalid. No accuracy improvement or causal effect may be attributed across
  rounds.
- Stay out: model-class superiority, controller efficacy, distributed-agent or
  MARL value, topology generalization, stability certificate, robustness,
  deployment, training, and support for the prospective conference-title
  terms.

### Pre-registered outcomes and optimization rules

- `INVALID-DYNAMIC-REDUCTION-VALIDATION`: any seal, model, 50-record execution,
  sidecar, or 36-view EVAL integrity guard fails. Interpret no model metric;
  permit only one new cause-specific canary.
- `DYNAMIC-REDUCTION-NO-GO`: execution is valid but any parent, reduction,
  mismatch, peak, timing, stability, or cross-value gate fails.
  - Parent physical fails while reduction-to-parent passes: stop order tuning
    and open one descriptor/nonlinear-interpolation diagnosis.
  - Parent passes while reduction-to-parent or stability fails: permit one
    separately sealed constrained-realization diagnosis, not an order sweep.
  - Fidelity passes but cross value fails: stop retained-cross control design.
- `DYNAMIC-REDUCTION-PASS`: all gates pass. Close Q-0071 and make one separate
  deterministic-controller-design question eligible. R316 itself authorizes
  no controller, runtime, agent, reward, or training implementation.

No order, pole bound, input, point, threshold, guard, or interpretation changes
after any R316 physical record is observed.

## Asset protection contract

- Preserve R312--R315 artifacts and all paper-cited plant/runtime assets.
- New assets are limited to the R316 plan, seal, model, create-only records,
  EVAL, analysis/provenance, feed, claim, verdict, navigation, and minimum
  new runner/probe/tests. Do not modify the sealed R315 runner or validator.
- Keep the working conference title exactly `Decoupling-Oriented Coordination
  of Paralleled VSGs With Multi-Agent Reinforcement Learning`; evidence terms
  remain prospective.

## Cross-references

- Local predictor authority: CLM-0780.
- Invalid execution and permitted repair: CLM-0785.
- Active question: Q-0071.
