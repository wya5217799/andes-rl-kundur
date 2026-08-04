---
round: R300
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R300 plan — held-out doubled relative-RoCoF gain evaluation

**Opened**: 2026-08-03
**Driver**: Convert the only R299 classical candidate into valid or negative
held-out evidence before changing the baseline or reopening learning.
**Parent**: Q-0057; CLM-0705; CLM-0700.

## TL;DR

Run 36 fresh trajectories on the untouched 12-case bank frozen before R299
outcomes: CLM-0700 `Kv`, selected fixed `2Kv`, and centralized vector PI. No
parameter, endpoint or threshold changes are allowed after the first trace.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0057 [opened R300] Does the R299-selected fixed doubled relative-RoCoF gain retain material held-out value over the CLM-0700 baseline and the named centralized PI?

## Recently Closed (last 3)

- Q-0056 closed-negative @ R299, by CLM-0705 — Does the R298 residual-DAPI baseline leave material, locally signalled edge-allocation headroom for a deployable distributed residual?
- Q-0055 closed-positive @ R298, by CLM-0700 — Does the selected zero-sum relative-RoCoF DAPI residual retain held-out fast inter-area value against fresh DAPI and centralized vector PI?
- Q-0054 closed-positive @ R297, by CLM-0695 — Does a full anchor-magnitude zero-sum relative-RoCoF residual cross the materiality gate that the half-magnitude boundary arm narrowly missed?

## Methodology

Use exactly the disjoint bank stored in the effective R299 v2 seal:
`tie k={1.375,1.625} x location={PQ_0,PQ_Bus14,PQ_Bus15} x sign={-1,+1}`.
These operating points were not used in R299 selection. `k` remains an
impedance-strength proxy on one physical topology.

Freshly run three arms for 100 steps at 0.2 s with zero M/D modulation, the
same four ESD1 action coordinates and the same power/current/ramp/SOC/energy
projection:

1. explicit neighbour-local residual DAPI at `Kv=0.2442407125`;
2. the same controller with equal full-anchor edge increments, exactly
   equivalent to fixed `2Kv=0.4884814250` before projection;
3. centralized vector PI with joint four-frequency information and `Ksync=1`.

All arms share `Kp=2`, `Ki=0.2`, vector active-power coordinates, plant,
horizon and constraints. The local arms also share four independent agent
states, `Kconsensus=1/s`, the regular ring and neighbour-only messages.

## Comparison-identifiability gate

- `2Kv` versus `Kv`: same action, feasible set, information, execution,
  controller family, budget, scenarios and endpoints; fixed gain is the sole
  treatment. Decision `ALLOW` for incremental value of this executed retune.
- Either local arm versus centralized PI: same physical vector actuator path
  and limits, but different joint/local information, temporal state and law.
  Decision `QUALIFY` for executed-formulation comparison only.
- `BLOCK` pure decentralization, multi-agent/MARL, neural, topology,
  communication robustness, stability, safety, EMT/HIL or deployment claims.

## Frozen validity and statistical gate

All 36 records and sidecars must exist and pass finite telemetry, TDS, exit,
vector-action, storage and physical guards. Both local arms require 100
mechanism samples and pre-projection total-residual sum error at most `1e-12`.
Any failure makes the bank `INVALID` and all endpoint estimates non-evidence.

The unit is matched operating condition. For each endpoint, compute the
candidate/reference ratio of means and paired 20,000-resample percentile
interval with fixed seed 300004. The selected `2Kv` arm passes versus `Kv`
only if:

- fast inter-area IAE point ratio is at most `0.99` and its 95% interval upper
  bound is strictly below `1.0`;
- synchronization-loss point ratio is at most `1.0` and interval upper bound
  at most `1.01`;
- every common-endpoint interval upper bound is at most `1.05` and worst
  individual ratio at most `1.10`;
- every validity, action, storage, physical and zero-sum guard passes.

Classify `VALID-2KV-PASS`, `VALID-2KV-TRADEOFF`, `VALID-2KV-NO-VALUE`, or
`INVALID`. For centralized secondary comparisons, name one executed formulation
clearer only if both differential-endpoint intervals lie wholly on the same
side of one; otherwise report no joint winner.

## 资产保护契约

- Preserve R274--R299 plans, seals, traces, decisions, feeds, verdicts and
  claims byte-for-byte.
- Add Q-0057/R300 state, one formal runner and focused tests, one create-only
  seal, 36 create-only records and one formal summary with sidecars. No
  manuscript changes and no training.
- Use exactly three scratch-isolated WSL workers. Do not read intermediate
  endpoints or modify the protocol after any trace exists.

## Cross-references

- `results/r298_relative_rocof_formal` is the measured CLM-0700 baseline.
- CLM-0705 authorizes only `2Kv` and the predeclared bank; its ratios are not
  efficacy evidence.
