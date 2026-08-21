---
round: R470
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: normal final-step done=True was misclassified as donor TDS failure;
  no donor file or training trace created
superseded_note: null
---
# R470 plan — U2 actor/critic message-source factorial with independent placebo donors

**Opened**: 2026-08-21
**Driver**: Execute GPT Pro U2 with the corrected U3 executed-action Bellman seam and a donor-independent placebo that destroys semantic pairing while preserving every pooled message marginal.
**Parent**: CLM-1315/R431, CLM-1360/R438, CLM-1440/R460; R451 is a preserved aborted engineering attempt and contributes no results.

## TL;DR

Run the complete `actor source in {0,P,N} x critic source in {0,P,N} x
reward access in {0,1}` factorial on six preregistered seeds.  `N` is the real
same-time neighbour message, `0` zeros all four message slots, and `P` is an
independent scenario-matched donor trajectory with a fixed-point-free episode
permutation and non-neighbour node donors.  All cells share byte-identical
per-seed initial weights, network/optimizer/budget, physical bank, and executed-
action SAC semantics.  The primary result is explicitly exploratory if the
six-seed materiality test or optimization-stability gate is unresolved.

## Snapshot at plan-time (oracle as of 2026-08-21)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Methodology

### Evidence identity and frozen factorial

- Work class: **evidence**; create-only root
  `results/research_loop/r470_u2_source_factorial`.
- Sources `S={0,P,N}`; arms are all 18 triples `(S_actor,S_critic,eta)` with
  `eta in {0,1}`. Seeds are `401..406`; each cell trains for 43,200 physical
  interaction steps on the same 24 disclosed development scenarios and is
  evaluated on the same 24 held-out scenarios.
- Primary endpoint is held-out `disturbance_differential_energy`; secondary is
  `off_diagonal_response_energy`. Primary materiality is a 10% reduction,
  represented by `delta=log(1.10)`. Two primary source contrasts (actor `N-P`
  and critic `N-P`) use seed-paired log endpoint ratios and Holm familywise
  alpha 0.05; 95% paired-bootstrap intervals are reported. All 18 cell curves,
  seed endpoints, failures, and integrity hashes are retained.
- Before any R470 network construction, estimate paired log-ratio SD from the
  sealed R431 message/no-message seed endpoints. With `sd=0.0823901083`,
  `n=ceil(((z_.975+z_.8)sd/log(1.10))^2)=6`. Six seeds are therefore frozen.

### Message-source intervention

- For recipient agent `i` in the four-agent ring, authentic slots are
  `L=(i-1 mod 4,e)` and `R=(i+1 mod 4,e)` at the same time and scenario.
- Each scenario has two independently generated, frozen random-policy donor
  trajectories `e in {0,1}`. Define `pi(e)=1-e`. Placebo slots are
  `L_P=(i,pi(e))` and `R_P=(i+2 mod 4,pi(e))`. Thus `pi(e)!=e` and neither
  placebo node is a true neighbour of recipient `i`.
- Donor banks are generated and hashed before arm training, with independent
  RNG streams. For each slot, feature, scenario, and time, verify that sorting
  over all `(i,e)` gives byte-identical authentic-donor and placebo pools while
  every semantic donor tuple changes. Training code may read only development
  donors; evaluation code may read only held-out donors.
- Source `0` zeros observation slots 3:7 only. Local frequency/RoCoF, previous
  executed action, reward formula, physical dynamics, and action limits remain
  unchanged.

### Learner and reproducibility

- Use R460 executed-action SAC: Markov state is `(observation, previous
  executed action)`; replay retains raw and executed actions; all current,
  target, and actor critic paths consume the projected executed action. Entropy
  remains only a raw-policy regularizer.
- Actor input uses `S_actor`; current/target critic observations use
  `S_critic`. State dimension, four-by-128 hidden width, optimizer, update
  count, replay capacity, batch size, reward code, and interaction budget are
  identical across all cells.
- RNGs are set before environment, network, optimizer, or replay construction.
  One base-state file is created per seed and loaded by every one of that
  seed's 18 cells; all manifests must record the same base-state SHA-256.
- Save full update curves and half/final checkpoints. Any nonfinite/TDS failure
  is retained as a failed seed, never retried. Half/final held-out direction
  flips or absent late-curve stabilization yield `OPTIMIZATION-UNRESOLVED`.

### Hardware and launch

- Physical entry is WSL-only through `scripts/andes_scratch.py`.
- Reuse R438's measured same-learner ladder and perform a fresh load/memory
  check. Freeze 16 unique workers plus one orchestrator, one native thread per
  process, host Python budget 17, other reserved processes 0. Never duplicate
  a scientific shard. GPU is excluded because the formal ANDES path is CPU and
  no multi-process CUDA throughput win is measured for these small networks.
- Phase order: power analysis -> capacity -> U3/source/reward/short-ANDES
  rehearsal -> seal -> six donor/base shards -> 108 training shards -> 36
  half/final arm-evaluation shards -> aggregate. No retry after seal.

## Formal launch contract

- `formal_entry`: `scripts/run_r470_u2_source_factorial.py <phase>`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r470_u2_source_factorial.py rehearse`
- `rehearsal_scope`: synthetic donor audit, `sac_semantics_probe` for U3
  executed-action loss-path parity, reward hash/config identity, identical
  initialization, and three real ANDES steps; no formal root.
- `capacity_evidence`: `memory/rounds/R470/capacity_evidence.json`
- `wsl_python_processes`: 17
- `native_threads_per_process`: 1
- `host_process_budget`: 17
- `other_reserved_processes`: 0

## Gate

- `U2-SOURCE-EFFECT-SUPPORTED`: all integrity gates pass, optimization is
  stable, and at least one Holm-controlled `N-P` primary contrast has a 95%
  interval beyond `log(1.10)` in the preregistered beneficial direction.
- `U2-SOURCE-EFFECT-NOT-SUPPORTED`: all integrity/optimization gates pass but
  neither primary contrast clears materiality and multiplicity.
- `OPTIMIZATION-UNRESOLVED`: full budget/curve checkpoint direction flips,
  late losses do not stabilize, or seed-level failures prevent the paired test.
- `FACTORIAL-INVALID`: initialization, donor independence/marginal equality,
  executed-action, reward/config/hash, fixed-budget, or held-out integrity fails.
- Even a supported contrast is bounded to this learner, bank, action projector,
  and six seeds; it is not a universal intrinsic value-of-communication claim.

## 资产保护契约

Preserve R431/R438/R451/R460 and all imported GPT material byte-for-byte. Add
only the R470 runner/module/tests, preregistered pre-attempt artifacts, create-
only donors/base states/training/evaluation/analysis, report, claim, verdict,
and registrations. No environment, paper-cited result, manuscript prose, or
sealed-root rewrite.

## Cross-references

- CLM-1315: five-seed R431 projected SAC comparison and endpoint definitions.
- CLM-1360: same-learner channel experiment and measured 16-worker capacity.
- CLM-1440: executed-action Bellman semantics required by every R470 cell.

## Theory intake

- Retained: paired source intervention, fixed-point-free donor permutation,
  pooled-marginal identity, seed-paired log effects, Holm control, and the U3
  physical Bellman action.
- Observable prediction: if semantic neighbour information has value beyond
  matched marginals, held-out loss is lower for `N` than `P` under at least one
  fixed actor/critic role, without a budget-direction flip.
- Blocked import: no intrinsic or topology-general communication theorem, no
  pooling of direct-M/D and energy-port evidence, and no reuse of aborted R451
  numbers.
