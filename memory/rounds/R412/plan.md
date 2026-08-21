---
round: R412
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'sealed runner defect: eig_gate crashed on init-divergent variants (out_Line_7_12/out_Line_9_15)
  instead of recording gate failure; 10/12 variants completed but the bank is incomplete;
  successor round re-runs A2 with the graceful-failure fix and a failure-path rehearsal'
superseded_note: null
---
# R412 plan — A2 拓扑变体鲁棒性 (topology-variant robustness)

**Opened**: 2026-08-17
**Driver**: soft-spot program A2（owner 授权创造模式整夜任务）：
N-1/阻抗变体是构网型器件评审标准轴；本轮把 R408/R409 验证过的 K=3.5
带通构造性结果放到 12 个冻结拓扑变体上复评，每个变体先过 CLM-0665
EIG 硬门。
**Parent**: CLM-1195 (R408 Q-ENTRY)、CLM-1210 (R409 HELDOUT-PASS)、
CLM-1220 (R411 A1)；`working/soft_spot_experiment_program.md` A2。

## TL;DR

Workload: `evidence`。Eval-only。冻结变体库 N=12（nominal + 6 线路开断
+ 5 联络线电抗 ×0.5/×1.5），每个变体 = 唯一拓扑因子；开断只经
`apply_line_outage()`（ANDES `Model.set`），阻抗经 `Line.set("x", …)`。
每变体先跑 CLM-0665 EIG 硬门（TDS.test_ok、exit_code=0、初始化残差、
有限谱、正实部 guard，全值记录），再在 R408 disclosed development bank
（8 配对探针 + 2 扰动 × 3 臂）上复评 K=3.5 带通 + zero/local 参照，阈值
= R409（r_d≤0.95、r_cross≤1.10、全 R379 guards）。nominal 变体 =
基案例锚：r_d/r_cross 必须在 1e-6 相对容差内复现 R408 值（0.938947 /
0.539791），否则 DRIFT 调查（creative：记录并继续）。完成判据 = 每变体
pass/fail 表 + 每 EIG 门值全记录的 hashed JSON。每变体 1 shard，12
shards；容量阶梯 rungs 1/2/4/8/12/16、32 任务/rung、5% 边际 + 半内存
规则后 seal 冻结预算。

## Methodology

### Mission boundary

- Outcome: `formal_analysis.json`（hashed）= per-variant EIG gate 全值 +
  per-variant r_d/r_cross/guards + pass/fail 表 + 基案例锚判定；随后
  feed/claim/verdict/LINE 一致关闭。
- Authority: soft-spot program A2（creative mode，pause 分支自动续走 +
  校准日志记录）。
- Permitted: 新 runner `scripts/run_r412_topology_robustness.py` + 测试、
  results 根 `results/research_loop/r412_topology_robustness/`
  （create-only）、复用共享分片驱动 `scripts/soft_spot_shard_driver.py`
  与 R408/R372 harness 导入（只读）、本轮 ledger/feed/手稿收尾。
- Forbidden: 改 R408/R409 runner/契约/gate_b3 模块/R379 资产；训练；
  换控制器/阈值/guard；变体库封存后改动；动 paper-cited 资产。
- Terminal: 12 variants × (eig_gate.json + records.json) 落盘 +
  formal_analysis.json 存在。

### 冻结协议 (frozen-first)

- TOPOLOGY_VARIANTS = nominal + out_Line_4/5/7/8/7_12/9_15 +
  x0p5/x1p5_Line_4、x0p5/x1p5_Line_7、x1p5_Line_7_12（协议常数，seal
  校验）。Line_2 排除（R305 正模先例）。
- 变异注入：`TopologyVariantEnvV4` 子类覆写 `_build_system`——super 构建
  后、任何潮流前施加唯一变异（outage: `apply_line_outage(ss, idx)`；
  impedance: `x ← x × factor` 经 `Line.set`）。reset 每次重建系统均自动
  复现变异。
- EIG 门：变体 env `reset(delta_u=None)` → `TDS.init()` → `EIG.run()` →
  `eig_validity_guard(positive_real_tolerance=1e-7)`；记录 tds_init/
  eig_return、readback（u==0 或 x 值）、init/residual/spectrum/
  positive_real_count/max_real 全值。
- Bank：R408 development bank 逐字复用（probe
  dev3_probe_bus15_minus_0p45 + disturbances dev3_disturbance_pq1_plus_0p65、
  dev3_disturbance_bus14_minus_0p55；8 配对探针 + 2 扰动 × 3 臂 = 30
  records/变体）；记录循环 = R408 `_run_job` 逐字语义 + 变体 env。
- 判定：每变体 r_d = candidate 差模能量 / local 同变体差模能量 ≤0.95；
  r_cross = candidate off-diag / local 同变体 off-diag ≤1.10；candidate
  与两参照 guards 全过 → variant PASS；否则 FAIL（如实记录，不重试）。
- 基案例锚（预注册）：nominal 变体 r_d/r_cross vs R408 formal 值
  （0.938947/0.539791）相对偏差 ≤1e-6 → BASE-ANCHOR-REPRODUCED；
  超差 → BASE-ANCHOR-DRIFT（记录，creative 继续）。nominal EIG 门失败
  = 基案例本身不可靠 → 记录并调查，不静默。
- 分片: shard_id = variant_id（12 shards）；resume 规则同 R411（缺失
  文件补写，已存在只校验）。

## Gate

- EIG 硬门（CLM-0665）: `eig_validity_guard().passed` 为 paper-facing
  前提；失败变体单独列报，其 endpoint 表照记但不计入稳健通过集。
- 端点阈值 = R409 冻结：r_d≤0.95、r_cross≤1.10（strict 0.95 附记）、
  全 R379 guards。
- 汇总：EIG 通过变体数与端点通过变体数分别报告；稳健性陈述 = 有界
  per-variant 表，无通过率阈值预注册（完成判据即表本身）。
- 预注册失败 flag: 任一变体 EIG 失败 / 端点失败 → 如实记录为 fail；
  nominal 锚漂移 → DRIFT 记录；TDS 失败 → 该记录 guard fail。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r412_topology_robustness.py --shards tmp/andes/r412_shards.json --workers 8 --round R412` (12 shards, driver = launcher, budget 内) + `... run_r412_topology_robustness.py classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r412_topology_robustness.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + nominal 变体 1 条完整记录（同 job loop）+ nominal EIG 门全路径（不创建 formal artifact）。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R412/capacity_evidence.json
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit。
- R408/R409 runner/结果、gate_b3 契约模块、R372 harness、bandpass
  控制器、能量端口 env、topology_status.py 全部只读。
- paper-cited 资产（base_env / andes_vsg_env_v4 / train.py /
  paper_grade_axes.py）只读；变异经 env 子类注入，不改 env 源码。
- 新文件仅: run_r412 runner + tests、R412 results 根（create-only）、
  ledger/feed/手稿收尾文件。
- 容量痕迹与分片日志非 claim-bearing（tmp/andes + memory/rounds/R412）。

## Cross-references

- CLM-1195 (R408)：基案例锚数值与 disclosed bank 来源。
- CLM-1210 (R409)：阈值与 guard 语义。
- CLM-1220 (R411)：A1 先序轮。
- `working/soft_spot_experiment_program.md` A2 + owner 决策。
- SKILL.md §2/§4；CLM-0665 拓扑/EIG 硬门。
