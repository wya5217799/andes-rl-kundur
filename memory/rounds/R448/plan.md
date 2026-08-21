---
round: R448
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: formal logD perturbation was ineffective because reset overwrote vsg_d0;
  frozen plan had no in-round recovery path, so the hashed CANARY-INVALID artifact
  is retained and repair moves to a successor round
superseded_note: null
---
# R448 plan — P1.1 比值灵敏度两分量分解 (candidate vs reference)

**Opened**: 2026-08-20
**Driver**: R447 验证了复响应导出 seam; 本轮补 P1.1 的 ∂ρ 分解, 判 relaxed
block 的 r_d 恶化由「候选闭环灵敏度」还是「参照分母」主导。
**Parent**: `CLM-1395` (R447 seam), `CLM-1230` (R415 relaxed 0.9712),
`CLM-1340` (R437 频带失谐 REFUTED), NOTE-0031。

## TL;DR

(完成后填)

## Methodology (冻结契约)

- 复用 R447 的 `run_r447_p1_complex_response.py` 闭环合成 (bandpass + local
  PI + headroom H)。
- **∂ρ 灵敏度**: 在 M/D 相对扰动点重线性化 — 建 env 于
  `V4Config(vsg_m0=200*(1±δ), vsg_d0=100)` 与 `V4Config(vsg_m0=200,
  vsg_d0=100*(1±δ))`, δ=0.01, 各得 SampledInputModel → 中心差分
  ∂A_d/∂log M, ∂A_d/∂log D。
- **链式法则**: ∂A_cl/∂ρ = ∂A_d/∂ρ (控制器/headroom 不依赖 ρ) 嵌入 A_cl
  的 A11 块 → ∂G/∂ρ = C (zI−A_cl)⁻¹ (∂A_cl/∂ρ) (zI−A_cl)⁻¹ B。
- **P1.1 分解**: candidate_term = 2Re⟨G_K,∂ρG_K⟩_W/‖G_K‖²;
  reference_term = −2Re⟨G_L,∂ρG_L⟩_W/‖G_L‖²; 频带 0.3-0.5Hz, W=差分能量。

## Theory intake

```
observable: P1.1 两分量 (candidate_term, reference_term), ρ∈{log M, log D}
  definition: 2Re⟨G_K,∂ρG_K⟩_W/‖G_K‖² 与 −2Re⟨G_L,∂ρG_L⟩_W/‖G_L‖² 在
    0.3-0.5Hz 加权和 (差分变换 T_d)
  source: results/research_loop/r448_p1_sensitivity/formal_analysis.json
  predicts: candidate 主导 → relaxed 失败源于候选灵敏度 (增益/相位类);
    reference 主导 → 分母参照能量变化 (归一化类); 同量级 → mixed
```

## Gate (判定树)

- 两分量 |term| 比 > 3 且方向匹配 r_d 恶化 → CANDIDATE-DOMINANT /
  REFERENCE-DOMINANT。
- 比值 <= 3 → MIXED。
- 线性化/闭环合成失败 → CANARY-INVALID。

## Formal launch contract

- `formal_entry`: `python scripts/run_r448_p1_sensitivity.py` (WSL)。
- `rehearsal_command`: 同 entry `--rehearse`。
- `wsl_python_processes`: 1; `native_threads_per_process`: 1。

## 资产保护契约

- 只读: src/, scripts/ 既有, results/, memory/。
- 新建: `scripts/run_r448_p1_sensitivity.py`; 结果写
  `results/research_loop/r448_p1_sensitivity/` (.sha256)。

## Cross-references

- CLM-1395, CLM-1230, CLM-1340; NOTE-0031; R447 runner。
