---
round: R296
state: completed
opened: '2026-08-02'
closed: '2026-08-02'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R296 plan -- zero-sum neighbour relative-RoCoF residual

**Opened**: 2026-08-02
**Driver**: Act directly on the dominant differential-power path after R295
showed that consensus-state tuning changes internal state but not the endpoint.
**Parent**: Q-0053; CLM-0680; CLM-0685.

## TL;DR

Add one causal filtered-RoCoF state to each explicit local DAPI agent and an
antisymmetric ring-edge residual `-Kv*L*r`. Freeze `Kv=0` plus two gains derived
from the registered 1.135 Hz inter-area mode. Run only 12 development
trajectories. A passing candidate requires material fast-inter-area improvement,
strict pre-projection zero-sum residual action, and all common/physical guards;
only then may a separate full held-out evaluation start.

## Snapshot at plan-time (oracle as of 2026-08-02)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Preserve this bounded plan-time navigation snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) -- verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0053 [opened R296] Can a zero-sum neighbour-relative RoCoF residual materially improve the fast inter-area response of explicit distributed DAPI without common harm?

## Recently Closed (last 3)

- Q-0052 closed-negative @ R295, by CLM-0685 -- DAPI consensus-time-scale tuning no-go.
- Q-0051 closed-partial @ R294, by CLM-0680 -- model-first coupled distributed control.
- Q-0049 closed-partial @ R292, by CLM-0675 -- distributed edge learned comparison was invalid.

## Methodology

For each agent, retain R294's explicit local DAPI law at `Kp=2.0`, `Ki=0.2`,
`Ksync=1.0`, and `Kconsensus=1.0 1/s`. Add the independently owned state

`r_i[k] = alpha*r_i[k-1] + (1-alpha)*(f_i[k]-f_i[k-1])/dt`,

with `dt=tau=0.2 s` and `alpha=exp(-dt/tau)=0.367879`. Each agent exchanges
its current scalar `r_i` with the same two ring neighbours and adds

`Delta P_i = -Kv*(r_i - mean_{j in N_i} r_j)`.

Because the ring is undirected and regular, `sum_i Delta P_i=0` before the
physical projection. This is a controller-coordinate common-mode guard, not a
claim that the nonlinear plant is decoupled.

At the registered anchor frequency `f*=1.1352719 Hz`, `omega*=7.1331 rad/s`.
The continuous filtered differentiator magnitude is
`|H(jw*)|=omega*/sqrt(1+(omega*tau)^2)=4.0943 1/s`. Choose residual gains
`Kv={0, 0.0610602, 0.1221204} system-pu*s/Hz`, making the residual magnitude
approximately 0%, 25%, and 50% of the frozen static synchronizing term at the
anchor mode. These values are frozen before simulation and are not a sweep.

Use the same four explicitly outcome-aware development cases as R295 and run
three arms per case for 100 steps at 0.2 s, producing 12 jobs in three shards.
All arms instantiate the same estimator and differ only in `Kv`. Record base,
residual, total-request differential RMS and maximum residual-sum error.

## Comparison-identifiability gate

| Field | All arms | Consequence |
|---|---|---|
| Sensors/history | own and neighbour frequency streams plus neighbour DAPI integral messages | matched; RoCoF is locally derived, not a new global sensor |
| Action | four independently projected ESD1 active-power requests | matched |
| Execution | four local stateful objects; neighbour scalar messages; no global statistic or aggregation | matched |
| Plant/budget | same cases, horizon, DAPI gains, projection, endpoints and compute class | matched |
| Treatment | `Kv` only | identifies only the executed residual's development effect |

Decision: `ALLOW` for a bounded residual-structure development inference;
`BLOCK` for universal architecture, MARL, topology, stability, safety, or
deployment claims.

## Frozen gate

All 12 records must complete with finite telemetry, 100 residual samples,
`TDS.test_ok`, `exit_code=0`, zero storage violations, vector actions, and
maximum absolute pre-projection residual sum at most `1e-12`. Otherwise the
stage is `INVALID-RELATIVE-ROCOF-PROBE` and performance endpoints are not read.

For each candidate versus `Kv=0`, use ratios of matched-bank endpoint means and
the worst individual common-endpoint ratio. A candidate passes only if:

- fast inter-area IAE ratio is at most `0.99`;
- normalized synchronization-loss ratio is at most `1.01`;
- every common-endpoint mean ratio is at most `1.05`;
- worst individual common-endpoint ratio is at most `1.10`;
- residual RMS is nonzero while the residual-sum guard passes.

If both pass, select the lowest fast-inter-area ratio, breaking an exact tie
toward lower `Kv`. Classify `RELATIVE-ROCOF-CANDIDATE-IDENTIFIED` or
`RELATIVE-ROCOF-NO-GO`. Do not add gains, filters, cases, or endpoints after
the seal.

## Full-evaluation return gate

Only a passing candidate may open a new round. That round must use a
prospectively sealed operating-condition bank disjoint from all R294--R296
selection cases and freshly execute baseline DAPI, selected residual DAPI, and
centralized vector PI with paired uncertainty intervals. If no candidate
passes, do not run the full eval.

## Asset preservation contract

- Preserve R274--R295 plans, seals, traces, decisions, feeds, verdicts, and
  claims byte-for-byte.
- Add Q-0053/R296 state, one reusable local residual controller, one runner,
  focused tests, one JSON seal, and create-only results with sidecars.
- Use `scripts/andes_scratch.py` for every WSL ANDES invocation. Add no extra
  round Markdown beyond plan/feed/claim/verdict.
- Do not edit manuscripts or train a neural policy.

## Cross-references

- CLM-0680 establishes the explicit DAPI baseline and rejects hard plant
  decoupling.
- CLM-0685 closes consensus-speed tuning and identifies the dominant action
  path as the next bounded design hypothesis.
