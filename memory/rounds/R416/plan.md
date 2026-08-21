---
round: R416
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R416 plan — A3 确定性规则池扩充 + 预言机 (law-family expansion + oracle)

**Opened**: 2026-08-17
**Driver**: soft-spot program A3（owner 授权创造模式整夜任务）：
加固"无实测余量"结论——R399 只在九种法则上测得预言机零余量；本轮把
规则池扩到 21 种（加密增益网格 + 一种 PI 型法则）并用同一预言机在同一
四块评估剖面上测余量。
**Parent**: CLM-1140 (R399 九法则零余量)、CLM-1220/1225/1230 (A1/A2/A4)；
`working/soft_spot_experiment_program.md` A3。

## TL;DR

Workload: `evidence`。Eval-only。冻结扩展候选集（
`src/andes_rl_kundur/evaluation/soft_spot_headroom_expansion.py`）：惯性
增益 {0.5,1.0,1.5,2.0,3.0} × 阻尼增益 {0.5,1.0,1.5,2.0} = 20 种网格法
则（含原九种）+ 1 种 PI 型符号比例-积分频率反馈法则（每机独立、
u=tanh(-kp·Δf-ki·∫Δf)、积分限幅 ±2、同 slew 投影）= 21 候选。R399 的
剖面、估计器、阈值、guards、结果可见预言机语义逐字复用（
`classify_bank` 原样消费新契约）。双锚：九种原法则重评必须与 R399
逐位一致（行级）+ 九法则子集分类必须 1e-6 复现 R399 的 development
选择与预言机改善。完成判据 = 预言机余量 delta 的 hashed JSON。22 arms
× 6 profiles × 6 scenarios = 792 records ≈ 100 min serial → 共享分片
驱动 + 容量阶梯（rungs 1/2/4/8/12/16、32 任务/rung、5% 边际 + 半内存），
seal 冻结预算。

## Methodology

### Mission boundary

- Outcome: `formal_analysis.json`（hashed）= 扩展族 development 选择 +
  预言机每评估剖面选择 + 预言机余量 delta（off-diag / differential）+
  分类（HEADROOM-PASS / STOP-NO-JOINT-HEADROOM）+ 九法则锚判定；随后
  feed/claim/verdict/LINE 一致关闭。
- Authority: soft-spot program A3（creative mode，pause 分支自动续走 +
  校准日志记录）。
- Permitted: 新模块 soft_spot_headroom_expansion.py + 测试、runner
  `scripts/run_r416_headroom_expansion.py` + 测试、results 根
  `results/research_loop/r416_headroom_expansion/`（create-only）、复用
  共享分片驱动、正常收尾。
- Forbidden: 改 R399 runner/契约/分类器/per_vsg_md 源码；训练；换
  估计器/阈值/guard/预言机语义；候选集封存后改动；动 paper-cited
  资产。
- Terminal: 22 arms × 6 profile 文件落盘 + formal_analysis.json 存在。

### 冻结协议 (frozen-first)

- 候选集 21 项（模块常量，seal 校验）；PI 法则参数 kp_m=kp_d=1.0、
  ki_m=ki_d=0.4、积分限幅 2.0、slew 0.25、dt 0.2 s 全冻结。
- 记录循环 = R399 `_run_job` 逐字语义（env 构造、adapt、act、行 schema
  全部一致）；seed 399、30 步 × 0.2 s、同 6 剖面（2 dev + 4 eval）。
- 分片: shard_id = arm_id（22 shards）；resume 规则同 R411（缺失
  profile 文件补写）。
- 分类: `classify_bank(summaries, contract=扩展契约)` 原样；锚 =
  九法则子集 + R399 契约 → 与 R399 `formal_analysis.json` 比
  development 选择相等 + 预言机改善相对偏差 ≤1e-6。

## Gate

- 分类树与阈值 = R399 冻结（5% 联合改善 + 3%/10% no-harm + 全 guards +
  预言机 per-profile 结果可见选择）。
- 主预注册测量: 扩展族预言机余量 delta（off-diag / differential，vs
  扩展族 development 选择法则）；delta ≥ 5% 且 guards 全过 →
  HEADROOM-PASS（R399 的"无余量"须收窄到九法则族）；否则
  STOP-NO-JOINT-HEADROOM（扩展族内仍无余量，加固原结论）。
- 九法则锚（预注册）: 行级 bit-identical + 子集分类 1e-6 复现；超差 →
  ANCHOR-DRIFT 记录并调查，creative 继续。
- 预注册失败 flag: 任一 record 失败 → 该臂 invalid；分类
  ANALYSIS-INVALID → 如实记录。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r416_headroom_expansion.py --shards tmp/andes/r416_shards.json --workers <ladder> --round R416` (22 shards, driver = launcher, budget 内) + `... run_r416_headroom_expansion.py classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r416_headroom_expansion.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + zero/网格法则/PI 法则各 1 条真实完整记录（同 job loop，不创建 formal artifact）。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R416/capacity_evidence.json
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 执行修正（分析步，只修 JSON 形状处理不改科学契约，R411 probe 先例）

- 封存 runner 的 `classify` 在九法则锚处按 R399 `formal_analysis.json`
  的 `classification` 字段为字符串（非对象）处理出错；22 shards 的物理
  执行已全部落盘且有效，本修正不重跑任何轨迹。
- 修正：新增只读分析探针 `probes/r416_headroom_classify.py`，读 R416
  sealed records，按计划同一语义执行扩展族 `classify_bank` + 九法则锚
  （R399 字段形状修正：`classification` 为字符串、锚数值取顶层
  `selected_deterministic_arm` 与 `oracle_gate`），写入
  `results/research_loop/r416_headroom_expansion/formal_analysis.json`
  与 `formal_manifest.json`（create-only, hashed）。分类器、阈值、
  guard、预言机语义全部不变。

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit。
- R399 runner/结果/契约模块、per_vsg_md.py、V4 env 全部只读。
- paper-cited 资产只读。新文件仅: 扩展契约模块 + tests、run_r416 runner
  + tests、R416 results 根（create-only）、ledger/feed/手稿收尾文件。
- 容量痕迹与分片日志非 claim-bearing（tmp/andes + memory/rounds/R416）。

## Cross-references

- CLM-1140 (R399)：父结论与锚源。
- CLM-1220/1225/1230 (R411/R413/R415)：A1/A2/A4 先序轮。
- `working/soft_spot_experiment_program.md` A3 + owner 决策。
- SKILL.md §2/§4。
