---
round: R446
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R446 plan — P3 DAE 一阶权威 B_{u,r} 有限差分测量 (Object A)

**Opened**: 2026-08-20
**Driver**: 咨询包 P3 留「实际 ANDES 对象 B_{u,r} 未测」为未决; 离线代码分析
(`tmp/yang_md_decoupling_marl/p3_dae_authority_code_analysis.md`) 预测结构零。
本轮把该结构预测做成密封数值测量 — 若 ≈0 则 P3.2 从「条件引理」升为
「对实现对象的实测贡献」。
**Parent**: NOTE-0031; `route_owner_decision_advisory_unresolved_2026-08-21.md`;
CLM-1340 (R437 频带失谐 REFUTED), theory_audit_bundle IMPORT_NOTE (B_{u,r} 未识别).

## TL;DR

(完成后填)

## Methodology (冻结契约, seal 前不改)

- **对象**: Object A — 4 VSG GENCLS (`vsg_idx`), `andes_vsg_env_v4` +
  `base_env` 冻结实现, ANDES 2.0.0, kundur_full.xlsx。
- **平衡点**: `reset()` 后跑 TDS 到 0.5s 同步功率平衡 (ω_i=1, tm=te),
  冻结 `x* = dae.x`, `y* = dae.y`, 读 `fy`, `gy` (dense), 记 `g_y` 条件数。
- **输入列 u**: 8 列 = {ΔM_i, ΔD_i, i=1..4}。基准 M/D = vsg 平衡值。
- **residual_callback**: 在冻结 x*,y* 下 `ss.GENCLS.set("M"/"D", vsg_idx,
  base ± h, attr='v')` → `TDS.fg_update` → 读 `dae.f`, `dae.g` (flat)。
  `set("M")` 会改 `dae.Tf`(M 是 t_const), 记录并在每列后恢复 Tf。
- **差分**: 复用 `finite_difference_input_jacobians` (model_first_contract.py:375,
  central, 几何 h 序列) → f_u, g_u (各 8 列, 含 midpoint_ratios)。
- **折叠**: 复用 `fold_input_columns` (r405_linearization.py:39) → B_{u,r}
  (n_x × 8)。
- **噪声界**: 每列在几何 h 序列上求收敛性 (中心差稳定), 记录
  midpoint_ratios; materiality 阈值 = 本测量的 h-收敛残差上界。

## Theory intake (机制预测可观测清单)

外部解答 + 离线分析预测「平衡点 B_{u,r}=0」。本清单登记裁决所需可观测:

```
observable: B_{u,r} 各列 (DeltaM_i, DeltaD_i, i=1..4)
  definition: fold_input_columns(f_u, g_u, f_y, g_y) 的 8 个输出列, 单位
    与 f 残差同量纲; 逐列报 max |entry| 与 2-范数
  source: results/research_loop/r446_md_authority_fd/formal_analysis.json
  predicts: 8 列均 <= 噪声界 (SUPPORTED: 平衡点 B_{u,r}=0); 任一列超
    噪声界且 h-收敛 (REFUTED: 存在一阶权威通道)
```

## Gate (判定树)

- 全部 8 列 |B_{u,r}| <= 噪声界 且 h-序列收敛 且 g_y 条件数健康
  → `ZERO-FIRST-ORDER-AUTHORITY` (支持 P3.2 结构零; 升为实测贡献)。
- 任一列超噪声界且稳定 → `NONZERO-FIRST-ORDER-AUTHORITY` (REFUTED;
  停 claim gate 问 owner, 因它推翻 ODE 引理)。
- g_y 奇异 / fg_update 失败 / 平衡点不满足 (|ω-1| 或 |f_ω| 超阈值)
  → `CANARY-INVALID` (记执行失败, 不判科学结论)。

## Outcomes (pre-registered)

- `ZERO-FIRST-ORDER-AUTHORITY`: 8 列每列 max|B_{u,r}| <= 1e-6 且
  h-序列收敛残差 <= 1e-6 且 g_y 条件数 < 1e10 且 |ω-1| <= 1e-6 且
  max|f_ω| <= 1e-6。
- `NONZERO-FIRST-ORDER-AUTHORITY`: 任一列 max|B_{u,r}| > 1e-6 且该列
  h-序列稳定 (相邻 h 估计差 <= 1e-6)。
- `CANARY-INVALID`: 平衡点门 (|ω-1| / |f_ω|) 或 g_y 条件数或 fg_update
  失败。materiality=1e-6 是结构零 (solver 噪声 ~1e-9) 与真实通道 (~1e-2+)
  之间的预注册分界。

## Formal launch contract

- `formal_entry`: `python scripts/run_r446_md_authority_fd.py` (经
  `scripts/andes_scratch.py` 启, WSL)。
- `rehearsal_command`: 同 entry, `--rehearse` — 跑 1 列 (DeltaM_1) 的
  h=1e-3 单点, 验证 residual_callback 可读 + Tf 恢复 + g_y 可逆。
- `rehearsal_scope`: 1 平衡点 + 1 输入列 + 1 h 值, 不写 formal result。
- `rehearsal_checks`: fg_update 成功; f/g flat 形状稳定; g_y 条件数
  < 1e10; midpoint_ratio 有限。
- `wsl_python_processes`: 1 (单进程, 无 shard); `native_threads_per_process`: 1。
- `host_process_budget`: 单进程测量 (~分钟), 无训练; 无并发轮。
  `other_reserved_processes`: 0。

## 资产保护契约

- 只读: `src/andes_rl_kundur/` 全部, `scripts/` 既有 runner, `results/`
  既有, `memory/` 全部。
- 新建: `scripts/run_r446_md_authority_fd.py` (新 runner), 结果写
  `results/research_loop/r446_md_authority_fd/` (逐文件 .sha256)。

## Cross-references

- NOTE-0031; `vsg_failure_math_advisory_20260820/IMPORT_NOTE.md`;
  `tmp/yang_md_decoupling_marl/p3_dae_authority_code_analysis.md`;
  theory_audit_bundle IMPORT_NOTE (B_{u,r} 未识别 → 本轮补上)。
