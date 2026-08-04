---
round: R295
state: completed
opened: '2026-08-02'
closed: '2026-08-02'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R295 plan -- graph-spectral DAPI consensus diagnosis

**Opened**: 2026-08-02
**Driver**: Explain and reduce the small fast-inter-area penalty of the
explicit distributed DAPI controller before introducing any neural residual.
**Parent**: Q-0052; CLM-0680.

## TL;DR

Keep the genuine local-agent implementation, physical action, communication
graph, plant, and all gains except integral-consensus speed fixed. Test the
registered `1.0 1/s` controller against `2.0` and `4.0 1/s`, which move the
graph-differential integral states below the measured inter-area time scale
while remaining inside the discrete-time consensus stability interval. Use
only four known high-information development cases. A passing value must be
confirmed by a separate full held-out evaluation; a failed stage ends gain
tuning.

## Snapshot at plan-time (oracle as of 2026-08-02)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete -- re-render STATE.md to refresh navigation, but preserve -->
<!-- this block as the immutable plan-time oracle snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) -- verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0052 [opened R295] Can graph-spectral consensus tuning reduce the residual differential-mode penalty of explicit distributed DAPI without harming common-frequency control?

## Recently Closed (last 3)

- Q-0051 closed-partial @ R294, by CLM-0680 -- Which reduced mathematical model and constrained distributed-control architecture can represent and manage common--differential and fast--slow coupling before any neural policy is trained?
- Q-0049 closed-partial @ R292, by CLM-0675 -- Does a neighbour-only distributed edge policy retain reproducible differential-allocation value against a matched centralized vector actor?
- Q-0048 closed-negative @ R291, by CLM-0670 -- Does deterministic state-aware smooth handoff provide timing-specific value beyond fixed 3 s and fixed 5 s fast-support schedules?

## Methodology

For local agent `i`, retain the R294 law

`eta_dot_i = Ki*(f0-f_i) - kc*(eta_i-mean_{j in N_i} eta_j)`

`P_i^req = Kp*(f0-f_i) + eta_i - Ks*(f_i-mean_{j in N_i} f_j)`.

The row-normalized four-node ring Laplacian has spectrum `{0,1,1,2}`. Thus
the common integral mode is unaffected by `kc`, while graph-differential
integral modes decay at rates `kc*lambda`. With `dt=0.2 s`, the explicit
update factor is `1-dt*kc*lambda`; `kc=4` remains strictly inside the scalar
stability boundary for `lambda_max=2`, although its fastest graph mode changes
sign. The measured nominal-anchor inter-area mode is near `1.13 Hz`, so the
registered `kc=1` differential time constant is comparable to a physical
oscillation period. Candidates `kc={2,4}` are therefore a time-scale-separation
probe, not an arbitrary hyperparameter sweep.

The motivating measured baseline is
`results/r294_model_validation/stage_d_compact_controller_validation`; it is
used only to formulate this new question, not as an R295 held-out comparator.

1. Use the full nonlinear `AndesMultiVSGEnvV4Storage` DAE with the Toggler
   disabled, zero M/D modulation, four ESD1 actions, and the exact explicit
   local-agent DAPI execution from R294 Stage E.
2. Freeze `Kp=2.0`, `Ki=0.2`, `Ks=1.0`, the ring neighbours, `dt=0.2 s`,
   100 steps, projection and anti-windup behavior. Change only
   `kc in {1,2,4} 1/s`.
3. Use the four R294 development scenarios, explicitly as outcome-aware
   development cases: `k1/PQ_0/+`, `k1/PQ_Bus15/-`, `k2/PQ_1/+`, and
   `k2/PQ_Bus14/-`. Run 12 matched trajectories in three shards.
4. Record the registered physical endpoints plus local graph-differential
   integral, frequency, and requested-power RMS diagnostics. The latter are
   explanatory only and cannot rescue a failed endpoint gate.
5. Keep all results development-only. No candidate is formal evidence until
   a later round prospectively freezes and passes a disjoint held-out bank.

## Comparison-identifiability gate

| Field | All three arms | Inference consequence |
|---|---|---|
| Information | own frequency, two neighbour frequencies, two neighbour integral messages | matched |
| Action | four independent projected active-power requests | matched |
| Execution | four independent local objects and states, no global statistic or action aggregation | matched |
| Budget | same horizon, plant, cases, projection, `Kp`, `Ki`, `Ks` | matched |
| Treatment | `kc={1,2,4} 1/s` | identifies only the executed consensus-time-scale effect |

Decision: `ALLOW` for a bounded development inference about `kc`; `BLOCK` for
architecture, MARL, topology-generalization, stability, or deployment claims.

## Frozen gate

Every one of 12 records must complete with finite telemetry, `TDS.test_ok`,
`exit_code=0`, zero storage-constraint violations, and a non-scalar vector
request. Otherwise classify `INVALID-CONSENSUS-TIMESCALE-PROBE` and do not
read performance endpoints as evidence.

For each candidate against `kc=1`, use ratios of matched-bank endpoint means
and the worst individual common-endpoint ratio. A candidate passes only if:

- fast inter-area IAE ratio is at most `0.99`;
- normalized synchronization-loss ratio is at most `1.01`;
- each common-endpoint mean ratio is at most `1.05`;
- the worst individual common-endpoint ratio is at most `1.10`.

If both pass, select the lower fast-inter-area IAE ratio, breaking an exact tie
toward the smaller gain. Classification is
`CONSENSUS-TIMESCALE-CANDIDATE-IDENTIFIED` or
`CONSENSUS-TIMESCALE-NO-GO`. No gain or threshold may be added or altered
after the seal.

## Full-evaluation return gate

If and only if a candidate passes, close this development round and open a new
round with a prospectively sealed bank disjoint from all R294/R295 selection
cases. The full evaluation must freshly execute at least the registered
`kc=1` DAPI, selected DAPI, and centralized vector PI under matched physical
actions and constraints, report paired uncertainty intervals and failures,
and preserve the comparison-identifiability ceiling. If no candidate passes,
do not spend compute on that full evaluation; pivot to a new edge-residual law.

## Asset preservation contract

- Preserve all R274--R294 plans, seals, sources, traces, results, feeds,
  verdicts, and claims byte-for-byte.
- Add only Q-0052/R295 state, one prospective protocol/seal, one runner and
  focused tests, and create-only R295 results with hash sidecars.
- Do not edit paper files, train a network, or use R295 development outcomes
  in claim-bearing prose.

## Cross-references

- CLM-0680: hard decoupling failed; active power is the strongest tested
  common/inter-area actuator; explicit DAPI and centralized vector PI both
  passed, with no clear joint winner.
