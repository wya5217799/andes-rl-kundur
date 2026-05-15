# R20 — Reward Paradox Confirmatory Probe (verdict)

**Date**: 2026-05-07
**Phase**: ANDES V4.1 anti-paper root cause — Hypothesis A (paper Eq.14 trivial optimum on 4-agent ring)
**Wall**: ~6 min (1500 ANDES TDS calls = 6 scenarios × 50 steps × 5 substeps)
**Status**: ⚠ **PARTIAL** — Verdict gate (硬 AND 阈值) 判 PARADOX_NOT_CONFIRMED, 但 3-clause 中 A∧B 全过, C 部分过. **Hypothesis A 主框架部分支持, 但 trivial optimum 不是"互抵=0"而是"边界饱和=constant"**.
**Probe script**: `scripts/research_loop/r20_reward_settled_audit.py`
**Output**: `results/research_loop/r20_reward_settled.json`
**Log**: `logs/r20_andes.log`
**前置 handoff**: `quality_reports/handoff/2026-05-07_andes_v41_reward_paradox_handoff.md`

---

## TL;DR (1 段)

V4.1 ckpt s44 best 在 LS1/LS2 settled phase (last 30 step, t > 4s) 测出: (i) **agents 没拉回 50 Hz**, max\|Δω\| ≈ 0.16-0.20 Hz, max_df 0.21-0.22 (比 no_control 0.17-0.19 显著差, anti-paper); (ii) **r_f local-sync 接近达成**, settled r_f ≈ -0.34 ~ -0.47 (PHI_F=100 scale 下接近 0); (iii) **ΔD 4 agents 全军坐落在 mid-range attractor ≈ -39**, **不是 boundary 饱和** (V4 DD_MIN=-200, ΔD=-39 远离边界; D=D₀+ΔD=61 远离 D_MIN_PHYSICAL=10); (iv) **ΔH 部分互抵但非对称**, LS1 [-15, -28, **+46**, -15] (1 个 +H 三个 -H), LS2 全 -H 偏 (mean=-9.3). **Trivial optimum 真实形态 = sync 到非零 ω + ΔD 全军一致 mid-range attractor (~-39) + ΔH 非对称偏移**, 不是 hypothesis 预测的 "mean²=0 互抵". 推断 mechanism: V4.1 R18 把 PHI_D 从 1.0 rescale 到 0.0056 防爆炸 → r_d 弱惩罚 → SAC 把 ΔD 当近 free dim 输出, 收敛到一致 mid-range. PHI_ABS=50 inference replay 同 ckpt: r_f 翻 5.9× 但 policy 不变, 物理量级与 phi0 完全一致 → **必须 retrain 才能验**. handoff Phase 2 (50 ep PHI_ABS=50 retrain) 仍值得做, 但要警觉真正瓶颈可能在 PHI_D 而不是 PHI_ABS.

---

## Probe 设计 (handoff Section 3)

### 输入
- ckpt: `results/v4_1_paper_s44/agent_{0..3}_best.pt` (V4.1 200 ep, anti-paper 代表)
- env: `env/andes/andes_vsg_env_v4.py` V4.1 strict (PHI_ABS=0 default)
- env_patch: `_patch_phi_abs(value)` 改 PHI_ABS for inference (不改 policy)
- 6 scenarios: baseline_LS{1,2} + trained_phi0_LS{1,2} + trained_phi50_LS{1,2}
- N_STEPS=50, SETTLED_TAIL=30, deterministic policy, EVAL_SEED=42

### Verdict gate (hard AND, paradox_confirmed)
- A: `settled max|Δω| ≥ 0.05 Hz`           ← agents NOT pulling to 50Hz
- B: `|settled r_f| < 0.5` (PHI_F=100 scale) ← local sync achieved
- C: `|settled mean(ΔH)| < 5 ∧ std(ΔH) > 30` ← agents 互抵 (signs cancel)

---

## 实测结果

### Settled-phase 表 (last 30 of 50 steps)

| scenario | max_df | max\|dω\| | r_f | r_h | r_d | mean(ΔH) | std(ΔH) | mean(ΔD) | gates |
|---|---|---|---|---|---|---|---|---|---|
| baseline_LS1 (no SAC) | 0.189 | 0.145 | -0.11 | +0.00 | +0.00 | +0.00 | 0.0 | +0.00 | TTF |
| baseline_LS2 (no SAC) | 0.168 | 0.124 | -0.15 | +0.00 | +0.00 | +0.00 | 0.0 | +0.00 | TTF |
| trained_phi0_LS1 | 0.223 | 0.198 | -0.47 | -0.29 | -34.25 | **-3.20** | **28.8** | **-38.93** | **TTF** |
| trained_phi0_LS2 | 0.214 | 0.162 | -0.34 | -1.97 | -34.30 | **-9.29** | **9.6** | **-39.05** | **TTF** |
| trained_phi50_LS1 | 0.223 | 0.198 | -2.76 | -0.29 | -34.25 | -3.20 | 28.8 | -38.93 | TFF |
| trained_phi50_LS2 | 0.214 | 0.162 | -2.17 | -1.97 | -34.30 | -9.29 | 9.6 | -39.05 | TFF |

> phi50 行物理量与 phi0 完全相同 (r_f 翻 5.9× 因 inference 改了 reward 计算公式但 policy 不变). 这是 inference-time replay 不是 retrain.

### Per-agent settled mean (4 agents)

```
trained_phi0_LS1:
  ΔH = [-15.62, -27.73, +45.91, -15.35]   sum=-12.79
  ΔD = [-41.28, -35.06, -40.36, -39.03]   sum=-155.73   ← 4 agents 同坐 mid-range attractor ≈-39 (V4 DD_MIN=-200, NOT boundary)
trained_phi0_LS2:
  ΔH = [ -6.39, -19.48,  +5.06, -16.33]   sum=-37.15
  ΔD = [-45.33, -32.96, -47.69, -30.23]   sum=-156.21   ← 同上, 一致 attractor
```

---

## Verdict gates 解读

| Gate | LS1 | LS2 | 含义 |
|---|---|---|---|
| **A** (settled \|dω\| ≥ 0.05 Hz) | ✓ True | ✓ True | agents 没拉回 50 Hz, 漂浮稳态 0.16-0.20 Hz — **支持 hypothesis** |
| **B** (\|r_f\| < 0.5) | ✓ True | ✓ True | local sync 接近达成 (r_f -0.34 ~ -0.47) — **支持 hypothesis** |
| **C** (\|mean ΔH\|<5 ∧ std>30) | ✗ False (LS1: mean OK std 28.8 临界 30; LS2: mean=-9.3 std=9.6 全失败) | ✗ False | ΔH **不是对称互抵**, 是 LS1 1×强+H + 3×-H, LS2 全-H 偏 — **推翻 hypothesis 的"互抵"具体形式** |

---

## Hypothesis 修正 (R20 后真实图景)

### 原 hypothesis A (handoff)
- r_f=0 by sync (any ω) ∧ r_h=0 by ΔH 互抵 ∧ r_d=0 by ΔD 互抵
- 4 agents 对称分布 (2 +X, 2 -X), mean²=0

### R20 实测推翻的部分
- ΔD **不互抵**, 4 agents 全军坐 mid-range attractor ≈ -39 (LS1 std=2.8, LS2 std=8.3 — 4 agents **一致**)
- ΔH **非对称互抵**, mean ≠ 0
- 关键: **V4 DD_MIN = -200, ΔD = -39 远不是边界**; D=61 远不是 D_MIN_PHYSICAL=10 → **不是 action space boundary 局部最优**
- mean(ΔD)² = (-39)² ≈ 1521, 但 PHI_D=0.0056 → r_d 系数 ≈ -8.5 vs 实测 -34 (差 4×, 可能 r_d 公式含其他项, 待查 `env/andes/andes_vsg_env_v4.py::_compute_rewards`)

### 修正后的真实 trivial optimum
**Mid-range attractor, NOT boundary saturation**:
- V4.1 R18 PHI_D rescale 1.0 → 0.0056 (防 V4.0 PHI_D=1 ep75 爆炸) 让 ΔD 维度近 free
- SAC 在 ΔD 维度做 max-entropy 输出, 但偏移到 ω 频率扰动后的 attractor (-39 而非 0)
- 4 agents 在该 attractor 上一致 (集体偏移 ≠ 互抵)
- gradient 仍存在 (不是边界 plateau), 但被 r_f sync 项 dominant 拉到这个稳定点
- 这跟 hypothesis 框架"sync + 偷懒"兼容, 但**具体 mechanism = PHI_D 弱化后的 collective drift attractor**, 不是 mean²=0 也不是 boundary saturation

### Paper Yang 2023 怎么训出来的? (修正)
原 handoff 列了 3 种可能 (PHI_ABS>0 / r_f abs deviation / shaping). R20 后修正:
4. **paper PHI_D 实际值 ≠ 1.0 nominal**: V4.0 paper-strict (PHI_D=1) 已知 ep75 爆炸; V4.1 R18 rescale 0.0056 → mid-range attractor anti-paper. paper 中段值 (PHI_D ≈ 0.05?) 没记录, 是隐藏 free param.
5. **paper Sec.IV-B action range [-100,+300]/[-200,+600] 是 V4 已 calibrated**: 选项 2 (action range 校准) 已经做过, **不是当前 anti-paper root cause**.

---

## handoff 决策矩阵 vs R20 实测

| handoff verdict | R20 实测对应 |
|---|---|
| PARADOX_CONFIRMED (3/3) → 跑 V4.2 PHI_ABS=50 retrain | 不是 |
| PARADOX_PARTIAL (2/3) → 暂无明确路径 | **这个** |
| PARADOX_REJECTED (≤1/3) → 写 appendix B + 切 Simulink | 不是 |

PARTIAL 状态在原矩阵下没明示后续, 需新决策。

---

## 后续选项 (按 ROI 排序)

### 选项 1: handoff Phase 2 PHI_ABS=50 retrain (50 ep × 1 seed, ≤15 min)
- **原 plan**, R20 PARTIAL 状态下仍值得做
- **风险**: ΔD boundary saturation 可能不是 PHI_ABS 能破的, 是 action range 问题
- **价值**: cheap, 一次小训给绝对答案 (retrain 后 settled ΔD 全饱和 vs 不饱和)
- **gate**: ckpt @ ep 50 LS1 max\|Δf\| < 0.183 (no_control)

### ~~选项 2: action range 校准~~ (R20 修正后作废)
- V4 (`AndesMultiVSGEnvV4`) 已经把 DM_MIN/MAX 和 DD_MIN/MAX 改成 paper Sec.IV-B [-200,+600]
- 当前 ckpt s44 用的就是 [-200,+600], ΔD=-39 不是 boundary saturation
- 此选项**已经做过, 不是当前 anti-paper root cause**

### 选项 2' (R20 修正后新增): PHI_D rescale 部分撤回
- V4.1 PHI_D=0.0056 (R18 设) → 改 PHI_D=0.05 ~ 0.5 (中间值, 防爆同时给 ΔD 项一定权重)
- 50 ep retrain, ≤15 min
- **风险**: 已知 PHI_D=1 V4.0 STOP @ ep75; 中间值会不会还是爆需测
- **价值**: 直接破 mid-range attractor (强化 r_d gradient 拉 ΔD 回 0)

### 选项 2'' (R20 修正后新增): PHI_ABS curriculum
- 训练前 20 ep 用 PHI_ABS=200 (强拉回 50Hz), ep 20-50 衰减到 0
- 50 ep, ≤25 min (含改 train loop)
- **价值**: 用 ω→0 力把 attractor 推出 mid-range zone
- **风险**: 50 ep 不够 SAC 收敛, 需要 100 ep+

### 选项 3': 选项 1 + 2' 并行 (2 个 ANDES TDS, 不卡 MATLAB)
- 30 min 内拿到 2 个 retrain verdict, ROI 最高
- 按 feedback_optimal_workflow_default.md 默认并行原则

### 选项 4: 切 Simulink-discrete 主线 (handoff fallback)
- 写 appendix B 跨平台 negative finding
- ANDES 6 hr sunk + R20 PARTIAL → 撤离成本 ~2 hr
- **触发**: 选项 1/2'/2'' 都不破 mid-range attractor 后

---

## 不可触红线 (continue from handoff Section 6)

1. ❌ R20 实测 PHI_ABS=50 inference replay 不能代替 retrain (policy 没变, 物理量级一致). 后续 V4.2 必须 retrain.
2. ❌ 别在 R20 数据上加更多 inference probe (e.g. PHI_D=10 / PHI_H=100 inference). 都会得到同样的 deterministic 物理 trace.
3. ❌ 别盲扫 PHI 超参 (V4.0 PHI_D=1 STOP @ ep75, V4.1 PHI_D=0.0056 200 ep anti-paper, R20 + PHI_ABS=50 inference 也没破 saturation, 第 4 次扫不会换答案).
4. ❌ 别在 R20 上 anchor "paper Eq.14 incomplete" — handoff 假设需 V4.2 retrain 验证后才 anchor.

---

## 文件引用

- 本 verdict: `quality_reports/research_loop/round_20_verdict.md`
- probe 脚本: `scripts/research_loop/r20_reward_settled_audit.py`
- raw json: `results/research_loop/r20_reward_settled.json`
- ANDES log: `logs/r20_andes.log`
- 提取脚本: `scripts/research_loop/_r20_extract.py`
- 前置 handoff: `quality_reports/handoff/2026-05-07_andes_v41_reward_paradox_handoff.md`
- paper 事实: `docs/paper/kd_4agent_paper_facts.md` (Eq.14-18)

---

*Generated 2026-05-07 by main agent. Hypothesis A 部分支持 (sync + r_f≈0) 部分推翻 (ΔD 全饱和 ≠ 互抵 mean=0). 后续等用户在选项 1/2/3/4 选.*
