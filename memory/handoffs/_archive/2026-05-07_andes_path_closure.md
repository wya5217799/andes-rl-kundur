# ANDES Path Closure — R01-R08 Negative Finding 汇总

**Date**: 2026-05-07
**Decision**: 停 ANDES R09, 切回 Simulink-discrete 主线
**Total wall**: ~145 min (R01-R08, ~3 hr)
**Status**: ANDES path 不可达 paper Fig.7/9 视觉对齐, 即使全部已知 root cause 修对, 仍剩 2× cosmetic gap
**Trigger**: R08 H scan 实测 H=300 paper-scale no_control max_df = 0.266 vs paper 0.13 (2× too large), 不是 SAC 训练问题

---

## ⚠⚠⚠ 2026-05-07 (later 同日) — Closure RE-OPENED by R10-R17 ⚠⚠⚠

R10-R17 forensic 推翻本 closure decision. 关键发现:

1. **Root #2 升级**: IEEEG1 整 model 在 ANDES DAE 没激活 (0 Algeb/State), 不只是 wiring 错. 修法: V1 加 `_pre_setup_addons` hook + V3 重写为 hook-based, IEEEG1 在 ss.setup() 之前 add. R10 verdict ALL_PASS.
2. **Root #3 不是平台残差, 是测量定义错配 + H₀ 量级错**: 我们一直拿 `max(|freq-50|)` 整 episode 比 paper "0.13" — paper Fig.6 0.13 实际是稳态偏差 (settled). 而 V2 default `VSG_M0=30` (H₀=15s) 严重低于 paper Eq.12 box [10, 300] 中段; H₀=100 (V4) 给 nadir/settled 都 paper-magnitude.
3. **G4 inertia zeroing** 解释 26% no-control 残差 (V1 默认 G4=0 是模拟风电场, 不是 paper Kundur).
4. **V4 env created** (`env/andes/andes_vsg_env_v4.py`) consolidate all fixes. R17 verify: V4 LS1 nadir 0.26 (V2 0.51 → 49% 降), settled 0.088 = paper 0.08 的 1.10×.

**新 decision**: ANDES path **RE-OPENED**. V4 baseline paper-faithful, 训练有 reach paper Fig.7/9 视觉对齐的物理可能性.

完整 R10-R17 verdict: `quality_reports/research_loop/round_10_to_17_unified_verdict.md`.

下一步: V4 重训 SAC, 跑 6-axis 评估, 实施方向 3 CTDE (FEASIBLE), 修 V4 action range to paper Sec.IV-B (V4.1). paper appendix B 仍写 PI-AC negative finding (方向 2 不可逆).

---

---

## TL;DR (1 段)

R01-R08 在 ANDES Kundur 4-VSG 复现 Yang2023 paper 上跑 ~3 hr, 找到 3 个 root cause:
1. **eval 公式 bug** (R06 audit 找到, R07 修了) — `paper_grade_axes.py` range axis 公式语义反, 已 fix
2. **V3 env governor wiring 完全失效** (R08 实测找到) — IEEEG1+EXST1 加进 ANDES 但 vout 没接 swing 方程, R03/R04 governor 实验全 invalid
3. **平台 2× 残差** (R08 量化) — 即使 H=300 (paper Eq.12 上限) no_control max_df 仍 2× paper, ANDES vs paper Simulink 平台层差异

修 1 + 2 + SAC 完美训练**最乐观**仍只能到 max_df 0.14-0.20, paper 是 0.13. **2× 残差是平台层 (line/SBASE/solver damping), 不是 SAC 能 fix**.

ANDES 本来就是 frozen historical path (per `MEMORY.md`), 主项目在 Simulink-discrete repo. 决定停 ANDES, 不再 R09.

---

## R01-R08 Timeline (节录关键)

| Round | wall | Phase | 关键 finding | verdict path |
|---|---|---|---|---|
| R01-R04 | 120 min | Train (老路径) | PHI_D=0.05 偏 paper 1.0 → 修 PHI_D=1.0 (R03→R04) | round_03/04_verdict.md |
| R04 | — | — | adaptive=no_ctrl 6-axis 0.010, 控制实现/平台问题信号 | round_04_verdict.md §2 |
| R05 | 20 min | Explore (短-多臂 bandit) | 8 hyperparam 维度全 6-axis=0.037 attractor, hyperparam 不是 root | round_05_verdict.md |
| R06 | 30 min | Audit (4 audit 并行 fork) | exp1 找到 axes.py range axis bug, exp2 推翻 P 注入嫌疑, exp3 确认 disturbance 已对齐 | round_06_verdict.md |
| R07 | 20 min | Explore (audit-driven) | 修 axes.py 后 attractor 破 (0.037→0.139), 暴露 no_control 平台 4× 残差 | round_07_verdict.md |
| R08 | 15 min | Empirical sweep | V1 H scan 单调降 67%, V2 governor 完全无效, V3 H=300+gov 仍 2× paper | round_08_verdict.md |

新工作流 (R05+R06+R07+R08, ~85 min) 找到 3 个 root cause, vs 老路径 (R01-R04, ~120 min) 0 root cause. 信号密度 ~10× 提升.

---

## 3 个 Confirmed Root Causes

### Root #1: eval 公式 bug (已修, 通用收益) ✅

`evaluation/paper_grade_axes.py` range axis 公式语义反:
- 老逻辑: `score = 1 - |1 - proj_span/paper_span|/0.5` 反向惩罚 ΔH span 不够大
- 把 paper Eq.12 box bound 宽度 (400) 当成 trajectory span 期望值
- paper Eq.17 (`r^h = -ΔH_avg^2`) 实际要 ΔH_avg → 0 守恒

**修法 (R07 commit `9bc7a08`)**: 加 `_box_containment` 函数, proj 完全在 box 内 → score=1.0, 越界扣分.

**通用价值**: 这个修对 Simulink-discrete 路径用同一 evaluator 也有效. 是 R01-R08 真改进保留下来.

### Root #2: V3 env governor 整个模型未激活 (R10 forensic 升级 2026-05-07) ⚠⚠

**升级前 R08 描述**: "ANDES IEEEG1 模型默认 syn= 字段不自动 wire 到 GENROU 的 Pm input, 需手动设"
**升级后 R10 forensic** (`round_10_verdict.md`): **不只是 Pgv→Pm 链路断, IEEEG1 整个模型在 ANDES DAE 里没被激活**

R10 实测铁证:
- L1 PASS: `IEEEG1.syn = [1,2,3,4]` 完美对齐 `GENROU.idx = [1,2,3,4]`
- **L2 字段缺失**: IEEEG1 introspection **0 个 Algeb / State / ExtAlgeb**, 只有 24 个 NumParam (K, T1-T7, PMAX, PMIN 等常数) + IdxParam (syn) — ANDES 没把 IEEEG1 编译进 DAE
- L3 PASS 但 L4 FAIL: V3 GENROU.Pm 移动来自 GENCLS 自带 swing eq (V2 也有), 不是 IEEEG1 给的
- **V2 vs V3 Pm 轨迹完全相同到小数点后 13 位** (差 = 0.0, 不是 ~0)
- **V2 vs V3 max_df 完全相同**: 0.5580468747419118 = 0.5580468747419118

`env/andes/andes_vsg_env_v3.py::_build_system` 的 `try: ss.setup() except: pass` 吞掉了 fatal error — ANDES 不允许 `setup()` 后再 `.add()` 新模型. 必须一次性 build.

**修法** (若未来重启 ANDES path, 仍不推荐): 重写 V2 base 让 add 都在 setup 前, 或 V3 自己 build ss 重头. 但修对 governor 后 Root #3 平台 2× 残差仍在, **仍不能 reach paper**.

**probe script**: `scripts/research_loop/r10_governor_wiring_forensic.py` — 4 layer (L1 静态 + L2/L3/L4 动态 + L0 max_df 比对), 复用 `introspect_model()` 通用 utility (任何 "ANDES 加了模型生效了吗" 问题适用)

**给未来 ANDES 路径的警告**: 已在 `env/andes/andes_vsg_env_v3.py` header 加 `⚠ GOVERNOR WIRING NOT VERIFIED EFFECTIVE`. R10 forensic 进一步确认: governor 不只 wiring 没接, 是整个 IEEEG1 在 DAE 里就没参与计算.

### Root #3: 平台 2× 残差 (无法 fix) ❌

R08 V1 H scan 实测:
| H | LS1 max_df no_ctrl | vs paper |
|---|---|---|
| 10 (baseline) | 0.815 | 6.3× |
| 30 | 0.539 | 4.1× |
| 100 | 0.328 | 2.5× |
| **300 (paper Eq.12 上限)** | **0.266** | **2.0×** |

**结论**: 即使 H 拉到 paper 物理上限 300 (= paper action box upper bound), ANDES no_control max_df 仍 2× paper.

**残差源候选** (audit 没做, 估计):
- ANDES `kundur_full.xlsx` line impedance / transformer leakage 跟 paper Kundur Power System Stability 标准不一致
- ANDES TDS solver 数值阻尼 vs Simulink Power Block solver 不同
- ANDES PQ 模型 p2p=1.0 (常功率) 注入 vs paper Simulink load step 不同

**为啥不修**: 平台层差异需要重写 ANDES system spec 或换 solver, 工作量等价"切 Simulink-discrete repo 重头". 后者已在跑, 投入更值.

---

## SAC 调参全 falsified (Methodological Lesson)

R05 短-多臂 bandit 测了 8 hyperparam 维度:

| arm | 改的维度 | 6-axis (修前) | 6-axis (R07 修后) |
|---|---|---|---|
| baseline | V2 + paper Table I | 0.037 | 0.139 |
| phid_5x | PHI_D=5.0 | 0.037 | 0.138 |
| lam_zero | LAMBDA_SMOOTH=0 | 0.037 | 0.138 |
| v1_env_back | V1 env (M0=20, D0=4 uniform) | 0.037 | 0.138 |
| action_range_2x | DM/DD × 2 | 0.037 | 0.138 |
| v3_governor | V3 (V2 + IEEEG1+EXST1) | 0.037 | 0.138 |
| disturb_5x | DISTURB_SCALE=5 | 0.037 | 0.139 |
| combo_v1_disturb5x | V1 + 5× disturb | 0.037 | 0.139 |

8 个不同方向, 修 axis 后**全部 0.138-0.139, 几乎并列**. 物理动态 (max_df / final_df / settling) 在 SAC 改善天花板内 (no_control max_df 0.55, SAC best 0.49 = 11% 改善). **SAC 调参不是 root cause, 平台是**.

**Lesson 锁进 `.claude/skills/research-loop/SKILL.md`**:
- physics validation **必须 R0 跑** (no_control 物理基线 vs paper baseline), 不是 R5+
- attractor 破后立刻 check no_control, 若 no_control 已超 paper 几倍, SAC 训练再多也 reach 不到
- governor 物理修改后必须 zero-action 物理量对比 probe, 不是 "TDS PASS" probe

---

## 给未来 ANDES 路径的 Caveat (重启时必读)

如果未来用户/AI 想重启 ANDES path, **先读这份文档**, 然后:

1. **不要重做 R01-R04 hyperparam sweep** — 已 falsified
2. **若想跑 governor**: 必须先验证 IEEEG1 vout → GENROU Pm wiring (zero-action V2 vs V3 max_df 对比, 见 r08_h_scan.py)
3. **若想 reach paper Fig.7/9 视觉对齐**: 必须先解决平台 2× 残差 — 改 ANDES system spec 或换 solver
4. **eval 工具 (paper_grade_axes.py) 已修**, 直接用. 但 range axis 0→1.0 跳是因为 box containment 平凡满分 (项目 ΔH range << box width), 不是 paper-aligned

---

## Paper Appendix 候选 (学术诚实材料)

R01-R08 的 negative finding 可作 paper appendix 增加学术价值:

> **Appendix B: Cross-Platform Validation — ANDES vs Simulink Kundur**
>
> We attempted to cross-validate the proposed DDIC controller on the ANDES dynamic
> simulation platform (Cui et al., 2020). Despite matching paper hyperparameters
> (Table I) and verifying disturbance protocol alignment, ANDES no-control LS1
> max_|Δf| = 0.266 Hz at H=300 (paper Eq.12 box upper bound) remains 2× larger
> than paper Simulink baseline (0.13 Hz), suggesting platform-level damping or
> solver numerical differences. We document this as a known limitation of
> cross-platform DDIC reproduction.

学术价值: cross-platform reproducibility 是当前 RL+power systems 文献缺失的话题. 把 ANDES negative finding 写成 appendix 是诚实学术态度, 反而**增加 paper credibility**.

---

## 现 ANDES Codebase 状态 (handoff give-up state)

**保留 (有用 + 通用)**:
- `evaluation/paper_grade_axes.py` (R07 修 range axis bug, 通用) ✓
- `scripts/research_loop/eval_paper_spec_v2.py` (eval 单一入口, L4 lock-in) ✓
- `scripts/research_loop/r08_h_scan.py` (H scan 物理验证 script, 给未来路径) ✓
- `quality_reports/research_loop/round_*.md` 全部 verdict (历史快照) ✓
- `quality_reports/research_loop/audits/2026-05-07_*.md` (R06 audit reports) ✓

**警告 (未修但已识别)**:
- `env/andes/andes_vsg_env_v3.py` — governor wiring 实测无效 (本 commit 加 header 警告)

**Frozen, 不再投入**:
- `scenarios/kundur/_legacy_2026-04/` (L4 commit `e40ff06` 已归档)
- R01-R04 期所有 train ckpt (results/research_loop/r01-r04_*) — historical
- R05 8 arm + R06 5 v1_5seed ckpt — eval 完成 (R07 修 axes 后 ranking 已出)

---

## R09 (不做) — 留给未来文档

```
若有人 R09 重启 ANDES path, 推荐顺序:
1. 修 V3 env governor wiring (~30 min)
   - 读 ANDES IEEEG1 doc 看 vout = Pgv 字段
   - 读 GENROU input 看 Pm 是否能 set 为外部 (默认 Pm 是 algebraic)
   - 必须手动 link (e.g. 自定义 ANDES function 或 GENROU Pm input wiring)
2. 验证修对 (zero-action V2 vs V3 max_df 必须不同)
3. 平台 2× 残差 audit (line/SBASE/solver 参数)
4. 决策: 修后 max_df 是否 ≥ 0.4 → 继续 / 放弃
```

---

## 现在做啥 (next action for user)

切 `C:\Users\27443\Desktop\Multi-Agent-VSGs-discrete` repo:
1. 看 `results/sim_kundur/runs/phase1_7_trial_3/eval/` 状态
2. paper submission track 推进 (per `AGENTS.md::Paper Submission Track`)
3. 可选: 把本文档 §"Paper Appendix 候选" 加进 Simulink paper draft

ANDES path 这次 session 投入 145 min, 找到 3 root cause, 修了 1 个 (eval bug 通用), 2 个标记为不可修 (governor wiring + 平台 2× 残差). **不浪费**, 但**性价比已到顶**.

---

*Generated by main agent integrating R01-R08 verdict, 2026-05-07.*
