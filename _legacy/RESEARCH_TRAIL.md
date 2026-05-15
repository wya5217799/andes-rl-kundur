# RESEARCH_TRAIL — ANDES 因果链导航 (caveman, AI-consumer)

**Last full-rewrite**: v1 / 2026-05-08
**Status**: ⚠ ANDES 主线即将冻结, 此文档为收尾 snapshot
**Audience**: ⚠ **消费者 = AI**. 高密度表格, 一致 token, 精确锚点, 无寒暄
**Scope**: ANDES Stage 2 因果链 R01→R37 + 6 拐点 + commit map + 论文章节 type filter
**Reading mode**: §2 ASCII tree (60s) → §3 trail 表 (3min) → §4/§5 按需深入

---

## §0 Token Spec (AI 读取时按此 grep)

### Type tokens (方括号)
| Token | 含义 | 例 |
|---|---|---|
| `[DIAG]` | 诊断 / audit / forensic / probe (不改代码不训) | R06 attractor audit, R10 IEEEG1 forensic, r30 ranker audit |
| `[BUILD]` | 代码改 (env / ranker / inference algo / probe util) | R07 axes.py fix, R10-17 V4 env, ranker N1c geo-mean fix |
| `[TRAIN]` | 训练 (single / multi-seed / sweep / retrain / warmstart / fresh-seed) | R02 200ep×5seed, R21 V4 75ep, R28 warmstart, R34 fresh-seed |
| `[INFER]` | inference-time algo (无 retrain, 用已训 ckpt) | R30 HAWE 加权, R32 stochastic averaging |
| `[EVAL]` | re-eval / re-rank / 数字校正 (不动代码不训) | R07 重 eval R05 ckpt, post-fix re-rank 121 ckpt |
| `[VALID]` | 验证 / 反驳 / cross-check (统计 / 反例) | R34 fresh-seed 反 lineage, R33 Spearman 验 §VI-D |

复合用 `+` 拼: `[DIAG+BUILD]`, `[BUILD+INFER+EVAL]`.

### Verdict tokens
`PASS` / `FAIL` / `PIVOT` / `ABANDON` / `MIXED` / `INVALID`

### Trust tokens (引用 ANDES CONTEXT §0)
`[V]` verified / `[S]` speculative / `[T]` todo-verify / `[C]` corrected

---

## §1 TL;DR 因果总览 (1 段)

**12 phase, 6 拐点, 37 round, 3 day commit window (2026-05-04 ~ 2026-05-07)**.

P1-P5 attractor 0.037 (8 dim 全卡, 8e46248-8709884) → **拐点 1: R06 [DIAG] axes.py Bug-A** (0513b23) → P3-P4 修 ranker [BUILD] (9bc7a08) → 0.037→0.139 → P5 R08 governor 验证 [DIAG] (7af7c19) → V3 governor 死 → ANDES path closure (81dd629) → **拐点 2: R10-R17 [DIAG+BUILD] forensic** 找 4 bug + V4 env 重建 → P9 R21 [TRAIN] V4 75ep multi-seed → **拐点 3: V4_h50_s49 0.613 lucky single** → P11 R23-R27 [TRAIN] multi-seed 复现 → **拐点 4: R24 [VALID]** 22 ckpt 全 ≤ 0.22, R21 outlier → P12 R28-R34 [TRAIN+INFER] 6 family algorithm sprint → **拐点 5: R30 [BUILD+INFER] HAWE 0.554 (pre-fix)** → R34 [TRAIN+VALID] fresh-seed 99.3% recovery 反 lineage 循环 → **拐点 6: r30 [DIAG+BUILD+EVAL] ranker fix N1c** geo-mean across scenarios + NaN/tds_failed guard → R21 0.613→0.444, HAWE 0.607→0.439, no_ctrl 0.110→0.104 → 论文 L3 锁定 headline = 0.444.

---

## §2 主因果链 (ASCII tree)

```
P1-P5 attractor 0.037 (8 dim 全卡)
  │ R01 [TRAIN] LAMBDA_SMOOTH std collapse
  │ R02 [TRAIN] 200ep×5seed lam=0.01 final_R 60% std 4.88
  │ R03 [TRAIN] 500ep+obs9+governor → 0.036
  │ R04 [TRAIN] PHI_D=1.0 paper-aligned → 0.037
  │ R05 [TRAIN] 8-arm bandit → 8 全 0.037 attractor
  ↓
拐点 1: R06 [DIAG] ⭐ 4 sub-exp parallel (0513b23, 2026-05-06)
  │ exp0: attractor 性质 = action range starvation
  │ exp1: axes.py Bug-A range axis 公式语义反 (box bound 当 trajectory span)
  │ exp2: action box 偏小 100×, 不是 1000×
  │ exp3: disturbance 实为 -2.48/+1.88 sys_pu
  ↓
P3-P4 修 ranker
  │ R07 [BUILD+EVAL] 修 axes.py 25 LOC (9bc7a08) → 0.037→0.139 (3.76×)
  │ R08 [DIAG+TRAIN] H scan + V3 governor 验证 (7af7c19) → V3 governor on/off diff = 0.000 → 死的
  ↓
ANDES path closure (81dd629, 2026-05-06)
  ↓ [推翻]
拐点 2: R10-R17 [DIAG+BUILD] ⭐ ANDES 4 bug forensic
  │ R10 [DIAG] IEEEG1 整 model DAE_INACTIVE (ss.add 时序错)
  │ R10-13 [DIAG] PI-AC J=1e-7 数值精度死, CTDE 1.10× param OK, settling NO_SIGNAL
  │ R14-16 [DIAG] H scan + G4 inertia + LINE_X probe
  │ R17 [BUILD+TRAIN] V4 env 创建 → LS1 max_df 0.51→0.26, settled 0.088 = paper 0.080 1.10×
  │ post: DT bug fix (numpy ref → value-copy, 0.6s/step → 0.2s/step paper-faithful)
  ↓
P7-P8 V4.1 reward audit
  │ R18 [BUILD] PHI_H/D 1.0 → 0.0056 (除 178 = action range expansion)
  │ R19 [DIAG] WF2 not cause
  │ R20 [DIAG+TRAIN] reward paradox confirmatory probe
  ↓
拐点 3: R21 [TRAIN] ⭐ V4_h50_s49 0.613 (post DT-fix + V4 + 75ep)
  │ LS1 final_df 0.078 vs paper 0.080 = 97% match
  │ LS1 max_df 0.185 vs paper 0.13 = 1.42× cross-platform residual
  │ 历史 V2 attractor 0.036 的 17×
  │ ANDES path closure RE-OPENED → COMPLETED
  ↓
P10-P11 复现尝试
  │ R22 [TRAIN] V4.2 PHI 三路 retrain → 0.30 比 V4.1 0.22 更差
  │ R23 [TRAIN] H₀ sweep 8 并行 ANDES TDS crash 0 ep
  ↓
拐点 4: R24 [VALID] ⭐ R23 v3 + 多 seed 综合 (2026-05-07)
  │ H₀=50 multi-seed: s42 0.137 / s44 0.136 / s49 0.613
  │ s49 = 6× outlier vs same H₀ same seed family
  │ 22 ckpt 全 ≤ 0.22, 0.613 不可复现, paper main 不可投
  │ 真实 attractor ≈ 0.137, 仅 V1 0.037 的 3.7×
  ↓
P11 sweep abandon
  │ R23-R27 [TRAIN] 22 ckpt sweep 全 ≤0.22
  │ R25 [BUILD+TRAIN] AGC + ZIP probe → AGC 不 expose / ZIP config 不 propagate
  │ R26 [INFER] SWA / model-soup → SWA w98 = HAWE sweet spot
  │ R27 [DIAG] modal analysis → 反相关 (low-score 投影更高)
  ↓
P12 algorithm sprint (R28-R34, 2026-05-07 ~10:00 → 14:30)
  │ R28 [TRAIN] warmstart from R21 → 0.41-0.42 reproducible ceiling
  │ R28' [DIAG] R21 LS2 settling = 6.8s 不是 ∞, ranker 6s truncate bug 找
  │ R29 [TRAIN] hparam sweep 4 var → 全 rank 35-55, SAC update 拉离 R21 basin
  ↓
拐点 5: R30 [BUILD+INFER+EVAL] ⭐⭐ HAWE 突破 (pre-ranker-fix)
  │ a_i = sum_k w_k pi_k(o_i) at inference, no retrain
  │ w8515 = 0.554 (5.04× no_ctrl), w9802 sweet spot 0.607
  │ insight: structural actor diversity 不是 action variance averaging
  ↓
R31-R33 [TRAIN] reward shaping 全失败
  │ R31 PHI_MAX max_df 直罚 → 4 var 全 rank 35-43 conservative no-action
  │ R33 PHI_SETTLE settling 罚 → 同 R31 机制
  │ R32 [INFER] stochastic averaging → R21_stoch5 rank 95 worst
  ↓
R34 [TRAIN+VALID] ⭐ fresh-seed (s50/s51/s52) HAWE
  │ 单 fresh seed: 0.134-0.194 (vanilla attractor class)
  │ HAWE R21+freshN 98/2: 0.441 = 99.3% R21 (lineage-bound 0.439 = 98.9%)
  │ DA-CRIT-1 lineage 循环 REJECTED, basin 在 action-space 宽足够容忍 ANY 2% perturbation
  ↓
拐点 6: r30 [DIAG+BUILD+EVAL] ⭐⭐ ranker audit + N1c fix (2d9708e, 2026-05-07)
  │ C1 inconsistency: 同 evaluator 内 axes 用 geo-mean 但 scenarios 用 arith-mean
  │ C2.1 缺 NaN guard
  │ C2.2 缺 tds_failed check
  │ Fix: 一行改 arith-mean → geo-mean + NaN/tds_failed guard
  │ Re-rank 121 ckpt: R21 0.613→0.444, HAWE 0.607→0.439, no_ctrl 0.110→0.104
  ↓
论文 L3 锁定 (2026-05-08): headline = 0.444 (4.04× no_ctrl), HAWE 0.439 = 99.3% R21
  └ HAWE 升 5 bespoke asset 之一 (Asset 5)
  └ ANDES 主线冻结
```

---

## §3 详细 Trail R01-R37

⚠ **数字反映 verdict 当时**, post-ranker-fix headline 见拐点 6.
锚点路径相对 `Multi-Agent VSGs/`.

| R# | TYPE | commit | date | P# | verdict | 一句话 | →next | 锚点 |
|---|---|---|---|---|---|---|---|---|
| R01 | TRAIN | `8e46248` | 05-06 | P1 | MIXED | LAMBDA_SMOOTH 三档 std collapse 0.18, λ 三档差<1% | R02 | `quality_reports/research_loop/round_01_verdict.md` |
| R02 | TRAIN | `8e46248` | 05-06 | P2 | MIXED | 200ep×5seed lam=0.01 final_R 改善 60%, std 4.88 | R03 | `round_02_verdict.md` |
| R03 | TRAIN | `8e46248` | 05-06 | P2 | FAIL | 500ep+obs9+governor → 6-axis 0.036 ≈ no_ctrl | R04 | `round_03_verdict.md` |
| R04 | TRAIN | `8709884` | 05-06 | P2 | FAIL | PHI_D=1.0 paper-aligned 200ep → reward 退步 130%, 0.037 | R05 | `round_04_verdict.md` |
| R05 | TRAIN | `8709884` | 05-06 | P2 | ABANDON | 8-arm bandit 跨维度 → 8 臂全卡 0.037 attractor | R06 | `round_05_verdict.md` |
| **R06** ⭐ | DIAG | `0513b23` | 05-06 | P3 | PIVOT | 4 sub-exp parallel: axes.py Bug-A 公式反 + action box 偏小 100× + disturbance -2.48/+1.88 | R07 | `round_06_verdict.md`, `audits/2026-05-07_eval_formula_audit.md` |
| R07 | BUILD+EVAL | `9bc7a08` | 05-06 | P4 | MIXED | 修 axes.py 25 LOC, attractor 0.037 → 0.139 (3.76×, 仍 4× paper) | R08 | `round_07_verdict.md`, `evaluation/paper_grade_axes.py` |
| R08 | DIAG+TRAIN | `7af7c19` | 05-06 | P5 | FAIL | H scan + V3 governor on/off diff = 0.000, V3 = V2 完全相同, governor 死的 | R10 | `round_08_verdict.md` |
| (R09) | — | `81dd629` | 05-06 | P5 | (path closure) | ANDES path closure 决议 (后被 R10 推翻) | (re-open) | `2026-05-07_andes_path_closure.md` |
| **R10** ⭐ | DIAG | `2d9708e` | 05-07 | P6 | FAIL | governor wiring 4-layer forensic: IEEEG1 整 model DAE_INACTIVE (ss.add 时序错) | R11-13 | `round_10_verdict.md` |
| R11-13 | DIAG | `2d9708e` | 05-07 | P6 | MIXED | PI-AC J=1e-7 数值死 / CTDE 1.10× param FEASIBLE / settling NO_SIGNAL | R14 | `round_11_13_mvv_verdict.md` |
| R14-17 | DIAG+BUILD+TRAIN | `2d9708e` | 05-07 | P6 | PASS | V4 env 创建 (M0=200, gov active, G4 paper); V4 LS1 max_df 0.51→0.26 (49% 改善), settled 0.088 = paper 0.080 1.10× | R18 | `round_10_to_17_unified_verdict.md` |
| (post-V4) | DIAG+BUILD | `2d9708e` | 05-07 | P6 | CRITICAL | DT bug fix: `current_t = float(self.ss.dae.t)` numpy ref → value-copy, 0.6s/step → 0.2s/step paper-faithful (R10-17 数字 invalidate) | (re-test) | `env/andes/base_env.py` step() |
| R18 | BUILD | `2d9708e` | 05-07 | P7 | PASS | PHI_H/D 1.0 → 0.0056 (÷ 178 = action range expansion) 防 reward divergence | R19 | `quality_reports/handoff/2026-05-07_v4_session_handoff.md` |
| R19 | DIAG | `2d9708e` | 05-07 | P7 | NEUTRAL | WF2 (Bus 8 zero-inertia) probe → diff 0.0/0.1%, NOT cause | R20 | (R10-17 unified) |
| R20 | DIAG+TRAIN | `2d9708e` | 05-07 | P8 | MIXED | reward paradox confirmatory: settled max\|Δω\|≥0.05 + r_f<0.5 PASS, ΔH 非对称偏移 | R21 | `round_20_verdict.md` |
| **R21** ⭐ | TRAIN | `2d9708e` | 05-07 | P9 | PASS | V4 75ep multi-seed → V4_h50_s49 0.613, LS1 final_df 0.078 vs paper 0.080 = 97% match, 17× V2 attractor | R22 | `round_21_v4_breakthrough.md` |
| R22 | TRAIN | `2d9708e` | 05-07 | P10 | FAIL | V4.2 PHI_ABS/PHI_D 三路 retrain → A/B/C 全 max_df 0.30 比 V4.1 0.22 更差 | R23 | `round_22_verdict.md` |
| R23 | TRAIN | `2d9708e` | 05-07 | P11 | FAIL | H₀ sweep 8 并行 ANDES TDS crash, 0 ep, 单 venv 上限 ≤ 3 进程 | R24 | `round_23_verdict.md` |
| **R24** ⭐ | VALID | `2d9708e` | 05-07 | P11 | FAIL | R23 v3 + 多 seed 综合: H₀=50 multi-seed s42/s44 = 0.136-0.137, s49 = 0.613 (6× outlier); 22 ckpt 全 ≤ 0.22 | R23-27 | `round_24_verdict.md` |
| R23-27 | TRAIN | `2d9708e` | 05-07 | P11 | ABANDON | 5 轮 sweep 22 ckpt 试超 R21 → 没一个 >0.22, R21 不可复现 | R28 | `round_23_to_27_summary_verdict.md` |
| R25 | BUILD+TRAIN | `2d9708e` | 05-07 | P11 | FAIL | AGC + ZIP load probe 闭 LS2 gap → AGC 不 expose, ZIP config 不 propagate, paper §V-A AGC closure 路线废 | (skip) | `r25_agc_zip_probe_verdict.md` |
| R26 | INFER | `2d9708e` | 05-07 | P11 | MIXED | SWA / model-soup baseline → SWA w98=0.442 ≈ HAWE 0.439 sweet spot, 1-12% off-sweet 优势 | (note) | `r26_swa_baseline_verdict.md` |
| R27 | DIAG | `2d9708e` | 05-07 | P11 | FAIL | Kundur V4 modal analysis → low-score 投影更高, modal-align 假反 (Domain M2 REJECTED) | (drop) | `r27_modal_analysis_verdict.md` |
| R28 | TRAIN | `2d9708e` | 05-07 | P12 | PASS | warmstart from R21 ckpt finetune → reproducible ceiling 0.41-0.42 (3.8× no_ctrl) | R29 | `round_28_warmstart_verdict.md` |
| R28' | DIAG | `2d9708e` | 05-07 | P12 | PASS | R21 LS2 settling = 6.8s 不是 ∞, ranker 6s truncate bug 找 (H2 confirmed) | (ranker fix) | `r28_r21_settling_verdict.md` |
| R29 | TRAIN | `2d9708e` | 05-07 | P12 | FAIL | hparam sweep PHI_ABS/PHI_H/PHI_F 4 var → 全 rank 35-55, SAC update 拉离 R21 lucky basin | R30 | `round_28_to_34_final_verdict.md` §R29 |
| **R30** ⭐⭐ | BUILD+INFER+EVAL | `2d9708e` | 05-07 | P12 | PASS | HAWE: a_i = Σw_k π_k(o_i) at inference, no retrain; w8515 = 0.554, w9802 = 0.607 (sweet spot, 99% R21 0.613) | R31 | `round_30_ensemble_verdict.md`, `scripts/research_loop/eval_v4_ensemble.py:53` |
| R30' | DIAG+BUILD+EVAL | `2d9708e` | 05-07 | P12 | PASS | C1 fix (geo-mean across scenarios) + C2 fix (NaN/tds_failed guards) → re-rank 121 ckpt | R31 | `r30_ranker_audit_verdict.md` |
| R31 | TRAIN | `2d9708e` | 05-07 | P12 | FAIL | reward shaping PHI_MAX max_df 直罚 4 var → 全 rank 35-43, conservative no-action 摧毁 R21 basin | R32 | (R28-R34 final) §R31 |
| R32 | INFER | `2d9708e` | 05-07 | P12 | FAIL | stochastic averaging 同 actor 采样 N 次 → R21_stoch5 rank 95 worst (0.106 < no_ctrl 0.110), 噪声拉出 basin | R33 | (R28-R34 final) §R32 |
| R33 | TRAIN+VALID | `2d9708e` | 05-07 | P12 | PASS | reward shaping PHI_SETTLE → 同 R31 机制; **同时**: Gini-vs-score Spearman ρ=+0.530 CI[+0.257,+0.731] N=46 验 §VI-D | R34 | `r33_gini_vs_score_verdict.md`, (R28-R34 final) §R33 |
| **R34** ⭐ | TRAIN+VALID | `2d9708e` | 05-07 | P12 | PASS | fresh-seed (s50/s51/s52) HAWE 98/2 → 99.3% R21 recovery, lineage-bound 98.9%, DA-CRIT-1 lineage 循环 REJECTED | R35 | `r34_n2_fresh_seed_hawe_verdict.md` |
| R35 | EVAL | `2d9708e` | 05-07 | P12 | PASS | per-axis × per-controller breakdown for Table III → 3 轴=1, 1 轴=0, 仅 max_df + LS2 final_df 区分 | R36 | `r35_per_axis_breakdown_verdict.md` |
| R36 | EVAL | `2d9708e` | 05-07 | P12 | MIXED | ranker tuning 4-variant sensitivity → order 稳定, R21/no-ctrl 3.08× - 4.26× | R28-34 | `r36_ranker_tuning_verdict.md` |
| **R28-34** ⭐⭐ | (sprint) | `2d9708e` | 05-07 | P12 | PASS | 6 family / ~50 variant / 2 hr wall: 仅 R30 ensemble 破 0.42 ceiling; 4 path-blocker 全失败 | (frozen) | `round_28_to_34_final_verdict.md` |
| **ranker fix** ⭐⭐ | DIAG+BUILD+EVAL | `2d9708e` | 05-07 | P12 | PASS | r30 audit + N1c fix → R21 0.613→**0.444**, HAWE 0.607→**0.439**, no_ctrl 0.110→**0.104**; rank order 不变 | (论文 L3 锁定) | `r30_ranker_audit_verdict.md`, `2026-05-07_handoff_v14.md` §1, `evaluation/paper_grade_axes.py` |

---

## §4 6 关键拐点详述 (论文 §3.3 / §3.5 / §4.5 直接素材)

### §4.1 拐点 1: R06 axes.py Bug-A (`0513b23`, 2026-05-06, P3)

**Trigger**: R05 verdict — 8 hyperparam 全 6-axis = 0.037 attractor, audit-first pivot.

**4 sub-exp parallel** (10min 主上下文 + 3 agent fork × 3min):
- exp0 [DIAG] attractor 性质 → **(c) action 累积 range starvation**, 不是真 attractor 也不是 agent 不动
- exp1 [DIAG] eval 公式 audit → **Bug-A**: `evaluation/paper_grade_axes.py` range axis 公式语义反, 把 paper Eq.12 action box bound (`-100→+300`, 即 400) **当 trajectory span 期望值**, 反向惩罚 agent ΔH span 不够大. 但 paper §8.4 + Eq.17 (`r^h = -(ΔH_avg)^2`) 主张 ΔH_avg ≈ 0
- exp2 [DIAG] action 语义 audit → 推翻 P 注入嫌疑, 量级 gap 是 **20×** 不是 **100-1000×**
- exp3 [DIAG] disturbance audit → paper LS1 = **-2.48 sys_pu** @ Bus14, LS2 = **+1.88 sys_pu** @ Bus15 (修正旧 memo 1.53/0.90)

**因果**: bug 在代码 ranker, 症状在训练 8 dim 全卡. **代码-训练耦合典型例**: 修代码后训练数字立刻跳, 没动训练任何参数.

**论文用处**:
- §3.5 Sub-System Testing (rubric +++) — 经典 audit-driven bug-finding 例
- §3.3 Diagnostic Findings — Bug-A 公式语义反
- §4.5.5 Engineering Philosophy Lesson 1 (probe before commit, < 1:40 cost ratio)
- §3.9 F-tree M1 (cum_rf 单维 cherry-pick → 6-axis 几何均值)

### §4.2 拐点 2: R10-R17 ANDES forensic + V4 env (`2d9708e`, 2026-05-07, P6)

**Trigger**: R08 H scan max_df 在 H=300 仍 2× paper, ANDES path closure 决议 (`81dd629`). User "改所有 ANDES 问题" → RE-OPEN.

**4 fundamental bug**:
1. **Governor DAE_INACTIVE**: IEEEG1 加进 `ss` 但完全没在 DAE solver 激活. 原因 `ss.setup()` 后再 `add()` 不被 ANDES 支持, V3 try/except 吞了 fatal. **修法**: V1 加 `_pre_setup_addons` hook + V3 重写 hook-based.
2. **G4 inertia**: V1 默认 `ZERO_G4_INERTIA=True` 模拟风电场, 但 paper Kundur 是 4 SG 全 H. 修后 26% max_df 改善.
3. **DT bug**: `current_t = self.ss.dae.t` 是 numpy 0-d ref 不是 value-copy, ANDES TDS 推 dae.t 后 current_t 也跟着变, sub_target 累计 0.6s/step 不是 paper-faithful 0.2s/step. **修法**: `current_t = float(self.ss.dae.t)`. **R10-R17 全部 trace 数字在 3× 错时间尺度上测**.
4. **V4 baseline**: V2 `VSG_M0=30` (H₀=15) 太小, paper Eq.12 box [10, 300] 中段未给值. **修法**: V4 `VSG_M0=200` (H₀=100), DM/DD 范围 paper Sec.IV-B.

**因果**: 4 bug 全 cross-cutting (代码 + env + 训练). 修后必须 V4 multi-seed retrain 才知有效. **耦合不可分**.

**论文用处**:
- §2.3 Asset 3 (TDD probe layer) — `probes/andes_common/` 760 LOC reusable, "10 min/probe vs 90 min pre-extraction"
- §3.5 Sub-System Testing — governor wiring + DT bug 是 unit-test catchable 类
- §4.5.5 Engineering Philosophy Lesson 4 (solve real, not real-looking) — DT bug 看起来 trace 正常实际错时尺
- §3.3 Diagnostic Findings 主战场

### §4.3 拐点 3: R21 V4_h50_s49 0.613 lucky single (`2d9708e`, 2026-05-07, P9)

**Trigger**: R10-R20 forensic + V4 paper-faithful baseline + 7-9 seed × 75ep.

**Headline (pre-ranker-fix)**:
- ddic_v4_h50_s49 LS1 0.80 / LS2 0.43 / Mean **0.613** (H₀=50, M0=100)
- LS1 final_df 0.078 vs paper 0.080 = **97% match**
- LS1 max_df 0.185 vs paper 0.13 = 1.42× cross-platform residual (R19/R20 排除 G4/governor params/Bus 8 后归因 ANDES vs Simulink solver 差异 + PQ vs ZIP load 模型)
- 历史 V2 attractor 0.036 的 17×

**Post-ranker-fix (拐点 6 之后)**:
- LS1 0.46 / LS2 0.43 / Mean **0.444** (4.04× no_ctrl 0.104)

**因果**: ANDES path closure RE-OPENED → COMPLETED. 但 single seed, 复现待验.

**论文用处**:
- §3.4 头条数字 (post-fix 0.444)
- §3.4 outlier 标注 + R24 multi-seed 推翻 + R30 HAWE 99.3% recovery 三件套
- §3.5 ANDES vs Simulink solver 差异 (cross-platform residual 学术诚实)

### §4.4 拐点 4: R24 R21 outlier 推翻 (`2d9708e`, 2026-05-07, P11)

**Trigger**: 用户战略转向 "ANDES 成功为核心, 效果至上, 想超过 V1", R23 v3 + 另一 session multi-seed 综合.

**核心数据 (H₀=50 multi-seed)**:

| H₀ | seed 42 | seed 44 | seed 49 | 备注 |
|---|---|---|---|---|
| 40 | — | — | 0.136 | R23/v4_3 |
| **50** | **0.137** | **0.136 / 0.137 / 0.219** | **0.613** ⭐ + 0.137 final | R21 + multi-seed |
| 60 | — | — | 0.136 / 0.135 | R23/v4_3 |
| 70 | — | — | 0.134 | R23 v3 |
| 100 | 0.151-0.21 | 0.241 | — | V4 default |
| 200 | — | — | 0.325 | 1 seed |
| 300 | — | — | 0.137 (s48) | 1 seed |

**Finding**:
- s49 = 6× outlier vs same H₀ same seed family
- 22 ckpt 全 ≤ 0.22, 真实 attractor ≈ 0.137 (V1 0.037 的 3.7×, 远低 paper-grade 0.6)
- 0.613 不可作 paper main result (reviewer 一问 multi-seed 验证答不出)

**因果**: 强制把 paper headline 从 "0.613 我们达 paper-grade" 改写为 "0.444 / HAWE 99.3% recovery" 故事. 触发 R28-R34 sprint.

**论文用处**:
- §3.4 头条数字 framing 决策点
- §4.5 Reflection on Management — multi-seed 验证作为防 cherry-pick 的方法论
- §3.9 F-tree M1 (cherry-pick 反模式)

### §4.5 拐点 5: R30 HAWE 突破 (`2d9708e`, 2026-05-07, P12)

**Trigger**: R28 warmstart 0.41-0.42 ceiling + R29 hparam sweep 失败.

**Method**: $a_i = \sum_k w_k \pi_k(o_i)$ at inference, no retrain.

**Result (pre-ranker-fix)**:
- w8515 (R21 + ws8 weighted 85/15) = **0.554** (rank 2, 5.04× no_ctrl)
- w9802 (sweet spot) = **0.607** (rank 1 reproducible, 99.0% R21 lucky 0.613)
- 单 actor: R21 = 0.613, ws8 = 0.419

**Result (post-ranker-fix)**:
- w9802 = **0.439** (99.3% R21 0.444, 4.21× no_ctrl 0.104)

**Insight (R32 反实证)**:
- ensemble win 来自**结构性 actor diversity** (不同 seed/init 训出独立 basin)
- **不是** action variance averaging (R32 stoch5 rank 95 worst)
- **不是** single-axis reward tuning (R29/R31/R33 全失败)

**因果**: 解决 "R21 0.613 不可复现" 问题; HAWE 升 5 bespoke asset 之一 (Asset 5).

**论文用处**:
- §2.3 Asset 5 (HAWE) — 主战场
- §3.4 headline 数字
- §3.6 Architectural Ablation (R28 warmstart vs R30 HAWE vs R29-R33 negative)
- §4.5.5 Engineering Philosophy Lesson 1 (cheap inference exploration vs expensive retrain) — 12 weight 配置 sweep < 10 min vs single-seed train 6-8 hr = **600× ROI**

### §4.6 拐点 6: r30 ranker audit + N1c fix (`2d9708e`, 2026-05-07, P12)

**Trigger**: R28' 找 ranker 6s truncate bug → 系统 audit `evaluation/paper_grade_axes.py`.

**3 类 finding**:
- **C1 真不一致**: line 220 axes-overall 用 geo-mean, line 290 scenarios-overall 用 arith-mean. docstring 写 "any one 0 → overall 0 enforce holistic pass" 仅 geo-mean 满足
- **C2.1 缺 NaN guard**
- **C2.2 缺 tds_failed check**
- **C3 design choice flag**: action-range axis 对 V4 结构性 = 1.0 (DA-CRIT-3); `max(s, 0.01)` floor lifts 0-axis; non-DDIC controllers 仅 3 axes vs DDIC 7 axes

**Fix**: 一行改 arith-mean → geo-mean + NaN/tds_failed guard.

**Re-rank 121 ckpt**:
- R21 0.613 → **0.444**
- HAWE 98/2 0.607 → **0.439**
- SWA w98 0.610 → **0.442**
- no_control 0.110 → **0.104**
- **rank order 不变** (top-3 unchanged)

**因果**: 推翻所有 pre-fix 数字, 论文 L3 锁定 headline = 0.444. HAWE 99.3% recovery 仍成立 (R34 fresh-seed 反 lineage 循环).

**论文用处**:
- §3.5 Sub-System Testing — 经典 ranker audit + bug fix 例 (rubric +++)
- §3.4 数字校正声明 (学术诚实)
- §3.8 Spec Validation rigour (SPEC-9 evaluator-parity test catches bug)
- §4.5.5 Engineering Philosophy Lesson 1 (probe before commit) + Lesson 4 (real not real-looking)

---

## §5 Type-View Filters (按论文章节查 trail)

写不同章节时按 type 筛选 §3 trail 表.

### §5.1 写 §3.3 Diagnostic Findings → 主筛 `[DIAG]` + 副筛 `[BUILD]` (修 fix 即)

R06 (Bug-A) / R10 (governor DAE_INACTIVE) / DT bug fix / R19 (WF2 not cause) / R20 (reward paradox) / R27 (modal analysis 反相关) / R28' (ranker 6s truncate) / R30' (ranker C1/C2/C3) / r25 (AGC/ZIP probe).

### §5.2 写 §3.5 Sub-System Testing (rubric +++) → 主筛 `[BUILD]` + `[DIAG]` (audit-driven fix)

R06→R07 (axes.py Bug-A find + 25 LOC fix) / R10-R17 (governor + DT + V4 env) / R30 (HAWE inference algo) / r30+N1c (ranker audit + 1 行 fix + re-rank 121 ckpt).

每个都是 "找 bug → 修 → 验证" 闭环, 写论文经典 audit-driven 故事.

### §5.3 写 §3.6 Architectural Ablation → 主筛 `[TRAIN]` + `[INFER]`

P11 attempt: R23 H₀ sweep / R23-27 22 ckpt / R26 SWA / R27 modal.
P12 sprint: R28 warmstart (PASS) / R29 hparam sweep (FAIL) / R30 HAWE (PASS) / R31 reward shaping max_df (FAIL) / R32 stoch averaging (FAIL) / R33 reward shaping settling (FAIL) / R34 fresh-seed HAWE (PASS) / R35 per-axis (analysis).

R28-R34 final verdict 提供完整 ablation table.

### §5.4 写 §3.7 Hparam Sensitivity → 主筛 `[TRAIN]`

R01 LAMBDA / R02 lam=0.01 / R04 PHI_D=1.0 / R05 8-arm bandit / R22 PHI_ABS×PHI_D / R29 PHI_ABS/PHI_H/PHI_F.

警告: 全失败案例多, 写时聚焦 "为啥 single-axis hparam 不能突破 attractor".

### §5.5 写 §3.4 Headline 数字 → 主筛 `[EVAL]` + `[VALID]` + `[INFER]` (HAWE)

R21 (0.613 lucky), R24 (multi-seed 推翻), R30 HAWE (0.554/0.607 pre-fix), R34 fresh-seed HAWE (99.3% recovery), ranker fix (0.613→0.444 post-fix), L3 锁定 (`2026-05-08_thesis_rewrite_andes_centric_plan.md`).

### §5.6 写 §3.9 Failure & Discussion → 全 trail + F1-F6 + M1-M3 (`andes_6axis_failure_analysis.md`)

cross-cutting, 不筛 type. 重点 6 拐点 + 4 path-blocker (R29/R31/R32/R33).

### §5.7 写 §4.5 Reflection on Management (rubric 10%) → 全 chain + 6 拐点 + commit

最重视, 因果链完整不可拆. 引 §1 TL;DR + §2 ASCII tree + §4 6 拐点详述.

特别强调 4 个反思点:
1. P5 ANDES path closure → R10 RE-OPEN: "停止 ≠ 失败, 是 forensic 不够深"
2. R21 0.613 → R24 outlier 推翻: "single-seed lucky 不是结果"
3. R29-R33 4 path-blocker: "single-actor reward shaping 全失败 → ensemble 是唯一通路"
4. ranker fix: "headline 数字推翻 ≠ 工作白做, 是 scientific honesty"

---

## §5.8 段落级材料清单 (写 main.tex 三主战场段落直接抓)

⚠ **AI-consumer**: 每段落给"主源 + 副源"两层, 写时直接打开主源 paste-ready 句子, 副源 cross-verify.

### §5.8.1 §3.4 Stage 2 Quantitative Comparison (post-fix headline 主战场)

| 段落 | 主源 (paste-ready 句子) | 副源 (cross-check 数字) | TYPE |
|---|---|---|---|
| 第 1 段 — Headline 数字 (R21 = 0.444 / 4.04× no_ctrl, HAWE 0.439 = 99.3% R21) | `EP-A2.md` [C-A2.1] [C-A2.3] | `handoff_v14.md` §1, `EP-C5.md` [C-C5.2], `RESEARCH_TRAIL.md` §4.3 拐点 3 | EVAL |
| 第 2 段 — R21 lucky single + R24 multi-seed 推翻 (22 ckpt 全 ≤0.22, attractor 0.137) | `EP-A2.md` [C-A2.2] | `round_24_verdict.md` §H₀×seed 矩阵, `RESEARCH_TRAIL.md` §4.4 拐点 4 | VALID |
| 第 3 段 — HAWE 99.3% recovery + R34 fresh-seed 反 lineage 循环 | `EP-A2.md` [C-A2.3], `EP-C5.md` [C-C5.3] | `r34_n2_fresh_seed_hawe_verdict.md` §3.4 表, `RESEARCH_TRAIL.md` §4.5 拐点 5 | INFER+VALID |
| 第 4 段 — Cross-platform residual (LS1 max_df 1.42×, R19/R20 排除 4 候选) | `EP-A2.md` [C-A2.4] [C-A2.8] | `round_10_to_17_unified_verdict.md` 末尾 + `appendix_B_cross_platform_draft.md::B.5` | DIAG |
| 第 5 段 — Ranker fix 学术诚实 disclose | `EP-A2.md` [C-A2.5] | `r30_ranker_audit_verdict.md` §C1, `RESEARCH_TRAIL.md` §4.6 拐点 6 | DIAG+BUILD |

### §5.8.2 §3.5 Six-Axis Evaluation Result (与 EP-D1 / EP-C4 共用)

| 段落 | 主源 | 副源 | TYPE |
|---|---|---|---|
| 第 1 段 — 6-axis framework 介绍 (geometric mean holistic gate, R06→R07 audit-driven) | `EP-C4.md` [C-C4.1] [C-C4.2] | `paper_grade_axes.py` 288 lines, `RESEARCH_TRAIL.md` §4.1 拐点 1 (Bug-A) | BUILD+DIAG |
| 第 2 段 — F1-F6 失败族谱 + M1-M3 (现 ME1-ME3 集成时改名) | `EP-D1.md` [F1-F6 + M1-M3] | `andes_6axis_failure_analysis.md`, `RESEARCH_TRAIL.md` §6 (F1-F6) | DIAG |
| 第 3 段 — 21 ckpt baseline 0.033-0.036 / DDIC vs no-control mechanism-level fidelity | `EP-C4.md` [C-C4.6], `EP-D1.md` §1 | `D1 baseline`, post-fix re-rank 121 ckpt | EVAL |
| 第 4 段 — R21 LS1/LS2 axes 详 (post-fix), final_df 97% match LS1, max_df 1.42× residual | `EP-A2.md` §3.2, [C-A2.4] | `round_21_v4_breakthrough.md` §LS1 axes | EVAL |
| 第 5 段 — R28' settling 修正 (LS2 R21 = 6.8s 不是 ∞) | `EP-A2.md` [C-A2.7] | `r28_r21_settling_verdict.md`, `RESEARCH_TRAIL.md` §3 R28' | DIAG |

### §5.8.3 §3.6 Architectural Ablation (与 EP-B3 / EP-C5 共用)

| 段落 | 主源 | 副源 | TYPE |
|---|---|---|---|
| 第 1 段 — Phase 7/9/10 (per-agent shaping rejected / shared-SAC tied / warmstart rejected) | `EP-B3.md` | (B3 内部) | TRAIN |
| 第 2 段 — Phase 12 R28-R34 sprint 6 family (warmstart PASS / hparam FAIL / HAWE PASS / 3 reward shaping FAIL / stoch FAIL) | `EP-C5.md` [C-C5.5], `EP-A2.md` [C-A2.6] | `round_28_to_34_final_verdict.md` 全文, `RESEARCH_TRAIL.md` §3 R28-R34 表 | TRAIN+INFER |
| 第 3 段 — HAWE 唯一突破 + structural diversity insight (R32 反实证) | `EP-C5.md` [C-C5.4] [C-C5.5] | `RESEARCH_TRAIL.md` §4.5 拐点 5 §Insight | INFER |
| 第 4 段 — HAWE 600× ROI (12 weight sweep < 10 min vs 6-8 hr/seed retrain) | `EP-C5.md` [C-C5.6] | `RESEARCH_TRAIL.md` §4.5 ROI 段 | (philosophy) |

### §5.8.4 论文章节 → EP / verdict 反向 cheatsheet

| main.tex 节 | 主 EP | 副 EP / verdict |
|---|---|---|
| §1 Intro | — | `CONTEXT.md` §1 + ANDES CONTEXT §1 |
| §2.1 Modelling | EP-A1 / EP-A2 §3 | `paper_grade_axes.py`, `andes_vsg_env_v4.py` |
| §2.2 Disturbance Calibration | EP-A2 §3.4 | `r25_agc_zip_probe_verdict.md` (failed) + R06 exp3 disturbance audit |
| §2.3 Asset 1-5 | EP-C1 / C2 / C3 / C4 / **C5** ⭐ | `RESEARCH_TRAIL.md` §4.5 (HAWE) |
| §2.4 Stage 1 (compressed) | EP-A1 §8 (8-iter 速查) | — |
| §2.5 Sub-System Testing | EP-C4 (R06→R07) + EP-C3 (probe layer) + EP-C1 / C2 (toolkit / bridge) | `RESEARCH_TRAIL.md` §5.2 (BUILD+DIAG view) |
| §3.1 Stage 1 Results | EP-A1 §3.2 表 + Fig-A1.1/A1.2 | — |
| §3.2 Stage 2 Method | EP-A2 §1 + EP-C5 §3.1 (HAWE algo) | — |
| §3.3 Diagnostic Findings | EP-D1 (F1-F6) + `RESEARCH_TRAIL.md` §5.1 (DIAG view) | EP-A2 [C-A2.5] (ranker fix) |
| §3.4 Headline ⭐ | **EP-A2 §3 (主战场)** + EP-C5 §3.4 (HAWE) | §5.8.1 段落级清单 |
| §3.5 Six-Axis Result | EP-C4 §3.6 + EP-D1 §F1-F6 + EP-A2 §3.2 | §5.8.2 段落级清单 |
| §3.6 Ablation | EP-B3 + EP-C5 §3.5 | §5.8.3 段落级清单 |
| §3.7 Hparam Sensitivity | EP-B4 | `RESEARCH_TRAIL.md` §5.4 (TRAIN view) |
| §3.8 Spec Validation Table | `CONTEXT.md` §4 + EP-A2 [C-A2.5] | — |
| §3.9 Failure Discussion | EP-D1 (F1-F6) + EP-D2 (LoadStep) + EP-D3 (PTDF) + EP-D4 (consolidated) | `RESEARCH_TRAIL.md` §6 + §3 (4 path-blocker) |
| §4.1 Summary | — | `CONTEXT.md` §1 |
| §4.2 Wider Context | — | `WRITING_STANDARD.md` §2 (rubric guidance) |
| §4.3 Limitations | EP-A2 §5.1 + EP-C5 §5.1 | — |
| §4.4 Future Work | EP-D4 + ANDES recovery plan §7.3 | — |
| §4.5 Reflection ⭐ | **`RESEARCH_TRAIL.md` 全文 + 6 拐点 + 4 反思点** + EP-E1 + EP-E2 | §5.7 above |
| Appendix A | EP-A1 §6 (reproduction commands) | — |
| Appendix B Cross-Platform | EP-A2 §3.4 + `appendix_B_cross_platform_draft.md::B.5/B.6` | — |
| Appendix E Bespoke | EP-C1-C5 §6 (Pack §6 章节×claim 表) | — |

---

## §6 Commit ↔ Round 映射

⚠ **commit-grain ≠ round-grain**. 大量 round 合 1 commit (尤其 R10-R36 全在 `2d9708e`). 这是 ANDES 主线开发的事实, 不是 bug.

### §6.1 主 commit 时间线

| commit | date | branch | 包含 round / 主题 |
|---|---|---|---|
| `49e9b89` | 04-25 | main | 6-axis evaluation framework + recovery plan + nav layer (Phase 0 基础) |
| `b195250` | 05-04 | main | ANDES DDIC reproduction n=5 + Phase 9/10 + eval bug fixes |
| `bfa4116` | 05-04 | main | IEEE-format LaTeX manuscript for ANDES DDIC reproduction |
| `e40ff06` | 05-06 | main | refactor ANDES eval to single-source [L4 + 轻量 L3] |
| `8e46248` | 05-06 | main | **R01-R04** + V3 env + figure cleanup |
| `8709884` | 05-06 | main | **R04/R05/R06** audit pivot + Explore→Exploit methodology |
| `cd455ed` | 05-06 | main | **R06 plan v2** — exp0 attractor 性质 + exp4 background |
| `0513b23` | 05-06 | main | **R06 verdict** — exp1 axes.py Bug-A + 推翻 P 注入嫌疑 |
| `9bc7a08` | 05-06 | main | **R07** — axes.py 25 LOC fix |
| `7af7c19` | 05-06 | main | **R08** H scan + V3 governor 失效发现 |
| `81dd629` | 05-06 | main | (R09) ANDES path closure (后被 R10 推翻) |
| `21ded9f` | 05-06 | main | research summary for literature search |
| `c468127` | 05-07 | feature/pm-pe-equiv-ptdf | PTDF R4 lock (D 方案另开, 主线不变) |
| `5e11244` | 05-07 | main | PTDF post-mortem (R0→R4 forensic) |
| **`2d9708e`** | 05-07 | main | **R25-R36 + R10-R24 unified verdict + Path B forensic + ranker fix + DA-CRIT-1 refutation** (HEAD) |

### §6.2 反查表 (Round → commit)

| Round | commit | 备注 |
|---|---|---|
| R01-R03 | `8e46248` | 跟 V3 env + figure 一起 |
| R04-R06 (plan + audit pivot) | `8709884` | 三 round 合一 commit |
| R06 plan v2 | `cd455ed` | exp4 background daemon |
| R06 verdict | `0513b23` | 单独 commit |
| R07 | `9bc7a08` | axes.py fix |
| R08 | `7af7c19` | H scan + V3 governor |
| R09 path closure | `81dd629` | (后 R10 RE-OPEN) |
| R10-R36 | `2d9708e` | **所有 R10+ 工作合 1 commit (HEAD)** |
| ranker fix | `2d9708e` | inside R30' |

### §6.3 跨仓库参照 (`毕业论文/plan/`)

⚠ 这批是 **ANDES 工程汇报错放论文仓库**. 物理路径在 dissertation, 性质属 ANDES 工程. 详见 `Multi-Agent VSGs/CONTEXT.md` §10.

按 trail 时点对应:
- R21 突破 → `毕业论文/plan/2026-05-07_andes_breakthrough_update.md`
- R30 HAWE 0.554 → 同上 (early R30)
- R36 sweep w9802 0.607 → `毕业论文/plan/2026-05-07_andes_breakthrough_FINAL.md` (pre-ranker-fix)
- ranker fix 0.444 → `毕业论文/plan/2026-05-07_handoff_v14.md` §1
- L3 锁定 → `毕业论文/plan/2026-05-08_thesis_rewrite_andes_centric_plan.md`
- 16 evidence pack → `毕业论文/plan/evidence/EP-{A1-E2}.md`
- 5-reviewer (DA-CRIT-1/2 提出) → `毕业论文/plan/2026-05-07_5reviewer/{01-06}_*.md`

---

## §7 与三份 hub doc 关系

| Doc | 视角 | 主轴 | 受众 |
|---|---|---|---|
| `毕业论文/CONTEXT.md` | 事实是什么 | 论文 SPEC + 错误防护 | 写论文者 (人) |
| `Multi-Agent VSGs/CONTEXT.md` | ANDES 工程怎么走的 | round / branch / env / failure family | 改代码者 + 答辩者 |
| **`Multi-Agent VSGs/RESEARCH_TRAIL.md`** (本文档) | **"我怎么解决问题的" 因果链** | 时间序 + type + commit | **AI** (写 §4.5 Reflection + §3.3 Findings) |

不重复. 三视角.

**入口顺序** (写 §4.5 Reflection 时):
1. 本文档 §1 TL;DR (60s)
2. §2 ASCII tree (3 min)
3. §4 6 拐点详述 (15 min)
4. §3 trail 表 + §5 type filter (按需深入)
5. ANDES CONTEXT §3/§5/§6 (verify fact)
6. 论文 CONTEXT §2/§3.2/§3.5 (写论文格式)

---

## §8 维护规则

- **ANDES 主线即将冻结** (2026-05-08 用户决议). 此文档为收尾 snapshot
- 新 round 出现 (R37+) → 加 §3 trail + §6.2 commit map; 如开 P13 → 更 §2 ASCII tree
- 新 ranker fix / 数字校正 → 加 §3 + §4 拐点 + 论文 CONTEXT §11 数字版本
- type 6 类不 expand (保 grep 一致性)
- caveman 中文 + AI-consumer 高密度

每次更新写日期戳:
```
[2026-XX-XX] <one line change>
```

[2026-05-08] v1 initial: ANDES 因果链导航建成. 37 round / 12 phase / 6 拐点 / commit map 含 grain mismatch 注 / 7 type-view filter / 3 hub doc 关系

---

*EOF — v1 / 37 round / 12 phase / 6 拐点 / 6 type / commit-grain mismatch documented / AI-consumer / caveman*
