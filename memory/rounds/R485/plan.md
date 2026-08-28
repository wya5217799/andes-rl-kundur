---
round: R485
state: active
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-28'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R485 plan — final 60-Hz learner factorial for the Yang M/D conference paper

**Opened**: 2026-08-28
**Driver**: R483/R484 的 208-policy audit 使用 legacy 50-Hz learner
observation/reward 语义，而 plant 与 physical endpoints 为 60 Hz；owner
授权沉淀一次最终 corrected successor 的设计，不授权本轮训练或 ANDES。
**Parent**: CLM-1505/R481 deterministic direct-M/D feasibility;
CLM-1515/R483 source factorial; CLM-1520/R484 30-s complete guard.

## TL;DR

一次性训练 `8 arms x 26 seeds = 208` 个 all-fresh learner cells。唯一科学
修正是 learner 从 training 到 evaluation 全链统一 60-Hz frequency/RoCoF
contract；算法、reward、action object、factorial、budget、bank、comparator、
guards 固定。训练后同一批 final checkpoints 只跑一次 30-s trace bank；6-s
结果取其冻结 prefix，不当独立 replication。结果正负都结束大规模实验，不因
performance 调 reward、补 seed、延长 budget 或重训。

当前 authority = **DESIGN-ONLY**。本 plan、审计或测试都不授权 WSL、ANDES、
training、evaluation、capacity probe 或 formal attempt。启动需要 owner 在未来
消息明确说长任务并点名 sealed R485 attempt。

## Snapshot at plan-time (oracle as of 2026-08-28)

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

### 1. Paper question and claim ceiling

Primary question: under one internally consistent 60-Hz learner contract, can
the frozen MARL family improve direct-M/D decoupling endpoints while satisfying
the registered complete physical/action guard?

Allowed if valid:

- finite-design result for one Kundur topology, frozen profiles, 26 seeds,
  43,200-step budget and named learner family;
- endpoint qualification versus complete-contract qualification;
- registered actor-source, critic-source and interaction contrasts;
- `N` versus `P` as total algorithm/source intervention, not pure neighbour-
  information value.

Stay-out:

- causal 50->60 scaling effect; historical R483 values are descriptive only;
- universal MARL capability/failure, convergence/optimality or training
  sufficiency;
- reward-causal, safety, probability, topology-generalisation, EMT, HIL,
  hardware or deployment claims;
- physical realism beyond the declared project-calibration stress regime.

### 2. Frozen design

- Cells: actor source `{N,P}` x critic source `{N,P}` x reward access `{0,1}`
  x seeds `501..526` = 208 all-fresh training cells.
- Batch purity: zero checkpoint, optimizer, replay, curve, evaluation row or
  training manifest carryover from R482/R483/R484. Historical results never
  enter R485 inference.
- Seed/base identity: keep the registered matched seed roster and deterministic
  per-seed base generator to isolate the contract repair; regenerate all R485
  base files create-only and verify hashes across all eight arms.
- Training: fixed 43,200 interaction steps per cell; half checkpoint stored for
  training-dynamics diagnostics, final checkpoint primary. No adaptive outcome-
  based extension or stopping claim.
- Algorithm/object: frozen R483 learner family, executed-action Markov state,
  projector, action decoder, clamps, slew and four-agent information pattern.
- Reward: frozen endpoint-oriented legacy reward. No RMS penalty, TV penalty,
  reward redesign, coefficient selection or hyperparameter search. The known
  fleet-average M/D cancellation is an explicit audited property, not hidden
  training alignment with the complete guard.
- Comparator: frozen development-selected direct-M/D law from R481, bound to
  `results/research_loop/r481_direct_md/formal_analysis.json`; no outcome-
  visible reselection or fallback.
- Profiles/scenarios: preserve the registered R483/R484 finite bank and six
  signed common/differential/localised scenarios. Because the rows are already
  historical/outcome-visible, call them a frozen benchmark, never fresh
  generalisation evidence or a population sample.
- Horizon: one 150-step, `dt=0.2 s`, 30-s evaluation trace per registered cell.
  The first 30 steps form the pre-registered 6-s prefix. Horizons are reported
  separately and never counted as independent replications.
- No Phase-3B/RMS arm. The old 26-cell branch addressed magnitude penalty only,
  did not target action variation and is outside the decoupling-centred paper.

### 3. End-to-end 60-Hz contract

Before any training, one canonical transformation must own all frequency and
RoCoF learner fields. The following paths must consume byte/numerically
identical transformed rows for the same physical state:

`ANDES state -> observation -> actor -> current/target critic -> replay -> reward -> evaluator`.

Required contract:

- physical plant/reporting base = 60 Hz;
- each converted observation slot, unit, sign, normaliser and inverse is listed
  explicitly; conversion occurs exactly once;
- reward frequency terms use the same 60-Hz rows seen by the learner;
- raw observation may be logged for provenance but may not enter any learner,
  replay, reward or evaluation decision path;
- deterministic comparator and learned controller report the same physical
  endpoint definitions without pretending their internal policies are the
  same object.

### 4. NO-RUN gates

Any failure below blocks prepare/seal and executes zero formal cells.

1. **Physical card**: device/system base, H/M/D units, reset anchor, runtime
   readback, action map, clamp and slew pass zero/nonzero/reset/round-trip/
   heterogeneity invariants. H0=100 s is labelled project calibration/numerical
   stress regime; no hardware equivalence is claimed.
2. **Golden state**: one known physical state produces identical 60-Hz learner
   rows in actor, critic, target, replay, reward and evaluator paths.
3. **Mutation falsification**: restore 50-Hz semantics in each path one at a
   time; every mutation must fail the parity test.
4. **Episode trace**: one bounded development episode proves step-by-step
   observation -> raw action -> projected/executed action -> M/D readback ->
   reward components -> replay -> next observation continuity.
5. **Reward identity**: paper equation and production code match numerically;
   sign, units, aggregation and cancellation example are pinned by tests.
6. **Routing purity**: per time/slot/scenario, N/P source multisets equal; P is
   fixed-point-free, no P donor is a true neighbour, both read the same
   contemporaneous state pool, and only registered factor columns differ.
7. **Train/eval parity**: the evaluator loads final checkpoint identity and
   uses the same observation/action contract; raw versus executed actions
   cannot be substituted.
8. **Data sufficiency**: a rehearsal proves every field needed for offline
   reanalysis is stored before long execution.
9. **Independent review**: exact frozen plan/code/config receives one
   confirmatory diff/data-flow review and one adversarial premise/estimand/
   domain review. Any P0/P1 blocks seal.
10. **Formal-entry rehearsal**: same pre-attempt path verifies source/parent/
    config/case hashes, installed package, output absence and checkpoint/base
    inventory without creating formal output.

### 5. Evaluation and saved data

For every final policy/profile/scenario trace, store create-only full-step data:

- raw physical state and canonical learner observation;
- raw, projected and executed actions plus clamps/slew/saturation;
- commanded and ANDES-readback per-device M/D;
- frequency, RoCoF, common/differential/odd/even components;
- every reward component;
- endpoint integrands, action RMS/TV inputs, validity/done/TDS flags;
- arm, seed, base, profile, scenario, checkpoint, source/config/code hashes.

Primary factorial uses final-checkpoint 6-s prefix and seed as inference unit.
Preserve the four registered source contrasts, direct `log(1.10)` materiality
boundary and Holm family of four; exact formulas/test/fallback must pass an
independent statistical audit before seal. The 30-s result is separate
complete-contract evidence and source sensitivity, never pooled with 6 s.

Complete-contract reporting must include continuous margins/distributions,
not binary counts alone:

- Jcross/Jd endpoint ratios;
- common-frequency, worst-peak and RoCoF ratios;
- action RMS and total-variation ratios;
- saturation/slew/nondegeneracy;
- pre-registered threshold sensitivity and endpoint-action Pareto summaries
  computed offline from the same traces.

Representative frequency, M(t) and D(t) plots are selected by a frozen rule
(comparator + median endpoint-qualified policy + worst complete-contract
policy), never by visual attractiveness.

### 6. Outcome-blind stop rule

- Design/integrity/execution invalidity: no scientific verdict; preserve all
  artifacts; successor only after new owner decision. No in-place patch/retry.
- Valid positive, mixed or negative result: report exact finite-design outcome
  and close R485. Poor performance, no convergence certificate, threshold
  sensitivity or an unattractive paper result never authorises more training.
- After the registered evaluation completes, this manuscript's large-compute
  phase is closed. Later work = sealed-data statistics, figures, evidence/
  domain audit and manuscript revision only.
- A new simulation is permissible only for a newly authorised expanded claim,
  never as post-hoc rescue of R485.

### 7. Formal launch contract (blocked until implementation)

- formal_entry: `TBD_R485_IMPLEMENTATION_BLOCKER`
- rehearsal_command: `TBD_R485_IMPLEMENTATION_BLOCKER`
- rehearsal_scope: exact formal pre-attempt path; no scientific trajectory
- rehearsal_checks: source/parent/config/case hashes, installed package/case,
  output absence, base/seed/shard identity, 60-Hz contract and data schema
- result_root: `results/research_loop/r485_60hz_source_factorial/`
- capacity_evidence: `TBD_R485_MEASURED_CAPACITY_BLOCKER`
- host_process_budget: `TBD_R485_MEASURED_CAPACITY_BLOCKER`
- wsl_python_processes: at most 16 training workers plus one launcher, subject
  to fresh measured capacity and owner launch authorisation
- native_threads_per_process: 1
- other_reserved_processes: remeasure immediately before seal; current design
  session observed no WSL job
- expected compute: estimate only until same-path measurement; historical
  scale is about 42 h training plus complete evaluation, not a deadline

The current `round_preflight.py` validates plan structure but does not inspect
`TBD` values; a green design-stage preflight is therefore **not launch
readiness**. Launch readiness requires zero `TBD`, the two frozen-hash reviews,
same-path rehearsal, measured capacity, formal seal and a new explicit owner
long-task authorisation. Removing TBDs, implementing/reviewing tests, running
rehearsal, sealing or launching are future explicit tasks; this design-only
turn does none of them.

## Gate

`NO-RUN` unless every Methodology §4 item is machine/reviewer verified on the
same final hash set and the formal launch contract has no TBD. After seal,
formal attempt requires a new explicit owner long-task authorisation. No gate
may infer that plan approval equals launch approval.

## 资产保护契约

- R478--R484 plans, seals, claims, checkpoints, traces, reports and verdicts
  remain immutable historical evidence.
- Do not edit or pool R482/R483/R484 results; do not relabel old 50-Hz learner
  data as corrected 60-Hz evidence.
- Preserve the manuscript/review/figure/ARTIFACTS batch frozen at commit
  `692766f`; R485 implementation must not amend, revert or rewrite that batch.
- R485 adds only its round artifacts until a separately authorised
  implementation task names exact code/tests/config files.
- No new framework, repository cleanup, runner consolidation or unrelated
  governance repair. The workspace-freeze governance findings were cleared
  before this plan's commit and do not authorise further R485 infrastructure.

## Cross-references

- `paper/yang_md_decoupling_marl/working/post_closure_experiment_and_analysis_plan_20260828.md`
- `paper/yang_md_decoupling_marl/working/corrected_md_revalidation_experiment_plan_20260824.md`
- `paper/yang_md_decoupling_marl/working/manuscript_evidence_map.md`
- `paper/yang_md_decoupling_marl/reports/R481.md` / CLM-1505
- `paper/yang_md_decoupling_marl/reports/R483.md` / CLM-1515
- `paper/yang_md_decoupling_marl/reports/R484.md` / CLM-1520
- `skills/kundur-round/references/experiment-design-guardrails.md`
