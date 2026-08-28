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
- Workload: `evidence`
**Driver**: R483/R484 的 208-policy audit 使用 legacy 50-Hz learner
observation/reward 语义，而 plant 与 physical endpoints 为 60 Hz；owner
已授权本轮实现、测试与 development canary，但未授权 sealed 208-cell formal attempt。
**Parent**: CLM-1505/R481 deterministic direct-M/D feasibility;
CLM-1515/R483 source factorial; CLM-1520/R484 30-s complete guard.

## TL;DR

一次性训练 `8 arms x 26 seeds = 208` 个 all-fresh learner cells。唯一科学
修正是 learner 从 training 到 evaluation 全链统一 60-Hz frequency/RoCoF
contract；reward 公式与数值系数固定，其实际读取的 frequency slots 改为正确的
60-Hz 物理量（该 reward 不读取 RoCoF slots）。算法、action object、factorial、budget、bank、comparator law
与 guards 固定。训练后同一批 final checkpoints 只跑一次 30-s trace bank；
6-s 结果取其冻结 prefix，不当独立 replication。结果正负都结束大规模实验，
不因 performance 调 reward、补 seed、延长 budget 或重训。

本设计是会议论文的**最小充分方案**，不是算法或实验设计的最优性声明。它只
冻结会导致昂贵返工的 method 与数据边界；结果出来后的统计、图和 discussion
可以继续改进，但不得反过来修改已冻结实验。

当前 authority = **IMPLEMENTATION+DEVELOPMENT-CANARY**。owner 已明确授权长任务
实现、测试、development canary、rehearsal 与 capacity；该授权不包含 sealed
208-cell formal attempt。正式启动仍需 owner 在未来消息单独点名授权。

## Paper-facing experiment card

**一句话目的**：在完全一致的 60-Hz learner contract 下，检验 actor source、
critic source 与 reward access 是否能改善多 VSG 的 M/D 解耦，并区分 endpoint
改善与完整物理/action guard 通过。

| 类别 | 冻结内容 |
|---|---|
| 本轮只改 | frequency/RoCoF learner path 由 legacy 50-Hz 语义改为 physical 60 Hz，且只转换一次；全部 learner 重新训练 |
| 坚决不改 | 算法族、8-arm factorial、26 seeds、43,200 steps、reward 公式与数值系数、action object、profile/scenario bank、direct-M/D law、判定阈值 |
| 旧两轮可用 | 代码/数据路径风险、运行时间、并行容量、产物 schema、失败恢复经验 |
| 旧两轮禁用 | checkpoint、optimizer、replay、curve、evaluation row、performance 数字，以及据其结果挑 arm/seed/threshold |
| 完成 | 208 个 fresh training cells 与冻结 evaluation roster 全部 hash-valid；随后无论 positive、mixed 或 negative 都结束本论文的大规模计算 |

论文 method 主要由本卡、下述参数卡和 factorial/metric 定义生成；discussion
主要解释 endpoint 与 complete guard 是否一致、哪些 source factor 有效、以及
有限拓扑/有限 bank 的边界。不得写成 50-versus-60 因果实验或最优算法搜索。

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

The learner qualification and source-factor inference are separate outputs.
`VALID-POSITIVE/MIXED/NEGATIVE` answer the primary endpoint-plus-guard question:
complete-contract pass / endpoint-only pass / no joint-endpoint qualification.
They are never inferred from a source-factor rejection. Source inference reports
its own `MATERIAL-EFFECT` or `MATERIAL-EFFECT-NOT-ESTABLISHED` result; an
assumption-limited source test does not erase an otherwise valid endpoint/guard
classification.

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
- Source intervention: `N` uses the authentic same-time rows; `P` preserves
  recipient-owned slots and applies the frozen `rho(i)=(i+1) mod 4` row
  permutation to the same-time authentic neighbour 4-tuples. No exogenous
  donor bank exists. Per-seed preparation creates only the fresh common base
  state shared by all eight arms.
- Reward: 公式、聚合方式和数值系数冻结；reward 实际读取的 frequency slots
  改为 canonical 60-Hz 物理行（不读取 RoCoF slots），所以数值 objective 会随正确输入改变，不能写成“reward 数值
  完全不变”。No RMS penalty, TV penalty, coefficient selection or
  hyperparameter search. The known fleet-average M/D cancellation is an
  explicit audited property, not hidden training alignment with the complete
  guard.
- Comparator: frozen development-selected direct-M/D law from R481, bound to
  `results/research_loop/r481_direct_md/formal_analysis.json`; law 不重选，但
  comparator 必须在 R485 同一 physical path 重新执行。R481/R484 旧比值不得当
  R485 分母；identity test 必须证明 legacy adapter 没有造成 60/50 double scale。
- Profiles/scenarios: preserve the registered R483/R484 finite bank and six
  signed common/differential/localised scenarios. Because the rows are already
  historical/outcome-visible, call them a frozen benchmark, never fresh
  generalisation evidence or a population sample.
- Horizon: one 150-step, `dt=0.2 s`, 30-s evaluation trace per registered cell.
  The first 30 steps form the pre-registered 6-s prefix. Horizons are reported
  separately and never counted as independent replications.
- No Phase-3B/RMS arm. The old 26-cell branch addressed magnitude penalty only,
  did not target action variation and is outside the decoupling-centred paper.

参数卡（seal 前必须绑定到 exact source/config）：

| 对象 | R485 规则 | 不允许的做法 |
|---|---|---|
| plant/report frequency | physical 60 Hz | 把 plant 当 50 Hz |
| learner frequency/RoCoF | canonical 60-Hz transform exactly once | 漏转或重复乘 `60/50` |
| reward | 公式与数值系数固定，输入使用同一 canonical 60-Hz rows | 用补偿系数偷偷恢复旧 objective |
| M/D/H | 按 device/system base 与单位重新核对；不作统一 `x1.2` | 把 M、D、H 全部按频率比例缩放 |
| p.u. power/voltage, time, seeds, network/optimizer | 保持冻结值 | 因 canary performance 修改 |
| direct-M/D comparator | law 固定，同路径重跑，adapter 只生效一次 | 复用旧 denominator 或 double conversion |

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

Any failure below blocks prepare/seal and executes zero formal cells. Only five
load-bearing checks are required; do not build a new documentation framework.

1. **60 Hz exactly once**: one golden physical state produces identical
   canonical rows in actor, current/target critic, replay, reward and evaluator;
   restoring 50-Hz semantics or adding a second `60/50` conversion must make the
   test fail. The same test covers units, reset anchor and M/D readback.
2. **Comparator identity**: at a fixed physical state, the production-path
   direct-M/D action equals an independently computed frozen-law action. A test
   fixture combining canonical transform with the legacy adapter must fail if
   it applies `60/50` twice; otherwise comparator execution blocks.
3. **6/30 prefix parity**: for the same controller/profile/scenario, every saved
   field in the 6-s result equals the first 30 rows of the 30-s trace. No second
   6-s simulation is allowed.
4. **Factor/data parity**: routing purity, reward equation/code identity,
   train/eval checkpoint contract, raw/projected/executed action distinction and
   full offline-analysis schema pass focused tests plus one bounded episode.
5. **Short teach-back + rehearsal**: two independent reviewers each use the
   experiment card to explain in plain language what changes, what stays fixed,
   what is compared and what may be claimed; any disagreement or P0/P1 blocks.
   The formal-entry rehearsal separately verifies hashes, installed package/
   case, output absence and complete roster without creating formal output.

### 5. Engineering canary

Before seal, run development seed `500` through all eight arms at the same
43,200-step budget and then through the same evaluation path: exactly eight
development training cells, outside formal seeds `501..526`. The canary may
inspect only data flow, numerical health, artifact completeness and resource
behaviour; its returns/endpoints cannot select coefficients, arms, checkpoints,
thresholds, budget or paper claims.

The canary also executes and schema-validates zero/direct-M/D references on
both same and fresh banks. These deterministic traces test comparator and bank
plumbing only; their endpoint values remain ineligible for selection or claims.

The canary is excluded from formal inference and stored outside the formal
result root. Any source/config change affecting the path invalidates it and
requires a new canary before seal. Owner granted the required long-task
authorisation for implementation and this development canary on 2026-08-28;
that authorisation does not extend to the formal 208-cell attempt.

### 5.1 Minimal implementation boundary (not a launch plan)

目标是正确完成最后一轮大实验，不建设通用实验平台。R485 复用现有
scientific kernels：V4 env/M/D convention、executed-action/source-factorial
SAC、source routing、reward formula、factorial statistics、endpoint/action
guards、artifact/seal helpers。历史 checkpoint/result 不随代码复用。

R485 新实现限于：一个 thin round adapter、一个 R485-only analysis/authority
helper、一个 config、2 个 focused test files，以及本轮必要的
seal/review/shard artifacts。adapter 只拥有
round identity、fixed roster、43,200-step cell loop、30-s evaluation binding、
canonical observation wrapper 和 create-only output；helper 只拥有 exact
roster/lineage validation、learner-admissibility、resolved TDS reproduction、
6/30 analysis、frozen statistics 与 formal authority，不形成通用 framework。现有
`adapt_v4_observations_to_physical()` 是唯一 50->60 observation transform，
不得再写第二套转换器。

为避免复制 guard/authority/I/O，优先复用既有 race-safe artifact I/O 与
scientific kernels；默认旧行为与 focused regression 必须保持。Production code
超过 800 lines 只触发一次 scope/simplicity review，不再作为科学硬门：若删除会
损失显式 roster、lineage、TDS、learner-admissibility 或 complete-contract 检查，
则保留并在 review 中说明。以下任一仍须暂停并回报 owner，不得顺势扩张：复制
整个旧 runner、继续动态套娃旧 round、或引入通用 runner/DAG/plugin/scheduler
abstraction。600--800 lines 是工程告警区间，不是必须写满的预算。

明确排除 adaptive stop、parameter search、RMS/TV reward branch、historical
runner cleanup、全仓重构和 future-proof CLI branches。本节不冻结启动命令、
容量、seal 或正式执行顺序；这些按项目流程在后续 implementation task 单独完成。

### 6. Evaluation and saved data

For every final policy/profile/scenario trace, store create-only full-step data:

- raw physical state and canonical learner observation;
- raw, projected and executed actions plus clamps/slew/saturation;
- commanded and ANDES-readback per-device M/D;
- frequency, RoCoF, common/differential/odd/even components;
- every reward component;
- endpoint integrands, action RMS/TV inputs, validity/done/TDS flags;
- arm, seed, base, profile, scenario, checkpoint, source/config/code hashes.

Exact roster mirrors the frozen two-bank comparison: `4,992` learned traces +
`48` same-bank zero/direct-M/D traces + `48` fresh-bank zero/direct-M/D traces =
`5,088` trajectories. Missing, duplicate or hash-invalid cell/profile/scenario
blocks inference; no seed replacement or partial-result verdict is allowed.

Primary factorial uses final-checkpoint 6-s prefix and seed as inference unit.
Preserve the four registered source contrasts, direct `log(1.10)` materiality
boundary and Holm family of four; exact formulas/test/fallback must pass an
independent statistical audit before seal. The 30-s result is separate
complete-contract evidence and source sensitivity, never pooled with 6 s.
The prospective sample-size authority is
`paper/yang_md_decoupling_marl/working/source_factorial_power_plan.json`
(`n_star=26`); it is design-only and contributes no R485 outcome rows.
For the two main effects the registered coordinate is explicitly
`log(loss_P / loss_N)`, where `N` is the authentic source and `P` is the
row-permuted placebo; a positive value therefore means the authentic source
has lower loss. The two interaction signs follow the exact registered
ratio-of-ratios in `source_factorial_design.seed_effects` and must be labelled
as interactions, not silently renamed as main-effect improvement.

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

### 7. Outcome-blind stop rule

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
- Pure operational interruption may reuse a completed create-only artifact only
  when its seal/hash/manifest are valid. A partial training cell restarts from
  step zero; no mid-cell resume without replay identity. Semantic, scientific
  or hash failure stops the attempt and preserves evidence; it never triggers
  result-based rerun or seed replacement.

## Formal launch contract

- formal_entry: sequentially run the sealed `base_shards.json`, then
  `train_shards.json`, then `eval_shards.json` with
  `/home/wya/andes_venv/bin/python scripts/soft_spot_shard_driver.py --runner scripts/run_r485_60hz_source_factorial.py --shards <sealed-stage-list> --workers 16 --round R485`; no `--resume`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r485_60hz_source_factorial.py rehearse`
- rehearsal_scope: validate one canary zero-action six-scenario 150-step profile through the production trace/schema path; no formal output
- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,output_absence,shard_roster,trajectory_count,representative_schema
- result_root: `results/research_loop/r485_60hz_source_factorial/<sealed-attempt-id>/`
- capacity_evidence: `memory/rounds/R485/capacity_evidence.json`
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0
- expected compute: estimate only until same-path measurement; historical
  scale is about 42 h training plus complete evaluation, not a deadline

The current `round_preflight.py` rejects prefixed `TBD_*` placeholders and this
contract therefore remains fail-closed until rehearsal and capacity are real.
Launch readiness requires zero `TBD`, the two frozen-hash reviews,
same-path rehearsal, measured capacity, formal seal and a new explicit owner
long-task authorisation. Implementation, review, development canary, rehearsal
and capacity are in the current authorised task. Sealing the final formal inputs
and launching the 208-cell attempt still require the later owner decision above.

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
- R485 implementation is limited to `scripts/run_r485_60hz_source_factorial.py`,
  `src/andes_rl_kundur/evaluation/r485_experiment.py`,
  `memory/rounds/R485/config.json`, the two R485 focused test files, the
  minimal fail-closed placeholder repair in `memory/tools/round_preflight.py`,
  and the narrowly compatible reuse edits to R484/U2 analysis authority.
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
