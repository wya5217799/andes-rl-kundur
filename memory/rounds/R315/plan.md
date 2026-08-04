---
round: R315
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R315 plan — sealed low-order dynamic reduction on off-template inputs

**Opened**: 2026-08-03
**Driver**: answer Q-0071 with one frozen reduced dynamic model and one fresh
physical mismatch bank before any controller or agent work.
**Parent**: CLM-0770; CLM-0775; CLM-0780; Q-0071.

## TL;DR

Use only the already declared R312 plus R313-HP1 development responses carried
by the R314 predictor artifact. Recover a causal 25-step Markov sequence from
the five-step rectangular pulses, interpolate it with the already validated
local simplexes, and freeze one order-10 ERA realization per new operating
point. Project poles only when needed to a spectral radius of 0.995. Then run
50 new physical traces at two untouched operating conditions using impulse,
triangle, and bipolar inputs. Stop at `DYNAMIC-REDUCTION-PASS`,
`DYNAMIC-REDUCTION-NO-GO`, or invalid execution. Do not tune a controller,
create a distributed runtime, define rewards, or train agents.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-run render.py if a refreshed programme view is needed. -->

## Open Questions

- Q-0004: AndesBaseEnv absorb-into-V4 remains unrelated and out of scope.
- Q-0026: archive-query loop signal remains unrelated and out of scope.
- Q-0071: what reduced-order plant surrogate and prospective residual envelope
  are sufficient before deterministic controller design?

## Methodology

### Frozen development authority and realization

- Development truth is limited to R312 (27 traces) and R313 HP1 (17 traces).
  R313 HP0, all R314 holdouts, and all R315 records are forbidden from fitting.
- The R314 `predictor_model.json` is used only as a provenance-checked carrier
  of those development templates and the already validated local-simplex rule;
  `R314_holdout_accessed` must remain false.
- For each input coordinate, invert the known five-sample rectangular pulse to
  obtain a causal 25-step Markov sequence. No outcome-dependent smoothing,
  regularization, or late-horizon truncation is allowed.
- At each R315 operating point, interpolate the Markov tensor with the frozen
  local simplex, then fit ERA with order 10, 8 block rows, 8 block columns,
  zero initial state, 0.2 s sample period, and the standard causal convention
  `y[k] = C x[k] + D u[k]`, `x[k+1] = A x[k] + B u[k]`.
- If the raw spectral radius exceeds 0.995, eigenvalue magnitudes are projected
  once to 0.995 while eigenvectors, B, C, and D are retained. This projection
  is part of the frozen candidate, not a post-holdout repair.
- The full retained-cross parent is the interpolated 25-step FIR response. The
  reduced candidate is the order-10 realization. The matched cross-deleted arm
  uses the same reduced prediction and only sets common-to-differential and
  differential-to-common output components to zero.

### Fresh operating conditions and off-template bank

- `HR0`: simplex `OP0,OP1,HP1`, weights `0.35,0.15,0.50`; per-device
  M/D=`182.5/91.25`, tie scale=`1.10`, SOC=`0.43`.
- `HR1`: simplex `OP0,OP2,HP1`, weights `0.35,0.15,0.50`; per-device
  M/D=`197.5/98.75`, tie scale=`1.25`, SOC=`0.49`.
- Both points differ from the R314 HQ0/HQ1 holdouts. No R315 trace may be read
  before the model artifact and formal seal are created.
- Inputs use common and edge-0/1/2 coordinates, paired signs, and a 25-step
  horizon. The three registered positive sequences are: impulse
  `[0.05]`, triangle `[0.02,0.04,0.05,0.04,0.02]`, and bipolar
  `[0.05,0.05,0,-0.05,-0.05]`; the negative case multiplies the whole
  sequence by -1. Each point also has one zero trace: `2*(1+4*3*2)=50`.
- The peak amplitude 0.05 system p.u. already occurs in development data.
  R315 tests new temporal shapes and operating conditions, not unseen-amplitude
  generalization.
- Physical plant, two-phase solver, topology, action coordinates, 60-Hz
  telemetry, and execution guards remain inherited from valid R312--R314
  execution authority.

### Pre-registered mismatch and mechanism gates

All forced records must meet every applicable bound; aggregation cannot hide a
failed record.

- parent-FIR versus physical total NRMSE `<= 0.15`;
- reduced versus parent-FIR total NRMSE `<= 0.10`;
- reduced versus physical total NRMSE `<= 0.15`;
- reduced versus physical global-peak-normalized maximum absolute residual
  `<= 0.20`;
- reduced versus physical peak-magnitude relative error `<= 0.10` and peak
  timing error `<= 0.2 s` on the directly excited coordinate;
- every frozen realization has spectral radius `<= 0.995 + 1e-10`;
- the matched retained-cross arm reduces aggregate physical cross-output SSE
  by at least 20%, wins at least 75% of observable cross records, and the
  aggregate physical cross energy is nonzero.

The registered mismatch envelope is therefore the conjunction of a global
energy bound (`NRMSE <= 0.15`) and a pointwise vector bound (maximum residual
no more than 20% of that record's physical global peak). It is a measured
small-signal envelope on this bank only, not a robustness certificate.

### EVAL diagnostic rule

- Verify all 50 source JSON records and sidecars before creating any EVAL
  input. EVAL uses the 36 edge-source records only, profile `vector_power`,
  1.0 s required active window, 10,000 bootstrap resamples, and seed
  `2026080315`.
- Guard values are synthesized fail-closed from authoritative physical record
  fields; every EVAL view binds the original source path and SHA-256.
- EVAL remains diagnostic-only with `EXTERNAL_AUTHORITY_REQUIRED`. Its
  scorecard cannot change the formal classification or thresholds. Run it only
  after the sealed physical bank is complete; if it fails, repair only the
  source/view integrity cause and never tune the model from EVAL outcomes.

### Comparison-identifiability gate

- Reduced retained-cross versus matched cross-deleted: `ALLOW`. Information,
  realization, order, state initialization, inputs, physical records, horizon,
  metric budget, and execution are identical. The only load-bearing difference
  is whether the predicted common/differential cross outputs are retained. The
  estimand is held-out cross-output prediction error in this frozen model.
- Parent FIR versus order-10 ERA: `ALLOW` only as a reduction-fidelity check;
  both are fitted to the same development Markov tensor. It is not an efficacy
  or algorithm-superiority comparison.
- R314 versus R315: `QUALIFY`. Model representation, excitation family, and
  holdout points all change, so no isolated improvement or causal attribution
  is allowed.
- Stay out: predictor-class superiority, controller efficacy, distributed
  execution value, agent or MARL value, topology generalization, stability
  guarantee, deployment, and any claim that the conference-title terms are
  already validated.

### Pre-registered outcomes and optimization rules

- `INVALID-DYNAMIC-REDUCTION-VALIDATION`: any seal, source, model-provenance,
  50-record execution, sidecar, or 36-record EVAL integrity guard fails. Do not
  interpret model metrics; run only one cause-specific execution/EVAL canary.
- `DYNAMIC-REDUCTION-NO-GO`: execution is valid but any stability, parent,
  reduction, mismatch-envelope, peak, timing, or cross-value gate fails.
  - Parent physical gate fails while reduction-to-parent passes: stop order
    tuning and open one descriptor/nonlinear-interpolation diagnosis.
  - Parent physical gate passes but reduction-to-parent or stability fails:
    permit one separately sealed constrained-realization diagnosis; no order
    sweep on the R315 holdout.
  - Fidelity gates pass but cross value fails: stop this retained-cross route
    before controller design.
- `DYNAMIC-REDUCTION-PASS`: every execution and scientific gate passes. Close
  Q-0071 and make a separately registered deterministic-controller-design
  question eligible. R315 itself still authorizes no controller, distributed
  runtime, agent, reward, or training implementation.

No threshold, order, pole limit, input, operating point, or interpretation may
change after any R315 physical record is observed.

## Asset protection contract

- Preserve all R312--R314 evidence and paper-cited plant/runtime assets.
- New evidence assets are limited to the R315 plan, seal, model, create-only
  source records, EVAL views/report, analysis/provenance, feed, claim, verdict,
  manifest entry, and the minimum reusable code/tests needed to produce them.
- The working conference title stays exactly `Decoupling-Oriented Coordination
  of Paralleled VSGs With Multi-Agent Reinforcement Learning`; R315 may update
  only its evidence navigation and current gate, never its wording.

## Cross-references

- Stage-1 authority: CLM-0770.
- Global predictor NO-GO: CLM-0775.
- Local predictor PASS and development provenance: CLM-0780.
- Active question: Q-0071.
