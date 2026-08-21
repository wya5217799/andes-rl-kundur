---
round: R452
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'CANARY-INVALID: aggregate joint_endpoint_eligible_count and conditional-minimum
  population added an unregistered valid=true filter; immutable shards preserved for
  a resealed successor aggregation'
superseded_note: null
---
# R452 plan — M5 全候选 guard 表与四目标 Pareto 前沿

**Opened**: 2026-08-20
**Driver**: R439 只保留每 profile 的 endpoint winner，R441 证明四个 winner
均违反 action-stress no-harm，但非获胜候选的完整 guard/action 记录不存在，
尚不能判断有限生成类中是否存在低应力联合改善候选。
**Parent**: CLM-1355 (R439), CLM-1365 (R441), CLM-1140 (R399),
advisory M5。

## TL;DR

Freshly rerun all 1,400 generated R439 candidate rows and four static references
on the exact four-profile/six-scenario bank. Store every full R441-style
summary, apply joint endpoint and all no-harm guards, and report the complete
four-objective nondominated set. This is an exhaustive check of the registered
finite generator only, not a lower bound over arbitrary controllers.

## Snapshot at plan-time (oracle as of 2026-08-20)

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

**Frozen scientific contract (prospective):**

- Object and execution seam are byte-reused from R439/R441: direct M/D, four
  VSGs, evaluation profiles `eval_a..eval_d`, six signed scenarios/profile,
  seed 399, 30 steps at 0.2 s, `STATIC_SELECTED =
  local_neighbour_md_km3_kd2`, `_run_trajectory`, `_profiles`,
  `_evaluation_scenarios`, and `summarise_profile`.
- Exact R439 candidate order is reconstructed per profile:
  `K=2`: 25 Cartesian schedules; `K=3`: 125; `K=5`: 200 RNG draws from
  `numpy.random.default_rng(399)`. IDs are `k{K}_{ordinal:03d}` plus
  `global_index=0..349`. Generated duplicates remain distinct. Canonical
  sequence SHA-256 must equal
  `6f505fa569e5a22d8163da44a38292fecc433180cff7640fce6fff4984433962`;
  K5 must contain 192 unique schedules and 8 duplicate rows.
- Every candidate runs all six scenarios and stores its complete
  `summarise_profile` row. Four static references are freshly rerun. Formal
  completion is exactly 1,400 candidate rows, 8,400 candidate trajectories,
  and 24 static trajectories; no pruning, early selection, or deduplication.
- Execution has 68 ready shards: 16 contiguous candidate chunks/profile
  (64 total; balanced 21--22 rows/chunk) plus one static-reference shard/profile.
  Offline verified aggregation creates exactly four profile tables and one
  formal analysis. Sharding changes only execution plumbing, not candidate
  order or selection.
- `genuinely_varying` means at least one adjacent scheduled pair differs.
  Repeated schedules are not called dynamically equivalent to one-segment
  control because R439 resets the execution object at segment boundaries.

**Per-candidate derived fields:**

- Endpoint improvements relative to that profile's fresh static reference:
  `I_d=(E_d,static-E_d,candidate)/max(E_d,static,1e-12)` and analogously
  `I_x` for off-diagonal energy.
- Joint endpoint eligibility is `I_d >= 0.05` **and** `I_x >= 0.05`.
- Common no-harm is all three R441 inequalities at `<=1.03 x static`:
  common-frequency IAE, worst-unit peak, and worst RoCoF.
- Action no-harm is both R441 inequalities at `<=1.10 x static`: action RMS
  and total variation. Saturation passes at `<=0.05`; validity additionally
  requires the full summary `valid` flag (completion, mapping, bounds, slew,
  finiteness).
- `joint_guard_feasible` requires joint endpoint eligibility, validity,
  common no-harm, action no-harm, and saturation pass.
- The nondominated set is computed among valid + common-clean +
  saturation-clean rows over four minimized ratios
  `(E_d/E_d0, E_x/E_x0, action_rms/action_rms0, action_tv/action_tv0)`.
  Weak-all/strict-one dominance is used; objective ties and duplicate IDs are
  retained.

## Theory intake

```
observable: finite-generator guard-clean joint headroom
  definition: existence of joint_guard_feasible candidates in each of four profiles
  source: results/research_loop/r452_m5_all_candidate_pareto/formal_analysis.json#/classification
  predicts: a lower-stress endpoint-improving candidate may exist even though the R441 endpoint winner violated action guards
observable: conditional minimum action stress
  definition: minimum action RMS and minimum action TV among candidates with both endpoint improvements >=5%
  source: same file #/profiles/*/conditional_minima
  predicts: if finite-grid trade-off is not structural, at least one profile contains a lower-stress eligible row
observable: four-objective finite-grid frontier
  definition: all nondominated generated IDs under the registered valid/common/saturation-clean filter
  source: same file #/profiles/*/pareto
  predicts: endpoint and action objectives expose a bounded trade-off rather than one winner
```

## Gate

- Source/parent/case/output pre-attempt checks, targeted tests, same-entry
  rehearsal, representative capacity evidence, and `BLOCK=0` precede seal.
- Rehearsal runs one fresh static and one fresh candidate trajectory, verifies
  candidate hash/count/duplicates, chunk partition, exact guard boundaries,
  Pareto ties, output absence, installed ANDES/case, and parent hashes. It is
  non-authoritative and creates no formal output.
- Static anchors: every finite numeric summary field must reproduce R441 static
  within relative error `<=1e-6`; booleans/identity are exact. R439 winning
  `(K,schedule)` rows must reproduce R441 winner summaries and guard booleans
  under the same rule.
- Completeness requires 68/68 hashed shard payloads, exact expected ID sets,
  no missing/extra/duplicate ID, exact 8,424 trajectories, four complete
  profile tables, all finite summaries, and valid parent/source/seal hashes.
- `GUARD-CLEAN-JOINT-HEADROOM-IN-GRID`: all four profiles contain at least one
  `joint_guard_feasible` candidate.
- `PARTIAL-GUARD-CLEAN-JOINT-HEADROOM-IN-GRID`: one to three profiles contain
  such a candidate.
- `NO-GUARD-CLEAN-JOINT-HEADROOM-IN-GRID`: complete valid bank, zero profiles
  contain such a candidate.
- Any completeness, hash, identity, finiteness, static/winner anchor, schema,
  or trajectory failure takes precedence as `CANARY-INVALID`; preserve and
  stop, with no in-round patch/retry after seal.

## Experiment efficiency card

- Execution readiness: `MEASURE-FIRST` until runner tests, rehearsal, and fresh
  representative capacity evidence pass; then `RUN-READY` only after seal.
- Stage: pre-seal tunable; formal is frozen and outcome-blind.
- Jobs/dependencies: 68 independent execution shards -> verified four-profile
  aggregation -> serial classification.
- Capacity prior: R441 same-object ladder measured 2.3599 trajectories/s at
  16 one-thread workers with zero other reservations; this is a prior, not the
  R452 seal input. R452 remeasures 32 representative trajectories per rung
  `1/2/4/8/12/16`, retains all rungs, checks inherited 943,718,400-byte worker
  RSS floor plus 3 GiB OS reserve, and freezes the highest safe accepted rung.
- Current target if fresh evidence agrees: 16 workers + one launcher,
  `host_process_budget=17`, `wsl_python_processes=17`,
  `native_threads_per_process=1`, `other_reserved_processes=0`.
- ETA prior: 8,424 / 2.3599 = about 3,570 s pure trajectory time, plus shard
  startup/aggregation/tail; formal ETA is recalibrated from the fresh ladder
  before seal and the first completed shard wave after launch.
- Monitor only process count, completed shard count, terminal artifacts,
  resource guards, and explicit engineering failures; do not read candidate
  outcomes before all shards pass completeness.

## Formal launch contract

- `formal_entry`: WSL scratch launcher + `soft_spot_shard_driver.py`, runner
  `scripts/run_r452_m5_all_candidate_pareto.py`, sealed 68-shard JSON; then
  the same runner `aggregate` after all sidecars verify.
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r452_m5_all_candidate_pareto.py rehearse`.
- `rehearsal_scope`: pure generator/guard/Pareto checks plus one real static
  and one real candidate trajectory; no formal result.
- `rehearsal_checks`: source/parent hashes, installed package/case, output
  absence, candidate sequence, chunk partition, summary schema, guard
  boundaries, Pareto ties, physical completion/identity.
- `capacity_evidence`: fresh `memory/rounds/R452/capacity_evidence.json`;
  representative 32 jobs/rung and all rung records retained.
- `host_process_budget`: 17; `wsl_python_processes`: 17;
  `native_threads_per_process`: 1; `other_reserved_processes`: 0. These four
  values are prospective targets and must be updated to the measured rung
  before seal if fresh capacity differs.

## 资产保护契约

- Read-only: R399/R416/R439/R441 source, results, seals, feeds, claims;
  all existing `src/`, scripts, tests, and paper assets.
- New only: R452 runner/test, capacity/rehearsal/seal, shard list, hashed
  `results/research_loop/r452_m5_all_candidate_pareto/`, feed/claim/verdict,
  manifest and line pointers at successful closeout.
- No training, learner change, candidate adaptation, topology change, new bank,
  threshold tuning, result-driven retry, or manuscript prose edit.

## Cross-references

- CLM-1355, CLM-1365, CLM-1140; advisory M5; R439/R441 runners and seals.
