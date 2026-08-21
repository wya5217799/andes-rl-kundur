---
round: R447
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R447 plan — P1 复响应导出 + 比值灵敏度分解 (relaxed block)

**Opened**: 2026-08-20
**Driver**: 咨询包 P1 的实证缺口 = 复响应 G_K/G_L 未测, 故增益/相位裕度因果
UNRESOLVED。本轮导出扰动通道的复响应并做 P1.1 比值灵敏度分解, 判「候选
灵敏度」还是「参照分母」主导 relaxed block 的 r_d 恶化。
**Parent**: NOTE-0031; `p1_p2_complex_response_design.md`;
CLM-1230 (R415 relaxed 0.9712), CLM-1340 (R437 频带失谐 REFUTED),
CLM-1390 (R446 B_{u,r}=0 结构+实测)。

## TL;DR

(完成后填)

## Methodology (冻结契约, seal 前不改)

- **对象**: Object B 能量端口 (bandpass K=3.5 vs local_feasibility_native 参照)。
  平衡点 = nominal 无扰动。
- **被控对象线性化**: `fold_descriptor(fx,fy,gx,gy)` → A_plant;
  `fold_input_columns` 折叠 PQ 扰动列 → B_dist; C_omega = 选 4 个 GENCLS
  omega 状态行; 离散化 dt=0.2s → A_d, B_d。
- **控制器 (解析, 不重推)**:
  - bandpass: `ring_bandpass_damping.prewarped_bandpass_coefficients`
    (F(s)=K·2ζωm·s/(s²+2ζωm·s+ωm²), ωm=2π·0.4, ζ=0.35, K=3.5, 4 边环)。
  - local 参照: `FeasibilityNativeLocalController` (4 独立 PI, kp_n/ki_n)。
- **闭环合成**: 采样数据 LTI 互联 (A_d,B_d,C_omega) ∘ 控制器状态空间 →
  A_cl,K, A_cl,L; G_K(jω)=C_omega(jωI-A_cl,K)⁻¹B_d, G_L 同理。
- **∂ρ 灵敏度**: ∂A_plant/∂M, ∂A_plant/∂D 用中心差分 (R446 FD seam) →
  ∂ρ G_K, ∂ρ G_L 经链式法则。
- **P1.1 分解**: ∂log r_d/∂ρ = 2Re⟨G_K,∂ρG_K⟩/‖G_K‖² − 2Re⟨G_L,∂ρG_L⟩/‖G_L‖²,
  频带 0.3–0.5 Hz, W = 差分能量加权。

## Theory intake (机制预测可观测清单)

```
observable: P1.1 两分量 (candidate_term, reference_term)
  definition: 2Re⟨G_K,∂ρG_K⟩_W/‖G_K‖² 与 −2Re⟨G_L,∂ρG_L⟩_W/‖G_L‖² 在
    0.3-0.5Hz 的加权和, ρ∈{M,D}, 单位 1/(p.u. M 或 D)
  source: results/research_loop/r447_p1_complex_response/formal_analysis.json
  predicts: candidate_term 主导 → relaxed 失败源于候选闭环灵敏度变化
    (增益/相位类机制); reference_term 主导 → 分母参照能量变化 (归一化
    机制); 两分量同量级 → mixed dominance
```

## Gate (判定树)

- 频带能量比 `e_k/e_l` 有限且在合理量级 (与 R408 实测 r_d≈0.938 同量级,
  允许 ~10% 线性化/平坦加权偏差) → `CLOSED-LOOP-COMPOSITION-VALIDATED`。
- `e_k/e_l` 非有限或量级错 (差一个数量级以上) → `CANARY-INVALID`。
- P1.1 的 ∂ρ 两分量分解 (CANDIDATE/REFERENCE-DOMINANT) 是本轮的 follow-up
  (需在 M/D 扰动点重建源模型), 不在本轮密封范围。

## Outcomes (pre-registered)

- `CLOSED-LOOP-COMPOSITION-VALIDATED`: `e_k/e_l` 有限且 ∈ (0.5, 1.5)
  (R408 r_d=0.938 的 ±50% 窗口)。
- `CANARY-INVALID`: `e_k/e_l` 非有限或 ∉ (0.5, 1.5)。

## Formal launch contract

- `formal_entry`: `python scripts/run_r447_p1_complex_response.py` (WSL)。
- `rehearsal_command`: 同 entry `--rehearse` (只做对象线性化 + 单控制器
  闭环合成, 不写 formal)。
- `wsl_python_processes`: 1; `native_threads_per_process`: 1。
- 无训练; 单进程测量 (~分钟)。

## 资产保护契约

- 只读: src/ 全部, scripts/ 既有, results/ 既有, memory/。
- 新建: `scripts/run_r447_p1_complex_response.py`; 结果写
  `results/research_loop/r447_p1_complex_response/` (.sha256)。

## Cross-references

- NOTE-0031; `vsg_failure_math_advisory_20260820/IMPORT_NOTE.md`;
  `p1_p2_complex_response_design.md`; CLM-1230, CLM-1340, CLM-1390。
