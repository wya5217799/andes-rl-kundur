---
round: R449
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R449 plan — P1.1 D 扰动修复后的比值灵敏度分解

**Opened**: 2026-08-20
**Driver**: R448 的正式 `logD` 扰动被 `reset()` 用 `d0_per_agent` 覆盖，
产生已保留的 `CANARY-INVALID`；本轮用正确配置入口做单因素 successor。
**Parent**: R448 retained failure; CLM-1395 (R447 complex-response seam);
NOTE-0031; advisory P1.1。

## TL;DR

(完成后填)

## Methodology (冻结契约)

- 对象、控制器、headroom、频带、差分能量权重与 R448 不变。
- 唯一修复：D 扰动从无效 `vsg_d0` 改为
  `d0_per_agent=(100(1±δ), …, 100(1±δ))`; M 扰动仍为
  `vsg_m0=200(1±δ)`；δ=0.01，各点独立 reset、重线性化。
- 中心差分：`∂A_d/∂logM = [A_d(M(1+δ))-A_d(M(1-δ))]/(2δ)`，
  `∂A_d/∂logD = [A_d(D(1+δ))-A_d(D(1-δ))]/(2δ)`。
- 链式法则：`∂A_cl/∂ρ` 只把 `∂A_d/∂ρ` 嵌入闭环 A11；
  `∂G/∂ρ = C(zI-A_cl)^(-1)(∂A_cl/∂ρ)(zI-A_cl)^(-1)B`。
- 两项精确公式：
  `candidate_term = 2 Re <G_K,∂ρG_K>_W / ||G_K||_W^2`；
  `reference_term = -2 Re <G_L,∂ρG_L>_W / ||G_L||_W^2`；
  `ρ∈{logM,logD}`，在 0.3–0.5 Hz 聚合，W 为三维差分频率能量。

## Theory intake

```
observable: P1.1 两分量 (candidate_term, reference_term), rho in {logM, logD}
  definition: 上述两个无量纲对数灵敏度项在 0.3-0.5 Hz 差分能量上的加权和
  source: results/research_loop/r449_p1_sensitivity/formal_analysis.json
  predicts: abs 比 >3 且主导项方向与总导数一致 = 对应项主导；否则 mixed；
    D 扰动矩阵仍为零或闭环失败 = canary invalid
```

## Gate (判定树)

- 每个 ρ 的两项有限，`max|∂A_d/∂ρ| > 1e-12`；若两项绝对值比 `>3`，
  绝对值较大者为 `CANDIDATE-DOMINANT` 或 `REFERENCE-DOMINANT`。
- 两项有限且绝对值比 `<=3` → `MIXED`。
- `max|∂A_d/∂ρ| <=1e-12`、分母非正、非有限数或闭环合成失败
  → `CANARY-INVALID`；不重试，保留产物后终止本轮。

## Outcomes (pre-registered)

- `CANDIDATE-DOMINANT`: `max(|candidate|,|reference|)/min(...) > 3` 且
  `|candidate|>|reference|`。
- `REFERENCE-DOMINANT`: 同一比值 `>3` 且 `|reference|>|candidate|`。
- `MIXED`: 两项有限、非零且上述比值 `<=3`。
- `CANARY-INVALID`: Gate 所列任一完整性条件失败。

## Formal launch contract

- `formal_entry`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r449_p1_sensitivity.py analyse` (WSL)。
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r449_p1_sensitivity.py rehearse` (WSL)。
- `rehearsal_scope`: nominal 与 D±1% 三个真实 learner/object 构建点；不写 formal。
- `rehearsal_checks`: installed ANDES/case 由 scratch launcher 检查；R449
  输出不存在；D± 的 `max|∂A_d/∂logD|>1e-12`；状态维数一致。
- `capacity_evidence`: owner 决策把 <=20 min eval 归为单进程 seam；本轮是
  五个串行线性化点，无 shard、无训练，采用最小 rung 1。
- `host_process_budget`: 1；`other_reserved_processes`: 0。
- `wsl_python_processes`: 1；`native_threads_per_process`: 1。

## 资产保护契约

- 只读：R448 结果与 sidecar、R447 结果、`src/`、既有 `scripts/`、既有
  `results/`、`memory/`。
- 新建：`scripts/run_r449_p1_sensitivity.py`、定向测试、
  `results/research_loop/r449_p1_sensitivity/`；formal JSON create-only + sidecar。
- seal 后源码失败或 formal 创建前失败 → 本轮 aborted；禁止原轮补丁重跑。

## Cross-references

- R448; CLM-1395; NOTE-0031;
  `working/vsg_failure_math_advisory_20260820/IMPORT_NOTE.md`;
  `working/route_owner_decision_advisory_unresolved_2026-08-21.md`。
