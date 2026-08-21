---
round: R414
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: seal-vs-runtime blocks comparison drifted on tuple/list JSON round-trip
  before the formal attempt was created; successor round re-runs with the canonical-form
  comparison and a regression test
superseded_note: null
---
# R414 plan — A4 能量端口额外未见 bank (energy-port extra unseen banks)

**Opened**: 2026-08-17
**Driver**: soft-spot program A4（owner 授权创造模式整夜任务）：
建设性结果的测试集多样性——今天只有一块公开开发 bank + 一块一次性
未见 bank；本轮冻结三块全新未见条件组合复评 K=3.5 控制器。
**Parent**: CLM-1195 (R408)、CLM-1210 (R409)、CLM-1225 (R413)；
`working/soft_spot_experiment_program.md` A4。

## TL;DR

Workload: `evidence`。Eval-only。冻结三块新未见 bank（
`src/andes_rl_kundur/evaluation/soft_spot_energy_port_banks.py`）：
a4_conditions_b = 新探针/扰动组合（名义机组）；a4_md_relaxed = M×0.85、
D×1.15 机组扰动；a4_md_stiff = M×1.15、D×0.85 机组扰动。每块 = 3 臂
（zero/local/bandpass_k3p5）× (8 配对探针 + 2 扰动) = 30 records；r_d /
r_cross 用 R409 冻结阈值（≤0.95 / ≤1.10，strict 0.95 附记）+ 全 R379
guards，candidate-vs-local 同块比值。串行估计 90 records × ~8-12 s ≈
12-18 min ≤ 20 min → 按 parallelism gate 走现有单进程 seam（不写并行
代码），封存预算 1 进程；容量锚 = 32 个串行代表性任务。完成判据 = 每块
r_d/r_cross + guards 的 hashed JSON。

## Methodology

### Mission boundary

- Outcome: `formal_analysis.json`（hashed）= per-block r_d/r_cross/guards
  + 通过块表 + ALL-BLOCKS-PASS/BLOCKS-FAIL 判定；随后 feed/claim/
  verdict/LINE 一致关闭。
- Authority: soft-spot program A4（creative mode）。
- Permitted: 新 runner `scripts/run_r414_energy_port_extra_banks.py` +
  测试、冻结 bank 模块、results 根
  `results/research_loop/r414_energy_port_extra_banks/`（create-only）、
  R408/R372 harness 导入（只读）、正常收尾。
- Forbidden: 改 R408/R409 runner/契约/gate_b3/R379 资产；训练；换
  控制器/阈值/guard；bank 封存后改动；动 paper-cited 资产。
- Terminal: 3 blocks × records.json 落盘 + formal_analysis.json 存在。

### 冻结协议 (frozen-first)

- BLOCKS 三块（模块常量，seal 校验）；每块唯一变化因子 = 一组未见条件
  （新扰动位置/强度，或一组 M/D 机组参数偏移）；K=3.5 带通、参照臂、
  估计器、阈值、guards 全部 R408/R409 资产只读。
- 记录循环 = R408 `_run_job` 逐字语义 + 块级 V4Config(vsg_m0,
  d0_per_agent)；50 步 × 0.2 s、seed 42、SOC 0.5、能量端口投影。
- 判定：r_d = candidate 差模能量 / local 同块差模能量 ≤0.95；r_cross =
  candidate off-diag / local 同块 off-diag ≤1.10；candidate 与两参照
  guards 全过 → block PASS；否则 FAIL（如实记录，不重试）。
- 执行 = 单进程串行 3 块；无分片驱动；预算 1 进程（saturate-or-skip）。

## Gate

- 阈值 = R409 冻结。汇总 = 通过块数/总块数 + 每块表；无通过率阈值
  预注册（完成判据即表本身）。
- 预注册失败 flag: 任一块 r_d/r_cross 超限或 guards 失败 → 如实记录为
  fail；TDS 失败 → 该记录 guard fail；bank 不完整 → 该块 invalid。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r414_energy_port_extra_banks.py execute` (单进程串行) + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r414_energy_port_extra_banks.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + 块 1 一条完整记录（同 job loop，不创建 formal artifact）。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R414/capacity_evidence.json
- host_process_budget: 1
- wsl_python_processes: 1
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit。
- R408/R409/R413 runner/结果、gate_b3 契约、R372 harness、bandpass
  控制器、能量端口 env、V4Config 全部只读（M/D 偏移经 config 参数注入，
  不改源码）。
- paper-cited 资产只读。新文件仅: run_r414 runner + tests、bank 模块、
  R414 results 根（create-only）、ledger/feed/手稿收尾文件。
- 容量痕迹非 claim-bearing（memory/rounds/R414）。

## Cross-references

- CLM-1195 (R408 Q-ENTRY)、CLM-1210 (R409 HELDOUT-PASS)、CLM-1225
  (R413 A2)；`working/soft_spot_experiment_program.md` A4 + owner 决策；
  SKILL.md §2/§4。
