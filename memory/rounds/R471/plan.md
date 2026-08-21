---
round: R471
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: external unified execution session ceiling terminated launcher after
  16 valid completed shards; 16 half-only shards excluded
superseded_note: null
---
# R471 plan — U2 source-factorial terminal-predicate successor

**Opened**: 2026-08-21
**Driver**: Repeat the complete U2 experiment after R470 misclassified normal final-step completion as donor failure.
**Parent**: R470 aborted engineering attempt; CLM-1315/R431, CLM-1360/R438, CLM-1440/R460.

## TL;DR

Output-isolated successor that changes exactly one predicate: `done=True` is
accepted at registered step 30/30 and rejected only when premature; any
`tds_failed=True` remains fatal. All 18 cells, six seeds, independent placebo
donors, executed-action SAC semantics, endpoints, multiplicity, materiality,
curve retention, and optimization gates are identical to the R470 plan.

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

- Work class: **evidence**; create-only root
  `results/research_loop/r471_u2_source_factorial`. R470's empty partial
  directories remain untouched and supply no data.
- Freeze all 18 `(actor source in {0,P,N}, critic source in {0,P,N}, reward in
  {0,1})` cells and seeds `401..406`, each at 43,200 physical steps. Same
  networks, optimizers, replay/update budget, development/held-out banks,
  previous-executed state, reward code, and action projector across cells.
- `N` is the real same-time ring-neighbour message; `0` zeros slots 3:7; `P`
  uses two frozen independent scenario-matched donor trajectories with
  `pi(e)=1-e`, left donor `(i,pi(e))`, and right donor `(i+2,pi(e))`. Verify no
  fixed points, no true-neighbour placebo nodes, every semantic tuple changed,
  and exact per-slot/feature/scenario/time pooled-marginal hashes.
- Power remains preregistered from the sealed R431 paired log ratios:
  `sd=0.0823901083`, materiality `log(1.10)`, two-sided alpha .05, power .8,
  `n=ceil(((z_.975+z_.8)sd/log(1.10))^2)=6`. Primary endpoint is held-out
  disturbance differential energy; secondary is off-diagonal response energy.
  Actor and critic `N-P` main effects use seed-paired logs, exact sign flips,
  95% paired-bootstrap intervals, and Holm familywise alpha .05.
- Save full curves plus half/final checkpoints and evaluations. A failed seed,
  half/final direction flip, or absent late-curve stabilization yields
  `OPTIMIZATION-UNRESOLVED`; no retry and no universal communication claim.
- R460 semantics remain exact: Markov state includes previous executed action;
  replay stores raw and executed actions; current/target/actor Q paths use the
  projected action; entropy is only a raw-policy regularizer.

### Sole successor correction

For `T=30` registered steps, abort donor generation iff
`tds_failed_t OR (done_t AND t<T-1)`. Accept `done_{T-1}=True`. Rehearsal must
exercise and record both the accepted horizon terminal and a synthetic
premature-terminal rejection predicate before seal.

### Hardware

Repeat the fresh load check against R438's same-learner ladder. Freeze 16 unique
workers plus one launcher, one native thread each, host Python budget 17, no
other reserved processes. GPU remains excluded because no measured CUDA win
exists for multi-process ANDES plus these small networks.

## Formal launch contract

- `formal_entry`: `scripts/run_r471_u2_source_factorial.py <phase>`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r471_u2_source_factorial.py rehearse`
- `rehearsal_scope`: `objective_semantics_probe`, U3 Q-path probe, exact donor
  audit, identical initialization, real three-step ANDES update, and terminal
  truth table; no formal root.
- `capacity_evidence`: `memory/rounds/R471/capacity_evidence.json`
- `wsl_python_processes`: 17
- `native_threads_per_process`: 1
- `host_process_budget`: 17
- `other_reserved_processes`: 0

## Gate

- `U2-SOURCE-EFFECT-SUPPORTED`: all integrity and optimization gates pass and
  at least one Holm-controlled primary `N-P` effect has CI lower bound above
  `log(1.10)` in the beneficial direction.
- `U2-SOURCE-EFFECT-NOT-SUPPORTED`: integrity/optimization pass but neither
  primary effect clears multiplicity and materiality.
- `OPTIMIZATION-UNRESOLVED`: seed shortfall/failure, direction flip, or absent
  plateau; retain data but authorize no source-effect conclusion.
- `FACTORIAL-INVALID`: initialization, donor, reward/config/hash, executed-
  action, fixed-budget, held-out, or terminal-predicate integrity fails.

## 资产保护契约

Preserve R431/R438/R451/R460/R470 and imported GPT material byte-for-byte. Add
only the R471 adapter/test, new pre-attempt artifacts, create-only result root,
report, claim, verdict, and registrations. No environment, parent learner,
paper result, or manuscript prose change.

## Cross-references

- R470: sealed no-data engineering abort that identified the sole predicate fix.
- CLM-1315: R431 endpoints and seed-paired training reference.
- CLM-1360: R438 measured 16-worker capacity and same learner width.
- CLM-1440: executed-action Bellman path required by all cells.

## Theory intake

- Retained unchanged: source intervention, donor independence/marginal
  identity, paired log effects, Holm control, and executed-action physics.
- Observable prediction: semantic `N` beats marginal-matched `P` beyond 10%
  under at least one actor/critic role without a budget-direction flip.
- Blocked: intrinsic/universal communication value, cross-topology theorem,
  and any use of R470 as scientific evidence.
