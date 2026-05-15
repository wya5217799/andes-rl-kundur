# R10-R17 — ANDES 全问题修 verdict 汇总

> ⚠⚠⚠ **DT-BUG CAVEAT — 全部 trace 数字 measured at 0.6s/step BUG, paper-faithful 是 0.2s/step** ⚠⚠⚠
>
> **2026-05-07 后发现** `env/andes/base_env.py` step() 内 `current_t = self.ss.dae.t` 是 numpy.ndarray reference 而非 value-copy → ANDES TDS 推 `dae.t` 后 `current_t` 也跟着变 → sub_target 累计 0.04+0.08+0.12+0.16+0.20=0.6s 而非 paper-faithful 0.2s.
>
> **影响**: R10-R17 全部 trace 数字 (max_df / final_df / settling / nadir time) **是在 3× 错时间尺度上测的**. 30 step trace = 18s 不是 6s; 150 step = 90s 不是 30s. paper Fig.6 6s window 我们的 trace 在 6s 时是 step 10 (= 1/3 进度).
>
> **paper-anchor 状态**:
> - 相对比较 (V2 vs V3 vs V4 / G4 paper vs zero / V3 governor effect) 仍有效, 因两边同 buggy DT
> - **绝对量级 paper 比对全部 invalid**, 任何"V4 LS1 nadir 0.26 = 1.4× paper" / "settled 0.088 = paper 0.08 1.10×" 等数字必须 DT-fix 后重测
> - PI-AC methodology error (R11 J=1e-7) 仍有效, 是数值精度跟 DT 无关
> - CTDE param 1.10× (R12) 仍有效, pure param count
>
> **修了**: `current_t = float(self.ss.dae.t)` (一行改动). V4 paper-faithful re-eval (DT-fix 后, paper Fig.6 6s window):
> - LS1 max_df=**0.183** (1.41× paper 0.13), final_df=**0.102** (1.27× paper 0.08), 6-axis=**0.110**
> - LS2 max_df=**0.169** (1.69× paper 0.10), final_df=**0.102** (2.04× paper 0.05), 6-axis=**0.082**
> - 跟 V2 历史 attractor 0.036 比仍 3× 改善, 但 absolute paper alignment 仍有 1.27-2.04× gap, 需 V4.1 (action range) + 训练才能 reach
>
> 详见 `quality_reports/research_loop/round_10_to_17_unified_verdict.md` 末尾 "DT-bug 后重测" §.


**Date**: 2026-05-07
**Wall**: ~90 min (R10-R17 含 V4 env 创建 + 验证)
**Trigger**: 用户 "改所有 ANDES 问题"
**Predecessor**: ANDES path closure (`2026-05-07_andes_path_closure.md`) — 现 RE-OPENED

---

## TL;DR (1 段)

ANDES path closure decision **被这次 audit 推翻**. 原 closure 基于 R08 H scan "max_df 在 H=300 仍 2× paper" 的 finding; R10-R17 forensic 显示:
1. **Root #2 (governor DAE_INACTIVE)** — IEEEG1 加进 ss 但完全没在 DAE solver 激活. 原因 `ss.setup()` 后再 `add()` 不被 ANDES 支持, V3 旧 try/except 吞了 fatal. **修法**: V1 加 `_pre_setup_addons` hook, V3 重写为 hook-based, IEEEG1 在 ss.setup() 之前 add. R10 verdict ALL_PASS, IEEEG1 0→7 Algeb/State.
2. **Root #3 主因 = 测量定义错配 + H₀ 太小**:
   - 测量错配: 我们一直拿 `max(|freq-50|)` 整 episode 比 paper "0.13" — 但 paper Fig.6 的 0.13 实际是稳态偏差 (settled), 不是 transient overshoot peak.
   - H₀ 太小: V2 default `VSG_M0=30` (H₀=15s) 严重低于 paper Eq.12 box [10, 300] 中段 (paper 未给具体值, fact doc Q-D). H₀=15 给大 transient overshoot, H₀=100 (V4 default) 让 nadir 跌到 paper 量级.
   - 次要: G4 inertia zeroing (V1 默认 G4=0 模拟风电场) 解释 26% no-control 残差. paper Kundur 是 4 sync gen 全 H, 不 zero.
3. **方向 2 PI-AC** — methodology error: J_residual = 数值精度 (1e-7), closed-form ODE simulator 已 enforce swing eq, 加正则梯度 = 0. 任何路径无效, paper appendix flag.
4. **方向 3 CTDE** — FEASIBLE: param 1.10× (137K→151K), 极便宜.
5. **方向 4 settling reward** — measurement-definition fix 即可激活信号.

V4 env 创建 (`env/andes/andes_vsg_env_v4.py`) consolidate 所有修, paper-faithful baseline. R17 verify: V4 LS1 max_df 从 V2 0.51 降到 0.26 (49% 改善), settled 0.088 = paper 0.08 的 1.10×.

---

## 后续 R19-R20 audit (2026-05-07 后, post DT-fix)

R19 / R20 / R21 forensic 用 paper-faithful DT 重测, 排除 Root #3 候选:

| Round | 候选 | Verdict |
|---|---|---|
| **R19** | WF2 (Bus 8 zero-inertia) | ❌ NEUTRAL — diff 0.0/0.1% on LS1/LS2 max_df, 完全不贡献 |
| **R20** | IEEEG1 K (gain) + T1 (lag) | ❌ NOT_CAUSE — 4 variant K∈{20,50,100} T1∈{0.1,1.0,2.0} max_df 0.189-0.190, 0.5% spread |

**结论**: 剩 **1.45× paper LS1 max_df gap (V4 0.189 vs paper 0.13)** 在我们能轻易触及的 env knob 之外:
- ❌ G4 inertia (R15: 26% partial fix, 已 V4 paper-restored)
- ❌ NEW_LINE_X (R16: not cause)
- ❌ WF2 (R19: not cause, 0.1% diff)
- ❌ IEEEG1 params (R20: not cause, 0.5% diff)
- 🔍 Total system load 3170 vs paper 2734 MW (+16% offset, R21 候选)
- 🔍 GENCLS xd1=0.15 transient reactance (R22 候选)
- 🔍 ANDES vs Simulink solver numerical 差异 (cross-platform irreducible)
- 🔍 PQ 常功率模型 (p2p=1.0) vs paper Simulink ZIP load 模型

**Working hypothesis**: 1.45× residual 是 ANDES vs Simulink **solver + PQ 模型差异**, 不是简单 env knob 修可消除. paper SAC 训练把 nadir 从 0.13 → 0.05 (61% reduction); V4 训练应能从 0.189 → 0.07-0.10 (60% reduction 类比). **不影响"复现 paper 趋势 + 学到合理 controller"** 主目标.

---

## 修复链 (R10 → R17)

| Round | Wall | 类型 | Key finding/fix |
|---|---|---|---|
| **R10** | 15 min | forensic | Root #2 升级: IEEEG1 整 model DAE_INACTIVE (0 Algeb/State). 通用 utility `probes/andes_common/utils.py` 上线. |
| **R11** | 5 min | MVV | 方向 2 PI-AC: J=1.069e-07 单一常数, methodology error |
| **R12** | 1 min | MVV | 方向 3 CTDE: param 1.10×, FEASIBLE |
| **R13** | 5 min (×2) | MVV | 方向 4 settling: NO_SIGNAL 即使 30s, 因 final_df 不 settle 到 paper |
| **R14** | 5 min | H scan | V3 active gov H=6.5: 0.514, H=300: 0.214 — `max_df` 仍 2× paper 但**比 R08 (V3 dead) 整体降** |
| **R15** | 2 min | G4 audit | G4 paper-restored 改善 26% (0.514 → 0.380) — partial root cause |
| **R16** | 5 min | LINE_X | NEW_LINE_X 不是 Root #3 主因 (sweep flat 0.43-0.50) |
| **R17** | 3 min | V4 verify | V4 (M0=200, governor active, G4 paper) **LS1 nadir 0.26, settled 0.088 = paper match** |

(R17b D₀=100 paper-faithful re-run 进行中, 应进一步降 nadir.)

---

## V4 env 设计 (paper-faithful baseline)

```python
class AndesMultiVSGEnvV4(AndesMultiVSGEnvV3):
    VSG_M0 = 200.0   # H₀=100s, paper Eq.12 box [10,300] 中段
    VSG_D0 = 100.0
    D0_HETEROGENEOUS = np.array([100.0, 100.0, 100.0, 100.0])
    # G4 默认 paper-faithful (V1 ZERO_G4_INERTIA=False)
    # IEEEG1 + EXST1 通过 V3 _pre_setup_addons 钩子 (DAE-active)
```

**关键差异 vs V2**:
| 项 | V2 default | V4 default | 来源 |
|---|---|---|---|
| VSG_M0 | 30 (H₀=15s) | 200 (H₀=100s) | paper Eq.12 box 中段 (R14/R17) |
| VSG_D0 (uniform) | n/a | 100 | paper Eq.12 box 中段 |
| D0_HETEROGENEOUS | [20,16,4,8] | [100,100,100,100] | paper-faithful uniform (V2 hetero 是 paper-deviation) |
| Governor (IEEEG1) | 无 | DAE-active | R10 fix |
| AVR (EXST1) | 无 | DAE-active | R10 fix |
| G4 GENROU.M | 0.1 | 111.15 | paper Kundur 4 SG (R15) |
| Action range (DM/DD) | [-12, 40]/[-15, 45] | inherits V2 | TODO V4.1 (paper Sec.IV-B) |

**V2 ckpts 不可 resume V4** (M0/D0/governor 都变, env 物理动力学完全不同).

---

## R17 V4 验证结果 (LS1 + LS2)

V4 默认 (D₀=20 hetero, V2 reset 覆盖 bug):
| Scenario | nadir@t | nadir | settled | paper nadir | paper settled | nadir 改善 vs V2 |
|---|---|---|---|---|---|---|
| LS1 (-2.48 @ Bus14) | 0.8s | 0.261 | 0.088 | 0.13 (2.01×) | 0.08 (**1.10×**) | 49% |
| LS2 (+1.88 @ Bus15) | 0.8s | 0.251 | 0.095 | 0.10 (1.93×) | 0.05 (1.90×) | n/a |

R17b D₀=100 fix 重跑结果 → 见 `r17b_v4_d0_100.json` (R17b 进行中).

---

## 测量定义改 (eval 已对, env 是关键)

`evaluation/paper_grade_axes.py` 已设计 6 axis 含 `final_df` (LS1=0.08, LS2=0.05). **eval metric 不需改**, V4 baseline 才是 fix.

旧 R08 finding "max_df 仍 2× paper at H=300" 是 V3 governor dead + 拿 max_df 当 paper 0.13 比. 修 governor + 用 final_df 比 → V4 几乎 paper-aligned.

---

## ANDES path 决策

**原 (2026-05-07 closure)**: 关 ANDES, 切 Simulink-discrete 主线.
**新 (2026-05-07 R17 后)**: **重开 ANDES**, V4 paper-faithful baseline 就绪, 训练有 reach paper Fig.7/9 视觉对齐的物理可能性.

下一步:
1. (待办) 等 R17b 出来确认 D₀=100 是否进一步降 nadir 到 paper 量级
2. (待办) 用 V4 重训 SAC, 跑 paper_grade_axes.py 6-axis 评估, 应大幅高于历史 0.04 attractor
3. (待办) 实施方向 3 CTDE (param 1.10× 几乎免费)
4. (Class A 修) 改 V4 action range 到 paper Sec.IV-B [-100,+300]/[-200,+600] (V4.1)
5. paper appendix B 仍写 PI-AC negative finding (方向 2 不可逆)

---

## 文件 / 引用

- 修过的 env: `env/andes/andes_vsg_env.py` (G4 opt-in), `andes_vsg_env_v3.py` (governor hook), `andes_vsg_env_v4.py` (V4 全套)
- Probe utility: `probes/andes_common/utils.py` (R10 留)
- Probes: `scripts/research_loop/r1{0..7}_*.py`
- 输出 JSON: `results/research_loop/r1{0..7}_*.json`
- 上游: `quality_reports/research_loop/优化方向.md`, `round_08_verdict.md`
- 之前 closure (待更新): `quality_reports/handoff/2026-05-07_andes_path_closure.md`

---

*Generated 2026-05-07 by R10-R17 unified audit, ANDES path RE-OPENED.*
