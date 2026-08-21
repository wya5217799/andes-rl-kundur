---
round: R411
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R411 plan — A1 探针幅度阶梯 (probe-amplitude ladder)

**Opened**: 2026-08-17
**Driver**: soft-spot program A1（owner 授权创造模式整夜任务）：
perturbation-amplitude 阶梯——signed-pair 归一化假设奇响应、单幅度网格；
本轮在 R410 冻结 bank 上重评估 5 个幅度因子，保护论文核心数字的
线性假设。
**Parent**: CLM-1215 (R410)；`working/soft_spot_experiment_program.md` A1；
owner 决策 `working/route_owner_decision_soft_spot_program_2026-08-16.md`。

## TL;DR

Workload: `evidence`。Eval-only。5 幅度因子 {0.5,0.7,1.0,1.3,1.5} × R410
冻结 8-profile 契约的 4 个 eval 剖面；只读加载 R410 9 组 arm-seed
checkpoint + deterministic 参照（local_neighbour_md_km2_kd2）；唯一变化
因子 = `probe_magnitude` × factor（localized_magnitude 不变）；同
estimators（summarise_profile）/ 同 guards / 同冻结分类器
（classify_canary）；新结果根 create-only。幅度 1.0 重评估 = R410 漂移锚
（预期 bit-identical 行 + 1e-6 相对偏差上限）。每 (arm,seed)×幅度 = 1
shard，共 50 shards / 1200 records（≈4h serial）；容量阶梯 rungs
1/2/4/8/12/16、每 rung 32 个代表性 eval 任务、5% 边际 + 半内存规则
（worker RSS 下限 = R402 锚 944,214,016 B）；阶梯后 seal 冻结预算再执行。

## Methodology

### Mission boundary

- Outcome: `formal_analysis.json`（hashed）= 每幅度的冻结 canary 分类 +
  每幅度每 arm-seed-profile 块的 endpoint 比值与 guard 状态 +
  幅度不变量表 + 1.0 漂移锚判定；随后 feed/claim/verdict/LINE 一致关闭。
- Authority: soft-spot program A1（creative mode，pause 分支自动续走 +
  校准日志记录）。
- Permitted: 新 runner `scripts/run_r411_probe_amplitude_ladder.py` +
  测试、共享分片驱动 `scripts/soft_spot_shard_driver.py` + 测试、
  results 根 `results/research_loop/r411_probe_amplitude_ladder/`
  （create-only）、本轮 ledger/feed/手稿收尾。
- Forbidden: 改 R410 runner/learner/契约模块/R402-R410 任何 sealed 资产；
  训练任何新策略；换估计器/guard/分类器；动 R410 结果根（只读）。
- Terminal: formal_analysis.json 存在且 50 shards 全部落盘。

### 冻结协议 (frozen-first)

- AMPLITUDE_FACTORS = (0.5, 0.7, 1.0, 1.3, 1.5)，协议常数封存。
- 每因子 f：eval 剖面 (canary_eval_a..d) 的 `probe_magnitude` × f；
  `localized_magnitude`、baseline_m0/d0、steady_loads 全部不变；
  scenarios 经冻结 `_signed_scenarios` 重建（common/differential 幅度 =
  缩放后 probe；localized 幅度 = 注册值）。
- 评估：3 学习臂 × 种子 401/402/403 + deterministic；checkpoint =
  R410 `final.pt`（加载前 sha256 对照父清单）；eval 循环逐字复用 R410
  语义（同 env 构造 / 同 projector / 同 mask / 同 deterministic 路径）；
  record 增 `amplitude_factor` / `probe_magnitude_executed` /
  `localized_magnitude_executed` 三字段，数值路径不变。
- 输出布局: `eval/<arm>/<seed|deterministic>/a<key>/<profile>.json`
  (hashed, create-only)。
- 分片: shard_id = `<arm>|s<seed>|a<key>` 或 `<arm>|det|a<key>`，共 50。
  resume 规则（plan 注册）：host-side crash 签名下以 `--resume` 重跑该
  shard，只补写缺失 profile 文件（文件粒度原子写入，已存在文件只校验
  不重写）；非 crash 失败按 missing-record 规则处理。
- 完成判据: 200 个 profile 文件（50 shards × 4）hashed 存在 + sidecar
  有效；classify 输出完整表。

## Gate

- 分类树 = 冻结 `classify_canary`（bank 完整性 → 行有效 → 物理 no-harm +
  动作 stress 守卫 → message 增量 → seed 一致 → 优于确定性参照 → 奖励
  不参与），阈值逐字为 R401 契约值。
- **主预注册测量**: 每幅度的分类 + 每 arm-seed-profile 块 endpoint 比值
  （learning / deterministic 同幅度）与 guard 状态；跨幅度比值相对展宽
  ≤20% → AMPLITUDE-ROBUST，>20% → AMPLITUDE-SENSITIVE（如实记录）。
- **1.0 漂移锚（预注册）**: 幅度 1.0 各行 `freq_hz_physical` 与 R410
  同块记录逐元素相等（bit-identical 预期）+ summary 端点相对偏差
  ≤1e-6；超差 → DRIFT，记录并调查环境，creative 模式下继续。
- **分类一致性（预注册）**: 5 幅度分类一致 → CLASSIFICATION-AMPLITUDE-
  INVARIANT；翻转（如某幅度 CANARY-PASS 或 CANARY-INVALID）→ 如实记录
  边界，claim 范围短语按幅度收窄，不暂停。
- 预注册失败 flag: 任何幅度 bank 不完整 → 该幅度记为 invalid 并报告；
  TDS 失败记录 guard 状态为 fail。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r411_probe_amplitude_ladder.py --shards tmp/andes/r411_shards.json --workers 8 --round R411` (50 shards, driver = launcher, budget 内) + `... run_r411_probe_amplitude_ladder.py classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r411_probe_amplitude_ladder.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + 幅度 0.5 真实 1 步 rollout 每臂（mask exercised）+ checkpoint 加载 + save/load roundtrip + deterministic 控制器 act；不创建 formal artifact。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R411/capacity_evidence.json
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 执行修正（只增派生视图，不改科学契约，R410 endpoint-table 先例）

- 冻结分类器在 CANARY-FAIL 路径不返回 `canary` payload（消息增量中位表
  只在守卫全过路径计算），故 `formal_analysis.json` 不含每幅度消息对比。
- 修正：新增只读派生探针 `probes/r411_message_contrast_ladder.py`，读
  R411 sealed eval records，用同估计器复算每幅度的 message-vs-no-message
  与 message-vs-scalar 三种子中位增量 + two-of-three，写入
  `results/research_loop/r411_probe_amplitude_ladder/message_contrast_ladder.json`
  （create-only, hashed）。分类器、阈值、guard、分类结果全部不变。
- 预注册解释：R410 头条负增量（-78.43% / -26.74%）是幅度 1.0 值；阶梯
  表报每幅度增量与符号稳定性（全部幅度为负 → 定性对比结论幅度稳健）。

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit。
- R410 runner/结果/记录、R402 契约模块、learner、estimators、控制器模块
  全部只读；checkpoint 只读（sha256 对照）。
- paper-cited 资产（base_env / andes_vsg_env_v4 / train.py /
  paper_grade_axes.py）只读。
- 新文件仅: run_r411 runner + tests、soft_spot_shard_driver + tests、
  R411 results 根（create-only）、ledger/feed/手稿收尾文件。
- 容量痕迹（阶梯任务 + 分片日志）非 claim-bearing，住 tmp/andes 与
  memory/rounds/R411。

## Cross-references

- CLM-1215 (R410)：本轮的父证据与 1.0 锚源。
- CLM-1160 (R402 容量扩容先例)：RSS 锚来源。
- `working/soft_spot_experiment_program.md` A1：冻结协议 + 完成判据。
- `working/route_owner_decision_soft_spot_program_2026-08-16.md`：授权。
- SKILL.md §2/§4：round 生命周期、容量阶梯抗噪规则（≥32 任务/rung、
  5%±2pp 复测）。
