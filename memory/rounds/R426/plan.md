---
round: R426
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-18'
closed: '2026-08-18'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R426 plan — B2 五种子扩展（R410 修复束，与 R425 并发）

**Opened**: 2026-08-18
**Driver**: owner 订单 2026-08-18（对比层统计功效升级：3 种子中位对比功率
偏低，排队程序 B2 值得跑；选 R410 修复束 = 论文头版负对比 −78.43% 所在束）。
Program 条目：`working/soft_spot_experiment_program.md` §B2；设计文档：
`tmp/yang_md_decoupling_marl/b2_five_seed_runner_design.md`。位复现依据：
R421 B3 证明 R410 learner 路径在当前字节（learner sha bd924733fe4d71ac，
与 R421 seal 一致）下重跑位一致（R410-BIT-IDENTICAL）→ 401/402/403 复用
存储的 R410 checkpoint，仅 1 个活体门跑（message|401）+ 6 组新训
（404/405 × 3 臂）。**Concurrency**: 与 R425 并发（owner 常设授权）——本
plan 声明 R425 的 17 进程（16 worker + 1 driver）为 reserved share；阶梯
在 R425 活负载下重测、免 5% 边际链、取最大内存安全 rung；总内存记账
（本任务活训练 RSS + 17×950 MiB + 3 GiB 底 ≤ WSL MemTotal）。
**Parent**: CLM-1215 (R410)；CLM-1285 (R424)；program B2 条目；R421 B3
位复现证明。

## TL;DR

Workload: `evidence`。Training + evaluation-only reuse。目标 = R410 修复束
5 种子中位/离散表（hashed JSON, reporting layer）+ 冻结分类树判定（3 种子
不动, 树不碰）。401/402/403 复用存储 R410 checkpoint（只读, sha 记录）；
message|401 活体门跑（fresh final.pt sha == 存储 R410 sha = 位复现确认）；
404/405 新训 6 组（同束同预算同守卫）。评估 15 arm-seed × 4 剖面 +
确定性参照；5 种子表中位/min/max 与 3 种子 verdict 分开登记。DRIFT 分支
（门跑不匹配）= 停、报告、owner 决定（重训 5 组或换束）。预算：
并发阶梯（R425 负载下）封存；7 分片单波；串行 evaluate + classify。

## Methodology

### Mission boundary

- Outcome: 7 manifest（含 message|401 门跑 + b2_gate 读数）+ 60 学习评估
  record + 4 确定性 record + formal_analysis（冻结 3 种子分类 +
  b2_gate + b2_five_seed_table）+ feed/claim/verdict/LINE 一致关闭。
- Authority: owner 订单 2026-08-18 + program B2 + 并发授权（CLAUDE.md
  并行预算条目）。
- Permitted: 新 runner `scripts/run_r426_b2_five_seed.py` + 测试、results
  根 `results/research_loop/r426_b2_five_seed/`（create-only）、存储 R410
  checkpoint 只读引用、正常收尾。
- Forbidden: 改 cd_matd3.py / 任何 R410/R419-R425 资产字节；改 R410 契约
  或冻结分类树；训练期访问评估剖面；动 paper-cited 资产。
- Terminal: formal_analysis.json 存在且 7 manifest + 64 评估文件齐全 +
  b2_gate + b2_five_seed_table 齐备。

### 冻结协议 (frozen-first)

- 基座 = R410 修复束逐字（7 槽观测、掩码语义、种子 401/402/403、43,200
  步/组、超参/奖励/估计器/守卫/checkpoint 同 R410 seal 契约）。
- 位复现门：message|401 新训一跑，final.pt sha256 == 存储 R410
  message|401 checkpoint sha（不匹配 = b2_gate_matches_r410=false →
  DRIFT 分支：停、报告、owner 决定；绝不静默重训或改判）。
- 复用：401/402/403 评估读存储 R410 checkpoint（只读，record 记 sha）；
  404/405 读本轮新训 checkpoint。
- 5 种子表：per arm per endpoint 的 median/min/max（与 R410 同款 per-seed
  聚合），登记 `formal_analysis.json#/b2_five_seed_table`；冻结分类树
  verdict 只跑契约 3 种子（树不碰，两处分开登记）。
- 锚：确定性参照评估逐字；存储 R410 checkpoint sidecar 逐一验证。
- 读数：critic-loss 趋势 + 限速诊断（R410 同款）。

## Gate

- 门跑：message|401 fresh sha == 存储 R410 sha = BIT-REPRO-CONFIRMED；
  不等 = DRIFT → 停 + 报告（预注册）。
- 分类树 = 冻结 classify_canary（3 种子, 树不碰）。
- Outcomes: 冻结树 CANARY-PASS/FAIL/INVALID 照常；5 种子表 = reporting
  layer（不参与树的判定分支）；消息对比的中位/离散对 R410 3 种子
  −78.43%/−26.74% 对照报告。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r426_b2_five_seed.py --shards tmp/andes/r426_train_shards.json --workers <ladder> --round R426` (7 train shards) + `... run_r426_b2_five_seed.py evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r426_b2_five_seed.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + snapshot + 每臂 1 步真实增广 rollout + replay store + learner update 演练 + checkpoint-source 复用 seam（401 存储路径存在且 sidecar 验证 / 404 新路径预缺席）+ 门比较逻辑 sanity（保存→重载 sha 相等、相同字节 copies 判 matches）+ R410 奖励路径。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, stored_checkpoint_sidecars
- capacity_evidence: memory/rounds/R426/capacity_evidence.json
- host_process_budget: 26
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 17

## 资产保护契约

- R410/R419-R425 资产只读（对照与锚只读引用）；cd_matd3.py 字节不动；
  paper-cited 资产只读；dirty worktree 保留。
- 新文件仅: run_r426 runner + tests、R426 results 根（create-only）、
  ledger/feed/手稿收尾文件。

## Cross-references

- CLM-1215 (R410)；CLM-1285 (R424 符号缺陷)；program B2 条目；R421 B3。
- `tmp/yang_md_decoupling_marl/b2_five_seed_runner_design.md`。
- `working/gate_calibration_log.md`（owner 并发/短预算/研究目的指令）。
