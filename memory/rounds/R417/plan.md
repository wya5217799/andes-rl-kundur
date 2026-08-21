---
round: R417
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R417 plan — 反馈环：K=4.0 在 A4 三块未见 bank 上的广度表

**Opened**: 2026-08-17
**Driver**: 反馈环第 1 轮（owner 指示不间断机制）。R415 发现冻结 K=3.5
在轻惯量/重阻尼块差 2.2% 未达 r_d 阈值；R408 同时披露了第二个进入目标
区的候选 K=4.0（dev r_d=0.911541, r_cross=0.515282，比 K=3.5 更强）。
本轮把 K=4.0 首次用到 R415 同一冻结三块未见 bank 上，产出预注册的
双增益边界表——不调参、不从这三块做任何选择。
**Parent**: CLM-1230 (R415 边界)、CLM-1195 (R408 双 Q-ENTRY 披露)；
反馈环目标（本次会话 goal）。

## TL;DR

Workload: `evidence`。Eval-only。协议 = R415 逐字复用（同一三块冻结
bank、同阈值 r_d≤0.95 / r_cross≤1.10、同 guards、同串行 seam），唯一
变化因子 = 候选臂 K=3.5 → K=4.0（R408 已披露的 dev 候选，非本 bank 上
的选择）。预注册解释：三块 bank 对 K=4.0 是首次使用；结果只进表，不进
任何选择逻辑；若 K=4.0 三块全过 → 论文可声称"两个已披露增益共同覆盖
三块未见条件（轻惯量边界随增益移动）"；若仍有失败 → 如实报告边界表。
串行估计 ≈12-18 min ≤ 20 min → 单进程 seam，预算 1 进程。

## Methodology

### Mission boundary

- Outcome: `formal_analysis.json`（hashed）= per-block r_d/r_cross/guards
  + 通过块表 + ALL-BLOCKS-PASS/BLOCKS-FAIL；随后 feed/claim/verdict/
  LINE 一致关闭。
- Authority: 反馈环（owner 2026-08-17 指示；creative 条款适用）。
- Permitted: 新 runner `scripts/run_r417_energy_port_banks_k4.py` +
  测试、results 根 `results/research_loop/r417_energy_port_banks_k4/`
  （create-only）、R415 冻结 bank 模块与 R408/R372 harness 导入（只读）、
  正常收尾。
- Forbidden: 改 bank 模块/R415 资产/阈值/guard；训练；任何以本 bank
  结果为基础的增益选择；动 paper-cited 资产。
- Terminal: 3 blocks × records.json 落盘 + formal_analysis.json 存在。

### 冻结协议 (frozen-first)

- 候选臂 = `bandpass_k4`（R408 冻结结构 K=4.0，clip ±0.70，同
  feasibility-native 端口映射）；参照臂 zero/local 不变。
- BLOCKS 三块、V4Config 扰动、记录循环、判定全部 R415 逐字。

## Gate

- 阈值 = R409 冻结。汇总 = K=4.0 的每块表 + 与 R415 的 K=3.5 表并列
  （并列表为派生视图，不改变任何选择）。预注册失败 flag 同 R415。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r417_energy_port_banks_k4.py execute` (单进程串行) + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r417_energy_port_banks_k4.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + 块 1 一条完整记录（同 job loop，不创建 formal artifact）。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R417/capacity_evidence.json
- host_process_budget: 1
- wsl_python_processes: 1
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit。
- R415 runner/结果/bank 模块、R408/R409 资产、bandpass 控制器、V4 env
  全部只读。
- paper-cited 资产只读。新文件仅: run_r417 runner + tests、R417 results
  根（create-only）、ledger/feed/手稿收尾文件。

## Cross-references

- CLM-1230 (R415)：边界来源与 K=3.5 对照表。
- CLM-1195 (R408)：K=4.0 披露记录。
- `working/soft_spot_experiment_program.md`（A4 已完成）；反馈环记录进
  `working/gate_calibration_log.md`。
