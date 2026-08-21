---
round: R415
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds:
- R414
superseded_by_round: null
abort_reason: null
superseded_note: 'R414 (same A4 protocol) aborted before its formal attempt: the seal-vs-runtime
  blocks comparison drifted on the tuple/list JSON round-trip. This round re-runs
  the identical frozen protocol with the canonical-form comparison and its regression
  test.'
---
# R415 plan — A4 能量端口额外未见 bank（R414 后继，同协议）

**Opened**: 2026-08-17
**Driver**: soft-spot program A4 后继轮。R414 以 aborted 终止（seal 块表
tuple/list JSON 往返比较缺陷，发生在 formal attempt 创建前）；本轮回跑
同一冻结协议，runner 带 canonical-form 比较修复 + 回归测试。
**Parent**: CLM-1195 (R408)、CLM-1210 (R409)、CLM-1225 (R413)；R414
abort 记录（校准日志 2026-08-17）。

## TL;DR

Workload: `evidence`。Eval-only。协议与 R414 逐字相同（见其 plan，本
文件只声明增量）：冻结三块新未见 bank（a4_conditions_b 新条件组合；
a4_md_relaxed M×0.85/D×1.15；a4_md_stiff M×1.15/D×0.85），每块 3 臂 ×
10 records = 30，r_d/r_cross 用 R409 冻结阈值 + 全 R379 guards，
candidate-vs-local 同块比值。串行估计 ≈12-18 min ≤ 20 min → 单进程
seam，封存预算 1 进程。**修复增量**：`_blocks_canonical()` 单一
JSON 往返规范形式，prepare 与 load_seal 同源比较；回归测试锁定往返
相等与 tuple 差异成因。

## Methodology

### Mission boundary

- Outcome: `formal_analysis.json`（hashed）= per-block r_d/r_cross/guards
  + 通过块表 + ALL-BLOCKS-PASS/BLOCKS-FAIL 判定；随后 feed/claim/
  verdict/LINE 一致关闭。
- Authority: soft-spot program A4（creative mode）；R414 abort 后按
  creative 条款自动续走后继轮（校准日志已记）。
- Permitted: 新 runner `scripts/run_r415_energy_port_extra_banks.py` +
  测试（`tests/test_run_r415_energy_port_extra_banks.py`）、results 根
  `results/research_loop/r415_energy_port_extra_banks/`（create-only）、
  R408/R372 harness 导入（只读）、正常收尾。
- Forbidden: 改 R408/R409 runner/契约/gate_b3/R379 资产；训练；换
  控制器/阈值/guard；bank 封存后改动；动 paper-cited 资产；读取 R414
  放弃产物作为证据（全新执行）。
- Terminal: 3 blocks × records.json 落盘 + formal_analysis.json 存在。

### 冻结协议 (frozen-first)

- 与 R414 逐字相同：BLOCKS 三块（模块常量，seal 校验）、R408 记录循环
  + 块级 V4Config、R409 阈值判定、串行执行、预算 1 进程。
- seal 比较修复：`_blocks_canonical()` = json.dumps/loads 往返后的块表；
  prepare 写入该形式，load_seal 与同一形式比较。

## Gate

- 与 R414 相同（R409 阈值 + 有界每块表 + 预注册失败 flag）。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r415_energy_port_extra_banks.py execute` (单进程串行) + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r415_energy_port_extra_banks.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + 块 1 一条完整记录（同 job loop，不创建 formal artifact）。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R415/capacity_evidence.json
- host_process_budget: 1
- wsl_python_processes: 1
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 与 R414 相同。R414 结果根（aborted，无产物）与 R414 的
  formal_seal.json 保留为审计记录。

## Cross-references

- CLM-1195 (R408)、CLM-1210 (R409)、CLM-1225 (R413)；R414 plan（协议
  真源）+ R414 abort reason；`working/soft_spot_experiment_program.md`
  A4 + owner 决策；SKILL.md §2/§4。
