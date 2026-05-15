# CONTEXT — Multi-Agent VSGs ANDES Track (caveman)

**Last full-rewrite**: v1 / 2026-05-08
**Status**: ⚠ **ANDES 主线即将冻结**, 此文档为收尾 snapshot
**Scope**: ANDES 工程迭代 + 决策追溯 + 失败族谱 + Round 索引
**Audience**: 改 ANDES 代码 / 答辩前回查 / 论文校对的 Claude (或人)
**Reading time**: TL;DR 30 秒 / 速查 3 分钟 / 全部 15 分钟
**Cross-ref**:
- 论文 finding (SPEC + 错误防护) → `毕业论文/CONTEXT.md`
- ANDES 因果链 (R01-R37 时间序 + commit + 6 拐点 + type-view filter, **写 §4.5 Reflection 主源**) → `Multi-Agent VSGs/RESEARCH_TRAIL.md`

---

## §0 Trust Legend

每条 fact 行尾标:

- `[V]` VERIFIED — file:line / commit / verdict 核过
- `[S]` SPECULATIVE — 推断未核
- `[T]` TODO-VERIFY — 应核未核
- `[C]` CORRECTED — 之前错过, 现在是对的版本

---

## §1 TL;DR (30 秒)

**ANDES Kundur 4-VSG 复现, R01 → R37 共 ~37 round, 12 phase + ranker fix.**

⚠ **数字有 4 个历史版本, 论文用 post-fix**. 详见 §11.

- **论文 headline (post-r30/N1c ranker fix, 2026-05-08 L3 锁定)**:
  - R21 6-axis = **0.444** (4.04× no_ctrl 0.104), 不是 0.613
  - HAWE w9802 (98% R21 + 2% ws8) **0.439** = **99.3%** R21, fresh-seed 反 lineage 循环 [V]
  - **HAWE = 5 bespoke asset 之一**, 不是补充技巧
- **Multi-seed attractor**: 0.137 ± 0.005 across H₀ ∈ {40,70,100,200} × 5 seed × 22 ckpts [V]
- **当前 active branch**: `main` (HEAD = `2d9708e R25-R36 Path B forensic + ranker fix + DA-CRIT-1 推翻`) [V]
- **Phase A-E recovery plan**: 实质 **abandoned**, 被 R28-R34 algorithm sprint 替代 [V]
- **Env 主用**: `andes_vsg_env_v4.py` (default H₀=100, paper-faithful Eq.14) [V]
- **核心 finding**: paper Eq.14 strict $\varphi_d=1.0$ 系统不可复现 (训到 ep75 必爆), $\varphi_d=0.0056$ 训稳但 anti-paper [V]
- **运行环境**: ANDES **WSL only**, Windows 端是历史误装 [V]
- **plan/ 文档生态**: 46 文件 (16 evidence pack + handoff v12-v14 + master index + 5-reviewer + ANDES IEEE 草稿). 详见 §10

---

## §2 Anti-Patterns (ANDES 端独有, 论文 CONTEXT §2 主表已收 7 条)

⚠ **新 Claude 必读. ANDES 端易犯错**。

主表见 `毕业论文/CONTEXT.md §2`. 此处补 ANDES 工程独有的 12 条:

| 错误声明 | 错在哪 | 真实 | 锚点 |
|---|---|---|---|
| V3 env governor wiring 工作 | R08 验过 | governor on/off diff = 0.000, IEEEG1 整 model DAE_INACTIVE, V3 governor **死的** | `quality_reports/research_loop/round_08_verdict.md`, `round_10_verdict.md` [V] |
| V4 default H₀=10 (经典 Kundur) | 错版本 | V4 用 H₀=100 (paper-faithful Eq.14). V1/V2 是 H₀=10. V4 是 paper 主线 env | `env/andes/andes_vsg_env_v4.py` [V] |
| `axes.py` range axis 公式正确 | R06 找到 Bug-A | 公式语义反: 把 box bound 当 trajectory span. R07 修后 attractor 0.037 → 0.139 | `quality_reports/research_loop/round_06_verdict.md` §Bug-A [V] |
| settling = ∞ 是物理模型问题 | 半错 | R28' 找到 ranker 6s truncate; LS2 actual settling = 6.8s 不是 ∞ | `quality_reports/research_loop/r28_r21_settling_verdict.md` [V] |
| Phase A-E recovery plan 在执行 | 已 abandon | DRAFT 状态, §Done Summary 空. 被 R28-R34 algorithm sprint 替代 | `quality_reports/plans/2026-05-07_andes_6axis_recovery.md` [V] |
| 8 ANDES 进程并行 OK | 上限 ≤ 3 | 16C/32T 工作站, 4+ → TDS internal stiffness mis-judge → spurious termination t=1.2-1.7s | `quality_reports/research_loop/round_23_verdict.md` [V] |
| Stochastic ensemble (同 actor 采样 N 次) 能改善 R21 | R32 反实测 | R21_stoch5 rank 95 (worst), 0.106 < no_ctrl 0.110. 噪声把 action 拉出 lucky basin | `round_28_to_34_final_verdict.md` §R32 [V] |
| Reward shaping (PHI_MAX / PHI_SETTLE) 能改善 max_df / settling | R31/R33 反实测 | 4 变体全 rank 35-43, SAC critic 偏 conservative near-zero action, 摧毁 R21 lucky strategy | 同上 §R31/R33 [V] |
| Hparam sweep (PHI_ABS / PHI_H / PHI_F) 能改 R21 | R29 反实测 | 4 变体全 rank 35-55, SAC update 把 actor 拉离 R21 lucky basin | 同上 §R29 [V] |
| R21 0.613 best.pt 文件 = R23+ 用的 best.pt | 不同文件 | R21 best.pt 1.31MB, R23+ 2.56MB. Env reward landscape 微变, lucky basin 已不存在 | `round_23_to_27_summary_verdict.md` [V] |
| ZIP DynLoad v2 闭 LS2 residual 可行 | R29 反实测 | LS1 = LS2 bit-identical, dispatch 失效, ZIP config 不 propagate | `quality_reports/research_loop/r29_zip_v2_verdict.md` [V] |
| AGC 能 expose 给 RL | R25 反实测 | AGC 不 expose, ZIP config 不 propagate, paper §V-A AGC closure 路线被废 | `quality_reports/research_loop/r25_agc_zip_probe_verdict.md` [V] |

---

## §3 Phase Timeline P1-P12

**12 phase, 各自 anchor round, audit-grade.** 锚点 = audit / verdict.

⚠ **表中数字反映 verdict 当时**. Post-ranker-fix (2026-05-07 N1c) headline 见 **§11**: R21 0.613→0.444, P12 ensemble 0.554/0.607→0.439.

| P# | Round 范围 | 一句话目标 | 关键 verdict | 锚点 |
|---|---|---|---|---|
| P1 | R01 | LAMBDA_SMOOTH 三档 + GPU stress | action_std collapse 0.18, λ 三档差<1%, BC probe Phase B governor add PASS | `quality_reports/research_loop/round_01_verdict.md` |
| P2 | R02-R05 | 多臂 Bandit 8 arms × 30ep 跨维度 sweep | 全 6-axis ≈ 0.037 attractor (no_ctrl 0.010), 8 维度全卡 | `round_05_verdict.md` |
| P3 | R06 | 物理对齐 audit (4 exp 并行) ⭐ | 找到 `axes.py` Bug-A: range axis 公式语义反 (box bound 当 trajectory span) | `round_06_verdict.md` |
| P4 | R07 | 修 axes.py Bug-A/B (25 LOC) | attractor 破 0.037 → 0.139 (3.76×), 仍远未 paper-align | `round_07_verdict.md` |
| P5 | R08 | H scan + governor 物理验证 (V3 env) | H=300 max_df 0.266 vs paper 0.13 (2× gap), V3 governor on/off diff = 0.000 | `round_08_verdict.md` |
| P6 | R10-R17 | ANDES 全 root cause forensic + V4 baseline ⭐ | 修 4 bug: governor DAE_INACTIVE / G4 inertia / DT 3× 错配 / V4 H₀=100 paper-faithful → V4 LS1 nadir 改善 49% | `round_10_to_17_unified_verdict.md` |
| P7 | R18-R19 | PHI rescale + V4.1 audit | $\varphi_d=0.0056$ (1/178) 防 reward 爆炸, $M_\text{min}=20$ / $D_\text{min}=10$ paper Eq.12 lower clamp | `quality_reports/handoff/2026-05-07_v4_session_handoff.md` |
| P8 | R20 | reward paradox confirmatory probe | settled max\|Δω\|≥0.05 + r_f<0.5 PASS, ΔH 非对称偏移 (LS1 [-15,-28,+46,-15]), trivial optimum 不是 mean²=0 | `round_20_verdict.md` |
| P9 ⭐ | R21 | V4 paper-grade 突破 (`h50_s49` 0.613) | LS1 final_df 0.078 vs paper 0.08 = **97% match**, 16.5× V1 (0.037), historical winner | `round_21_v4_breakthrough.md` |
| P10 | R22 | V4.2 三路 PHI sweep retrain | A/B/C 全 anti-paper, max_df 0.30 vs V4.1 0.22 vs no_ctrl 0.18, PHI_ABS [50,200] dimension dead | `round_22_verdict.md` |
| P11 | R23-R27 | 复现 R21 hparam + H₀ + 多 seed | 22 ckpts 全 ≤ 0.22, R21 0.613 不可 reproduce (best.pt 1.31MB vs 2.56MB 代码版本不同) | `round_23_to_27_summary_verdict.md` |
| P12 ⭐ | R28-R34 | warmstart + algo innovation 6 family | **R30 ensemble w8515 = 0.554** = 89.7% R21 = 5.04× no_ctrl. R29/R31/R32 全失败. 新 reproducible top | `round_28_to_34_final_verdict.md` |

---

## §4 Round Table R01-R36

⭐ = phase 切换 / 决策节点.

⚠ **数字反映各 verdict 当时**. Post-ranker-fix headline 见 **§11**.

| Round | 目标 | Verdict | 关键数字 | 锚点 |
|---|---|---|---|---|
| R01 | 50ep×5seed λ-sweep 验 smoothness penalty | MIXED | std 0.18 collapse, λ 三档差 <1% | `round_01_verdict.md` |
| R02 | 200ep×5seed lam=0.01 长训 + H0 sweep | MIXED | final_R 改善 60%, std 4.88 vs paper 0 | `round_02_verdict.md` |
| R03 | 500ep + obs9 + governor 试推 G5 | FAIL | 6-axis 0.036, 几乎 = no_ctrl | `round_03_verdict.md` |
| R04 | PHI_D=1.0 paper-aligned 重训 200ep | FAIL | reward 退步 130%, 6-axis 0.037 | `round_04_verdict.md` |
| R05 ⭐ | 8-arm 短 bandit 跨维度 sweep | ABANDON | 8 臂全卡 0.037 attractor | `round_05_verdict.md` |
| R06 ⭐ | attractor audit 找 eval bug | PIVOT | range axis 公式反, Bug-A/B/C | `round_06_verdict.md` |
| R07 | 修 axes.py Bug-A/B 重 eval | MIXED | 0.037 → 0.139, 仍 4× paper | `round_07_verdict.md` |
| R08 ⭐ | H scan + V3 governor 物理验证 | FAIL | V3 = V2 完全相同, governor 死的 | `round_08_verdict.md` |
| R10 ⭐ | governor wiring forensic 4-layer | FAIL | IEEEG1 整 model DAE_INACTIVE | `round_10_verdict.md` |
| R11-13 | 方向 2/3/4 MVV 三路 probe | MIXED | PI-AC J=1e-7 死, CTDE 1.10×, settling NO_SIGNAL | `round_11_13_mvv_verdict.md` |
| R10-17 ⭐ | 修全部 ANDES bug 建 V4 env | PASS | V4 LS1 max_df 0.51→0.26, settled 0.088 | `round_10_to_17_unified_verdict.md` |
| R20 | V4.1 reward paradox settled audit | MIXED | mid-range attractor ΔD≈-39, 不是互抵 | `round_20_verdict.md` |
| R21 ⭐ | V4 paper-faithful 75ep 多 seed 训 | PASS | s49 6-axis 0.613, paper 17× V2 attractor | `round_21_v4_breakthrough.md` |
| R22 | V4.2 PHI_ABS/PHI_D 三路 retrain | FAIL | 3 路全 max_df 0.30, 比 V4.1 更差 | `round_22_verdict.md` |
| R23 | H₀ sweep + multi-seed 复现 R21 | FAIL | 8 并行 ANDES TDS crash, 0 ep | `round_23_verdict.md` |
| R24 ⭐ | R23 v3 + 综合多 seed 验 0.613 | FAIL | R21 是 outlier, 其他全 0.13-0.22 | `round_24_verdict.md` |
| R23-27 ⭐ | 5 轮 sweep 22 ckpt 试超 R21 | ABANDON | 没一个 >0.22, R21 不可复现 | `round_23_to_27_summary_verdict.md` |
| R25 | AGC + ZIP load probe 闭 LS2 gap | FAIL | AGC 不 expose, ZIP config 不 propagate | `r25_agc_zip_probe_verdict.md` |
| R26 | SWA / model-soup baseline 对比 | MIXED | SWA w98=0.442 ≈ HAWE 0.439 sweet spot | `r26_swa_baseline_verdict.md` |
| R27 | Kundur V4 modal analysis | FAIL | low-score 投影更高, modal-align 假反 | `r27_modal_analysis_verdict.md` |
| R28 ⭐ | warmstart from R21 ckpt finetune | PASS | reproducible ceiling 0.41-0.42 (3.8× no_ctrl) | `round_28_warmstart_verdict.md` |
| R28' | R21 settling diagnosis (ranker bug) | PASS | LS2 settle 6.8s 不是 ∞, ranker 6s truncate | `r28_r21_settling_verdict.md` |
| R29 | ZIP DynLoad v2 闭 residual | ABANDON | LS1=LS2 bit-identical, dispatch 失效 | `r29_zip_v2_verdict.md` |
| R30 ⭐⭐ | ensemble R21+ws8 weighted 突破 | PASS | **w8515 6-axis 0.554, 89.7% R21** | `round_30_ensemble_verdict.md` |
| R30' | paper_grade_axes.py audit | MIXED | C1 geo+arith 不一致, 3 design choice flag | `r30_ranker_audit_verdict.md` |
| R33 | Gini-vs-score 统计 §VI-D 验 | PASS | Spearman ρ=+0.530 CI[+0.257,+0.731] N=46 | `r33_gini_vs_score_verdict.md` |
| R34 ⭐ | fresh-seed HAWE 反驳 lineage 循环 | PASS | HAWE 98/2 fresh seed 0.441, 99.3% R21 | `r34_n2_fresh_seed_hawe_verdict.md` |
| R35 | per-axis breakdown for Table III | PASS | 3 轴=1, 1 轴=0, 仅 max/final_df 区分 | `r35_per_axis_breakdown_verdict.md` |
| R36 | ranker tuning 4-variant sensitivity | MIXED | order 稳定, R21/no-ctrl 3.08×-4.26× | `r36_ranker_tuning_verdict.md` |
| R28-34 ⭐⭐ | algorithm innovation sprint final | PASS | reproducible top 0.554 ensemble | `round_28_to_34_final_verdict.md` |

锚点全在 `quality_reports/research_loop/`.

---

## §5 Decision Branch Tree

**走过的所有 ANDES 探索分支, 接受 / 废弃 / 为什么.**

⚠ **接受/废弃决策不变, 但数字反映 verdict 当时**. Post-ranker-fix headline 见 **§11**.

### §5.1 Accepted (写进论文)

| 决策 | Round | 理由 | 锚点 |
|---|---|---|---|
| `axes.py` Bug-A 修复 | R06 → R07 | range axis 公式语义反, 25 LOC fix attractor 0.037→0.139 | R06/R07 verdicts |
| V4 env paper-faithful (H₀=100, Eq.14 strict $\varphi_d$ rescale) | R10-17 | ANDES 4 bug 修, V4 LS1 nadir 49% 改善 | `round_10_to_17_unified_verdict.md` |
| Phase 12 ensemble (`w8515`) | R30 | reproducible 0.554, 89.7% R21, no retrain | `round_30_ensemble_verdict.md` |
| 6-axis 几何均值 metric | M1 修正 | cum_rf 单维 cherry-pick 假阳性 (-0.722 vs -0.68 = 6.2% diff "成功") | `andes_6axis_failure_analysis.md` §M1 |
| HAWE fresh-seed 反驳 | R34 | 99.3% R21, 反驳 lineage 循环假设 | `r34_n2_fresh_seed_hawe_verdict.md` |
| ANDES single-venv ≤ 3 并行 | R23 | 4+ → TDS internal stiffness mis-judge | `round_23_verdict.md` |

### §5.2 Abandoned (列论文 Future Work / Limitations)

| 方向 | Round | Abandon 理由 | 锚点 |
|---|---|---|---|
| Paper Eq.14 strict ($\varphi_d=1.0$) reproducibility | R04, R18-22 | 训到 ep75 必爆, 三 round 全失败 | `round_04_verdict.md`, `appendix_B_cross_platform_draft.md::B.5` |
| R21 hparam sweep (PHI_ABS/PHI_H/PHI_F) | R29 | 4 变体全 rank 35-55, SAC update 拉离 lucky basin | `round_28_to_34_final_verdict.md` §R29 |
| Reward shaping (PHI_MAX max_df, PHI_SETTLE) | R31, R33 | 4 变体全 rank 35-43, critic 偏 conservative near-zero | 同上 §R31/R33 |
| Stochastic ensemble (同 actor 采样 N 次) | R32 | rank 55-95, R21_stoch5 比 no_ctrl 还差 | 同上 §R32 |
| ZIP DynLoad v2 闭 LS2 residual | R29 | LS1=LS2 bit-identical, dispatch 失效 | `r29_zip_v2_verdict.md` |
| AGC § V-A closure | R25 | AGC 不 expose, ZIP config 不 propagate | `r25_agc_zip_probe_verdict.md` |
| Modal analysis 选 ckpt | R27 | low-score 投影更高, modal-align 假反 | `r27_modal_analysis_verdict.md` |
| V3 env governor (IEEEG1 + EXST1) | R08, R10 | DAE_INACTIVE, governor on/off diff = 0.000 | `round_08_verdict.md`, `round_10_verdict.md` |
| Phase A-E recovery plan | (写于 2026-05-07) | DRAFT, §Done Summary 空, 被 R28-R34 替代 | `quality_reports/plans/2026-05-07_andes_6axis_recovery.md` |
| ANDES NE39 训练 | (cross-route) | M₀ < 20 → TDS divergence; REGCA1 加 6 algebraic+state var DAE 膨胀 | `env/andes/andes_ne_env.py`, `andes_ne_regca1_env.py` |
| 8 ANDES 进程并行 | R23 | 单 venv ≤ 3, contention 上限 hard | `round_23_verdict.md` |

### §5.3 R21 0.613 复现失败链 (重点决策)

R21 `V4_h50_s49` 单 seed 6-axis 0.613 = **single-seed luck**, 不是可复现方法:

```
R21 (0.613, 1 seed) 
   ↓ multi-seed 复现 (R23 H₀ sweep)
R23 FAIL (8 并行 TDS crash, 0 ep)
   ↓ R23 v3 + 多 seed (R24)
R24 FAIL (其他 seed 全 0.13-0.22)
   ↓ 22 ckpt 试超 R21 (R23-R27)
R23-R27 ABANDON (没一个 >0.22)
   ↓ algorithm innovation (R28-R34)
   ├─ R28 warmstart finetune → 0.41-0.42 (3.8× no_ctrl) PASS
   ├─ R29 ZIP DynLoad v2 → ABANDON
   ├─ R30 ensemble w8515 → 0.554 PASS ⭐⭐ 当前 reproducible top
   ├─ R31 PHI_MAX shaping → FAIL
   ├─ R32 stochastic averaging → FAIL (worse)
   ├─ R33 PHI_SETTLE shaping → FAIL
   └─ R34 fresh-seed HAWE → 0.441 PASS (反驳 lineage)
```

**写论文锚点**: 论文 §3.5.1 multi-seed 验证 + §3.5.2 ensemble investigation + §3.6 Phase 12.

---

## §6 Failure Family F1-F6 + M1-M3

**6-axis evaluation 失败 + 3 方法论纠正.** 全在 `quality_reports/audits/2026-05-07_andes_6axis_failure_analysis.md`.

### §6.1 Failure Tree (F1-F6)

| ID | 现象 | 根因 |
|---|---|---|
| F1 | ΔH/ΔD range 70×/47× 偏小 (LS1 ΔH ~5 vs paper 350) | H₀=10 (Kundur 经典) → paper-literal ΔH=-100 物理不可行, 87% floor-clip; tanh 压缩到 [-1,1] |
| F2 | max\|Δf\| 3-4× 偏大 (0.41 Hz vs 0.13) | GENROU D=0 + GENCLS-only ESS 无 inner-loop damping + ESS 容量 31% + agent 调节力不足 |
| F3 | final\|Δf\|@6s 2.5× 偏大 (0.18 vs 0.08), 不收敛 | F2 欠阻尼 + load step 永久偏置导致频率永久偏差 (paper 6s 时已 settle 到稳态 0.08, 不是 0) |
| F4 | settling_s = ∞ (10s 内不收敛) | F2+F3 + actor stochastic 让 H/D step jump → 持续 perturb → 永远不 settle |
| F5 | ΔH/ΔD smoothness 锯齿 (std 2-22) | SAC stochastic Gaussian actor 每 step 重采样, deterministic eval 也学到不稳 mean, reward 无 smoothing penalty |
| F6 | cum_rf 假阳性 (-0.722 vs paper -0.68 = 6.2% "成功") | cum_rf 是 sync 偏差积分, 对 step-jitter 不敏感, agent stochastic action H/D 乱跳不影响 cum_rf |

### §6.2 Methodology Corrections (M1-M3)

| ID | 错误 | 修正 |
|---|---|---|
| M1 | 单维 metric (cum_rf) 选错, 任何单维都可被 cherry-pick | 改用 6-axis 几何均值, 任一轴 = 0 → overall = 0 |
| M2 | 论文图视觉量化滞后, 4 轮用粗估值 (max_df 0.12 / final_df 0.02) | 逐张 Fig.6/7/8/9 重读, 实际 final_df=0.08 residual 不是 0.02 |
| M3 | 训练失败被 cum_rf 掩盖, 没看 ΔH/ΔD 时序图 | release 协议必须看 Fig 7/9 时序, cum_rf 不区分 smooth control vs stochastic luck |

---

## §6.5 ⚡ QUICK LAUNCH (copy-paste, no context reading needed)

```bash
# ── WSL venv ──────────────────────────────────────────────────────
PYTHON=/home/wya/andes_venv/bin/python
REPO="/mnt/c/Users/27443/Desktop/Multi-Agent  VSGs"
SCRIPT=scenarios/kundur/train_andes_v4.py
RESUME=results/v4_h50_s49          # R21 best.pt (6-axis 0.444)
BASE_ARGS="--vsg-m0 100 --phi-abs 0 --phi-d 1.0"   # H0=50, match R21

# ── 单跑 (换 seed / save-dir) ─────────────────────────────────────
cd "$REPO"
nohup $PYTHON $SCRIPT --episodes 2000 --seed 49 --resume $RESUME \
  $BASE_ARGS --save-dir results/v4_ws_r21_2000ep_s49 \
  > logs/v4_ws_r21_2000ep_s49.log 2>&1 &
echo "PID=$!"

# ── GPU 版 (加 DEVICE=cuda) ───────────────────────────────────────
DEVICE=cuda nohup $PYTHON $SCRIPT --episodes 2000 --seed 52 --resume $RESUME \
  $BASE_ARGS --save-dir results/v4_ws_r21_2000ep_s52 \
  > logs/v4_ws_r21_2000ep_s52.log 2>&1 &

# ── 并行上限 = 3 个进程 (R23 硬限制, 4+ TDS crash) ───────────────
# ── 进度查看 ──────────────────────────────────────────────────────
# tail -f logs/v4_ws_r21_2000ep_s49.log
# ps aux | grep train_andes | grep -v grep
```

**关键路径速查**:
- 训练脚本: `scenarios/kundur/train_andes_v4.py` (V4 env, 不是 train_andes.py)
- 最优起点 ckpt: `results/v4_r21_best_resume/` ← **必须用这个** (best.pt 已 copy 为 final.pt)
  - ⚠ `results/v4_h50_s49/` 的 final.pt 是退化版本 (ep92), 用它 warmstart → ep80 action_collapse
- WSL venv: `/home/wya/andes_venv/bin/python` (Windows 端 andes 是误装, 不可用)
- nohup 在 `wsl -e bash -c "..."` 里**不持久化** (父 bash 退出会 kill 子进程); 解法: 写成 .sh 文件再 `bash script.sh`, 或者在 WSL 交互 shell 里直接跑
- 6-axis eval: `python evaluation/paper_grade_axes.py results/<dir>/`

---

## §7 Active State (2026-05-08)

### §7.1 Branch State

- **HEAD**: `2d9708e` on `main`
- **HEAD message**: `research-loop: R25-R36 — Path B forensic + ranker fix + DA-CRIT-1 refutation`
- **本地 branches**: 15 个 (含 worktree). 主要 active: `main` / `discrete-rebuild` / `disturbance-real-experimental`
- **远程**: `origin/main`, `origin/discrete-rebuild`, `origin/fix/governance-review-followups`

详见 `毕业论文/CONTEXT.md §3.4`. 本仓库非 main branch 的真实状态见该表.

### §7.2 Latest Handoff

`quality_reports/handoff/2026-05-07_user_sleep_status.md` (May 7 09:12, **最新**)

- **当前在做**: R23+R24 multi-seed 验证 + paper 战略修订
- **决策点 (用户 3 选 1)**:
  - A: paper 改诚实报告 mean 0.14, 0.613 移 footnote
  - B: CTDE / curiosity / reward shaping 突破 attractor (1-3hr)
  - C: 退 Simulink (不推荐)
- **关键 finding**: paper Eq.14 + SAC 真实 attractor ≈ 0.137, 0.613/0.325 都是 single-seed luck

**实际后续走向 (post-handoff)**: 选了 B 路 + ensemble (R28-R34), 拿到 R30 w8515 0.554 reproducible top.

### §7.3 Phase A-E Recovery Plan — Status

`quality_reports/plans/2026-05-07_andes_6axis_recovery.md` (DRAFT)

| Phase | 目标 | 当前 status |
|---|---|---|
| A | action smoothing (λ=0.01, INCLUDE_OWN_ACTION_OBS, target_entropy=-2) | **abandoned** (替代: R32 stoch ensemble 反实测变差) |
| B | IEEEG1 governor + EXST1 AVR | **broken** (V3 env wiring 失效, R08/R10 暴露) |
| C | H₀=50 baseline + ΔH/ΔD paper-literal range | **partial** (V4 改 H₀=100 paper-faithful, R21 lucky basin) |
| D | A+B+C 合并 V3 + 5 seed × 500 ep retrain | **bypassed** (R23-27 走 multi-seed 验证, R28-34 走 algorithm) |
| E | verdict + 文档 + figure | **完成** (实际由 R28-R34 final verdict 完成) |

**G1-G6 gates**: 全 TBD. Plan 整体 **实质 abandoned**, 被 R28-R34 algorithm sprint 替代.

---

## §8 ANDES Env Versions V1-V4

`env/andes/`:

| Env | 文件 | 关键参数 | 用途 / status |
|---|---|---|---|
| V1 | `andes_vsg_env.py` | H₀=10 homogeneous, paper Eq.14 baseline | 历史. R01-R05 attractor 0.037 主用 |
| V2 | `andes_vsg_env_v2.py` | H₀=10, D₀=(20,16,4,8) heterogeneous | 历史. Phase A 预期目标 |
| V3 | `andes_vsg_env_v3.py` | Phase B (governor) + C (H₀=50) 集成 | **broken** (governor wiring 失效, R08/R10), 已弃 |
| V4 ⭐ | `andes_vsg_env_v4.py` | H₀=100 paper-faithful, Eq.14 strict, $\varphi_d$ rescale 0.0056 | **当前主用**. R21 突破 / R23-R34 主线 |

跨拓扑:
- `andes_ne_env.py` — NE39 GENCLS, M₀<20 TDS divergence
- `andes_ne_regca1_env.py` — NE39 + REGCA1, 6 algebraic+state var DAE 膨胀, 不收敛
- `base_env.py` — 4 env 共享 step / reset / obs / reward

---

## §9 Sources Index

### §9A 写论文必查

**最终结果 verdict**:
- `quality_reports/research_loop/round_30_ensemble_verdict.md` ⭐⭐ — Phase 12 ensemble 0.554
- `quality_reports/research_loop/round_28_to_34_final_verdict.md` ⭐ — 6 family algorithm sprint
- `quality_reports/research_loop/round_24_verdict.md` ⭐ — R21 0.613 cherry-pick 推翻
- `quality_reports/research_loop/round_21_v4_breakthrough.md` — R21 historical winner
- `quality_reports/research_loop/round_10_to_17_unified_verdict.md` — V4 env baseline 建成

**Audits**:
- `quality_reports/audits/2026-05-07_andes_6axis_failure_analysis.md` — F1-F6 + M1-M3
- `quality_reports/audits/2026-05-07_andes_paper_alignment_root_cause.md` — paper-align 根因
- `quality_reports/audits/2026-05-07_ptdf_train_failure_postmortem.md` — PTDF + r_f cancel (Simulink 端 cross-route)

**Paper 锚点**:
- `docs/paper/andes_replication_status_2026-05-07_6axis.md` — 6-axis 真实状态
- `paper/appendix_B_cross_platform_draft.md::B.5` — Eq.14 strict 不可复现
- `paper/figures/ranking_bar.png` — V4_h50_s49 outlier 标注

### §9B 写代码必查

**Env / training**:
- `env/andes/andes_vsg_env_v4.py` — 当前主线 env
- `scenarios/kundur/NOTES_ANDES.md` — 修代码必读 NOTES (R10-R17 沉淀)
- `probes/andes_common/README.md` — probe utility 复用层决策树
- `probes/andes_common/{paper_constants,tracers,verdict,utils}.py` — 760 LOC reusable

**Eval (single source of truth)**:
- `scripts/research_loop/eval_paper_spec_v2.py` — ANDES eval 单一入口 (L4 lock-in)
- `evaluation/paper_grade_axes.py` — 6-axis 量化函数
- `paper/figure_scripts/figs6_9_ls_traces.py` — Fig 6/7/8/9 生成

**Ensemble**:
- `scripts/research_loop/eval_v4_ensemble.py:53` — `ensemble_action()` 实现

**Run env (重要)**:
- ANDES 必走 **WSL**, 见 `CLAUDE.md` § ANDES 运行环境

### §9C Archival (核 fact 用)

- `quality_reports/research_loop/handoffs/INDEX.md` — handoff 索引 (空, scripts/research_loop/handoff_index.py 维护)
- `quality_reports/handoff/2026-05-07_user_sleep_status.md` — 最新 handoff
- `quality_reports/plans/2026-05-07_andes_6axis_recovery.md` — Phase A-E plan (abandoned)
- `quality_reports/plans/2026-05-06_disturbance_real_loadstep.md` — Simulink LoadStep 5-method failure history
- `docs/paper/yang2023-fact-base.md` — paper 主索引
- `docs/paper/v3_paper_alignment_audit.md` — v3 align audit

### §9D 不要去的目录

- `scenarios/kundur/_legacy_2026-04/` — 老 ANDES eval 入口已归档, 不要复用
- `probes/kundur/archive/2026-04-sps-investigation/spike/` — Simulink SPS spike, ANDES 无关
- `results/` (根目录) — 2026-04-06 已清, 只剩 `results/harness/`
- Windows 端 `C:/Users/27443/miniconda3/python.exe` 的 andes — 历史误装, 不可信任

---

## §10 毕业论文/plan/ 文档生态

**46 文件, 论文重写主线 + ANDES algorithm sprint 衍生物**. 路径 = `毕业论文/plan/` (注意: 不在 Multi-Agent VSGs/ 内, 是论文仓库).

⭐ = 必读. 文件按主题分组.

### §10.1 索引 / 导航层 ⭐

| 文件 | 用途 |
|---|---|
| `2026-05-07_MASTER_INDEX.md` ⭐ | Stage 2 ANDES Algorithm Sprint 总索引 (R28-R37 / 8 family / 50+ variant). 含 figures / source code changes / spec status / abstract draft |
| `2026-05-07_evidence_pack_navigation.md` ⭐ | 16 evidence pack (EP-A1/A2/B1-4/C1-4/D1-4/E1-2) 导航. 按命题类型分组, 不按章节分组 |

### §10.2 Handoff 链 (时间序)

| 文件 | 时点 | 内容 |
|---|---|---|
| `2026-05-07_handoff_v12.md` | v12 | page 91 lock state |
| `2026-05-07_handoff_v13.md` | v13 | Path B 启动 |
| `2026-05-07_handoff_v14.md` ⭐ | v14, **最新** | Path B 第一轮 forensic 完成. 8 计划 5 done. **ranker fix 后 0.613 → 0.444** |
| `2026-05-07_HANDOFF_REWRITE_ANDES_CENTRIC.md` | 重写决策 | dissertation 转 ANDES-success-led, HAWE 升 5 bespoke asset 之一 |
| `2026-05-07_INTEGRATION_HANDOFF.md` | 集成 | Sprint 输出 → main.tex 集成路径 |
| `2026-05-07_user_sleep_status.md` | (在 Multi-Agent VSGs 仓库 quality_reports/handoff/) | 见 §7.2 |

### §10.3 ANDES Algorithm Sprint 突破文档

| 文件 | 时点数字 | 关键 |
|---|---|---|
| `2026-05-07_andes_breakthrough_update.md` | R30 0.554 (early) | first ensemble breakthrough memo (v1) |
| `2026-05-07_andes_breakthrough_FINAL.md` ⭐ | R36 w9802 0.607 (mid) | 8 family final memo (pre-ranker-fix). 被 v14 ranker fix 后再次推翻 |
| `2026-05-07_R21_HEADLINE_REVISION.md` | (R21 outlier 推翻) | R21 0.613 single-seed luck 论证 |
| `2026-05-07_FINAL_CONSOLIDATED.md` | (合并) | breakthrough + 推翻全集 |
| `2026-05-07_path_B_execution.md` | path B plan | priority list (B-1.5 / B-2 / B-4 / B-6) |

### §10.4 Per-agent / Cookbook / LaTeX patches

| 文件 | 用途 |
|---|---|
| `2026-05-07_per_agent_contribution_analysis.md` | 9 节 per-agent 分析, EP-B3 输入材料 |
| `2026-05-07_reproducibility_cookbook.md` | Appendix A 复现 recipe (双仓库) |
| `2026-05-07_LATEX_PATCHES_READY.md` ⭐ | Section A-H ready-to-paste main.tex patch (~500 行) |
| `2026-05-07_paper_revision_punchlist.md` | 论文修订打点列表 |
| `2026-05-07_paper_editors_brief.md` | editor 视角 brief |

### §10.5 Evidence Packs 16 个 ⭐

路径 = `毕业论文/plan/evidence/`. 按 5 group:

**Group A — Core Reproduction Results (2 个)**
- `EP-A1.md` ⭐ — Stage 1 TD3 复现 (39% > 33% paper), 主对话 Stage 1 finding
- `EP-A2.md` ⭐ (🟢 v1 post-fix) — Stage 2 ANDES R21 best-trained result, **post-r30/N1c ranker fix headline 0.444 / HAWE 0.439 / 99.3% recovery**, multi-seed cherry-pick 推翻 + cross-platform residual disclose

**Group B — Engineering Design Decisions (4 个)**
- `EP-B1.md` — Backend Selection (ODE → Simulink → ANDES) progression
- `EP-B2.md` — Reward & Objective Evolution (M1 φf rebalance / M2 D-floor / M3 dominance fix). ⚠ 与 D1 命名碰撞 (`M1-M3`)
- `EP-B3.md` — Architecture Ablation (Phase7 per-agent / Phase9 shared-SAC / Phase10 warmstart)
- `EP-B4.md` — Hyperparameter Sensitivity Sweep (3 robustness gate fail)

**Group C — Bespoke Transferable Assets (5 个, v16 升级)**
- `EP-C1.md` ⭐ — MCP Simulink Toolkit (3 layer / 45 tool / ~3,300 LOC), Asset 1
- `EP-C2.md` — Simulink-as-RL-Environment Bridge (5 design choice / 35-70ms step), Asset 2
- `EP-C3.md` — TDD-Inspired Diagnostic Probe Layer (~760 LOC ANDES infra), Asset 3
- `EP-C4.md` ⭐ — Six-Axis Evaluation Framework (geo-mean holistic gate, R06→R07 audit-driven, post-fix patched), Asset 4
- `EP-C5.md` ⭐⭐ (v16 升级) — **HAWE Heterogeneous Actor Weighted Ensemble** (inference-time, no retrain, 99.3% R21 recovery, structural diversity insight, 600× ROI), Asset 5

**Group D — Failures & Abandoned Routes (4 个)**
- `EP-D1.md` ⭐ — F1-F6 6-Axis Failure Root-Cause Tree
- `EP-D2.md` ⭐ — 5-Method LoadStep Path-Blocker (deepest engineering finding)
- `EP-D3.md` — PTDF Train Failure Postmortem (destructive interference w/ paper r_f)
- `EP-D4.md` — Abandoned Routes Consolidated (Kundur family + SMIB + NE39×2 + V1-V4 + branches + ODE)

**Group E — Process & Reflection (2 个)**
- `EP-E1.md` — PI-TD3 Pivot + 12 Internal Phases + 5 methodology changes
- `EP-E2.md` — AI 4-Role Collaboration (Launcher/Monitor/Observer/Evaluator + 3-layer Track)

`evidence/_template.md` = pack 标准模板 (8 字段必含).

⚠ **命名碰撞** (集成时必须 fix):
- M1-M3: D1 (eval methodology errors) vs B2 (reward redesign). 建议 D1 改为 ME1-ME3
- F1 / Phase 1: D1 F1 (ΔH/ΔD range) vs E1 Phase 1 (Stage 2 内部阶段)

### §10.6 ANDES IEEE Paper 草稿

| 文件 | 用途 |
|---|---|
| `2026-05-07_andes_ieee_paper.md` | ANDES 单论文 draft (post-ranker-fix v2). 重要: 数字用 0.444 不是 0.613 |
| `2026-05-07_andes_ieee_paper_REVIEW.md` | 自评 review |

### §10.7 5-Reviewer 审稿模拟

`plan/2026-05-07_5reviewer/`:

| 文件 | 角色 |
|---|---|
| `01_eic_report.md` | EiC (Editor-in-Chief) |
| `02_methodology_report.md` | Methodology reviewer |
| `03_domain_report.md` | Domain expert reviewer (DA-CRIT-1 lineage / DA-CRIT-2 LS2 settling 在此提出) |
| `04_perspective_report.md` | Perspective reviewer |
| `05_devils_advocate_report.md` | Devil's advocate |
| `06_editorial_decision.md` | 综合决议 |

### §10.8 论文写作 plan (主线)

| 文件 | 状态 |
|---|---|
| `2026-05-07_thesis_writing_plan.md` | v1, 历史 |
| `2026-05-07_thesis_writing_plan_v2.md` | v2, chapter mapping |
| `2026-05-08_thesis_rewrite_andes_centric_plan.md` ⭐ | **当前主线 plan**. ANDES-success-led 重写, L1-L14 锁定决策, 60-75 页, headline 0.444 |

### §10.9 其他

| 文件 | 用途 |
|---|---|
| `2026-05-07_multi_conv_plan.md` | 多对话并行计划 |
| `2026-05-07_research_philosophy_lessons.md` | research philosophy 7 lesson 早期版本, 已 fold 进 §3.8 论文 CONTEXT |

---

## §11 数字版本时间线 ⚠

**ANDES 6-axis score 在 2026-05-07 之内被推翻 4 次**. 写论文必须用 **post-fix L3 锁定数字**.

### §11.1 时间线

| 时点 | 事件 | R21 | HAWE w9802 | no_ctrl | Source |
|---|---|---|---|---|---|
| ~R21 (历史) | V4_h50_s49 single-seed luck | **0.613** | (n/a) | 0.110 | `round_21_v4_breakthrough.md` |
| 2026-05-07 早 | R30 first ensemble (w8515) | 0.613 | (w8515 = 0.554) | 0.110 | `round_30_ensemble_verdict.md` |
| 2026-05-07 ~13:00 | R36 fine-grained R21 weight sweep, 8 family final | 0.613 | **0.607** (98/2 sweet spot) | 0.110 | `2026-05-07_andes_breakthrough_FINAL.md` |
| 2026-05-07 后 (Path B) | r30 ranker audit + N1c fix (geo-mean across scenarios + NaN/tds_failed guards) | **0.444** | **0.439** | **0.104** | `r30_ranker_audit_verdict.md`, `2026-05-07_handoff_v14.md` §1 |
| 2026-05-07 后 | R34 fresh-seed HAWE (s50/s51/s52) | n/a | **99.3% R21** (fresh seed, lineage independent) | n/a | `r34_n2_fresh_seed_hawe_verdict.md` |
| 2026-05-08 | L3 锁定: 论文 headline = 0.444, 不是 0.613 | **0.444** | **0.439** | **0.104** | `2026-05-08_thesis_rewrite_andes_centric_plan.md` L3 |

### §11.2 论文 headline 用哪个

**论文 (dissertation) 用**: R21 = **0.444** (4.04× no_ctrl), HAWE = **0.439**, no_ctrl = **0.104**.

理由:
- r30 ranker fix 是 bug fix, 不是 design change. 旧 0.613 是 ranker 缺 geo-mean across scenarios + NaN guard 的 inflated 数字
- 用 0.613 是 **retracted-number error** (L3 决策原文)
- HAWE 99.3% recovery 仍成立 (fresh-seed 反驳 lineage 循环, R34)

### §11.3 各文档数字版本对照

| 文档 | 用的版本 | 是否需要修订 |
|---|---|---|
| `2026-05-07_andes_breakthrough_update.md` | R30 v1 (0.554) | 已 superseded by FINAL |
| `2026-05-07_andes_breakthrough_FINAL.md` | R36 mid (0.607) | **过期**, 被 ranker fix 推翻 |
| `2026-05-07_MASTER_INDEX.md` | R36 mid (0.607) | **过期**, headline 0.607 应改 0.439 |
| `2026-05-07_handoff_v14.md` | post-fix (0.444 / 0.439) | ✅ 当前正确 |
| `2026-05-07_andes_ieee_paper.md` v2 | post-fix (0.444) | ✅ 当前正确 |
| `2026-05-08_thesis_rewrite_andes_centric_plan.md` | post-fix (0.444) | ✅ 当前正确, L3 锁定 |
| 本文档 (`Multi-Agent VSGs/CONTEXT.md`) | post-fix (0.444 / 0.439) | ✅ 当前正确 |
| `毕业论文/CONTEXT.md` v15 | R30 (0.554) | ⚠ **需校核** — v15 写于 2026-05-08 但用的是 R30 数字, 可能已过期 |

### §11.4 校验入口

ANDES eval **single source of truth**:
- 入口: `scripts/research_loop/eval_paper_spec_v2.py` (L4 lock-in 2026-05-07)
- Ranker 函数: `evaluation/paper_grade_axes.py` (post-fix patched, geo-mean + nan/tds guards)
- 任何数字怀疑 → 重跑 ranker 验证. 不要相信旧 verdict 文件里的数字.

---

## §12 Cross-ref to 论文 CONTEXT.md

本文档关注 **ANDES 工程迭代**. 论文 finding / SPEC / 章节状态见:

`C:\Users\27443\Desktop\毕业论文\CONTEXT.md`

| 论文 CONTEXT 节 | 对应本文档 |
|---|---|
| §2 Anti-Patterns 主表 | §2 (本文档补 ANDES 独有 12 条) |
| §3.2 Stage 2 facts | §1 TL;DR + §3 Phase Timeline |
| §3.3 Simulink LoadStep | (Simulink track, 本文档不涉) |
| §3.4 Branch 真实状态 | §7.1 |
| §3.6 Training Management 4 Roles | (跨仓库 infra, 本文档不重复) |
| §3.8 Engineering Philosophy | (项目级 lesson, 不在工程地图重复) |
| §9.1-§9.4 Latest Verifications | 本文档 §3 Phase 12 + §6 Failure Tree + §7.3 Phase A-E |

**单一 fact 源**: 数字以 verdict 文件为准. 两 CONTEXT 都是索引层.

---

## §13 维护规则

- **ANDES 主线即将冻结** (2026-05-08 用户决议). 此文档为收尾 snapshot, 不预期大修
- 新 verdict 出现 (R37+) → 加 §4 Round Table + §3 Phase 时间线 (如开 P13)
- 决策分支变化 → 加 §5
- Branch 状态变化 → §7.1
- 论文章节移动 → 不更新本文档, 更新 `毕业论文/CONTEXT.md`
- caveman 中文风格保持

每次更新写日期戳:
```
[2026-XX-XX] <one line change>
```

[2026-05-08] v1 initial: ANDES 端事实地图建成, 36 round / 12 phase / 7 abandon 路径 / F1-F6 + M1-M3 全 evidence-anchor
[2026-05-08] v1.1: 加 §10 plan/ 文档生态 (46 文件, 16 EP + handoff 链 + 5-reviewer + ANDES IEEE 草稿) + §11 数字版本时间线 (R21 0.613 → ranker fix 后 0.444, L3 锁定). §1 TL;DR 校正 headline 为 0.444 而非 0.554

---

*EOF — v1.1 / 37 round / 12 phase / post-ranker-fix R21=0.444 HAWE=0.439 / ANDES freeze pending / caveman*
