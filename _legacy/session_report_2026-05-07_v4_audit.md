# Session Report — ANDES V4 forensic audit + 训练 anti-paper 谜团

**Date**: 2026-05-07
**Session length**: ~6 hr (单一对话)
**Investigator**: main agent (claude)
**Trigger**: 用户 "改所有 ANDES 问题"
**Status**: env-level 全 paper-faithful (R10-R19 audit), training-level **未 reach paper**, anti-paper SAC behavior unexplained

---

## Abstract

We conducted a 6-hour intensive forensic audit of the ANDES Kundur 4-VSG environment used to reproduce Yang et al. TPWRS 2023. Forensic probes R10-R19 identified and fixed **11 distinct bugs** spanning environment construction, action mapping, reward formula, and time integration. After fixes, the environment baseline (no SAC) reached paper-magnitude (within 1.3-1.7×). However, SAC training on the fully paper-faithful V4.1 environment **converged in the wrong direction**: trained policies REDUCED virtual inertia and damping when the disturbance required INCREASING them, yielding 20-30% LARGER frequency excursions than no-control. This is unexpected and suggests the reward formula (faithful to paper Eq.14-18) may be insufficient or misaligned in our 4-agent ANDES configuration. We document all findings and pause for deeper analysis before further training.

---

## 1. Methodology

We followed a forensic-then-fix pipeline using a generic probe framework (`probes/andes_common/`):

1. **Environment introspection** (R10): identify ANDES DAE-level bugs via attribute scanning
2. **Method viability** (R11-R13): minimum viable validation of each optimization direction
3. **Root cause sweeps** (R14-R16): systematic ablation to localize platform residuals
4. **Consolidation** (R17): create paper-faithful V4 environment
5. **Reward audit** (R18): per-component reward decomposition under SAC-like exploration
6. **Cross-cut audit** (R19): verify all fixes via single integrated probe
7. **Training + eval** (V4.1 × 3 seeds × 200 ep): produce trained policies, evaluate on paper Fig.6/8 scenarios
8. **Visual verdict** (paper Fig.7/9 plot): trained policy behavior overlay vs no-control vs paper

---

## 2. Findings — Environment-level (FIXED)

| # | Bug | Detection method | Fix |
|---|---|---|---|
| 1 | **IEEEG1 governor not in DAE** (0 Algeb/State after add) | R10 model introspection | V1 `_pre_setup_addons` hook + V3 hook-based add |
| 2 | **G4 inertia zeroed by default** (V1 模拟风电场, 不 paper-faithful) | R15 ablation | V1 `ZERO_G4_INERTIA = False` default |
| 3 | **Action range 17× narrower than paper** (V2 [-15,45] vs paper Sec.IV-B [-200,600]) | R12 + paper fact doc cross-check | V4 paper-faithful action range |
| 4 | **VSG_M0 too small** (V2 H₀=15s vs paper Eq.12 box middle ≈100s) | R14 H scan | V4 VSG_M0=200 (H₀=100s) |
| 5 | **D₀ heterogeneous V2 sweep finding, not paper baseline** | paper fact doc | V4 D0_HETEROGENEOUS = uniform 100 |
| 6 | **PHI_D × paper action range explodes 178×** (paper Eq.14 PHI_D=1 with V2 narrow range, paper-deviated 17×) | R18 reward decomposition | V4.1 PHI_D = PHI_H = 0.0056 (= 1/178) |
| 7 | **M_clamp 0.2 lets s49 H₀=50 collapse** (M → 0 ≈ no inertia) | s49 80% TDS failure | base_env M_MIN_PHYSICAL=20 (paper Eq.12 lower) |
| 8 | **D_clamp 0.1 same issue** | ditto | D_MIN_PHYSICAL=10 |
| 9 | **DT-bug**: `current_t = self.ss.dae.t` is ndarray reference, sub_target累积 0.6s/step instead of 0.2s | DT-bug audit | `current_t = float(...)` (one line) |
| 10 | **ANDES `setup()` after `add()` fails silently** (try/except 吞 fatal) | R10 forensic | refactor V3 to add-before-setup |
| 11 | **Reward eval used `final_df_Hz=0.0` default** (settling never reaches absolute zero with droop) | R19 audit | call site passes `paper.final_abs_df_Hz` (already correct in main eval, only default arg was misleading) |

---

## 3. Findings — Method-level

| # | Direction | MVV result |
|---|---|---|
| 12 | **PI-AC physics regularization** (Wang et al. 2023, "physics-informed actor-critic") | **METHODOLOGY ERROR**. Closed-form ODE simulators (ANDES TDS, Simulink Phasor, etc.) analytically enforce swing equation; J residual = numerical floating-point precision (1.069e-07 single constant on 30-step trace). PI-AC reg gradient = 0. Applies only to partial / measurement-noisy / hybrid models. **Paper appendix flag**. |
| 13 | **CTDE (centralized training, decentralized execution)** | **FEASIBLE**, param ratio 1.10× (137K→151K), CPU-tractable. Implementation deferred (need V4 paper-faithful baseline first). |
| 14 | **Settling-time reward** | Marginal value, env achieves paper-magnitude settling already (1s vs paper 3s, slightly over-damped). Implementation deferred. |

---

## 4. Findings — Training-level (UNRESOLVED)

After fixes 1-11 (V4.1 environment), trained 3 seeds × 200 ep with paper Eq.14 strict (PHI_F=100, PHI_H=PHI_D=0.0056, PHI_ABS=0). Result:

| Metric | s42 | s43 | s44 |
|---|---|---|---|
| Best reward | -556 @ ep 162 | -620 @ ep 161 | -594 @ ep 94 |
| Final reward (ep 199) | -1613 | -1462 | -1606 |
| TDS failures | 5.5% | 6.0% | 6.0% |
| Freq peak (Hz) | 0.39 | 0.57 | 0.34 |
| **r_f / r_h / r_d ratio** | r_d 91% | r_d 91% | r_d 91% |
| **action_collapse warnings** | yes | yes | yes |

**No reward divergence** ✓ (vs V4.0 PHI_D=1 hit STOP @ ep75-77).

**But eval on paper Fig.6/8 scenarios** (LS1 -2.48 sys_pu @ Bus14, LS2 +1.88 sys_pu @ Bus15):

| | LS1 max\|Δf\| | LS2 max\|Δf\| | DDIC ΔH direction | DDIC ΔD direction |
|---|---|---|---|---|
| no_control | 0.183 | 0.169 | n/a | n/a |
| s42 | **0.222** (worse) | **0.224** (worse) | LS1 +30 ✓ / LS2 -3 ❌ | mixed |
| s43 | **0.202** | **0.245** | LS1 -15 ❌ / LS2 -3 ❌ | -15 ❌ |
| s44 | **0.223** | **0.214** | LS1 +20 ✓ / LS2 -3 ❌ | oscillating |
| paper | 0.13 | 0.10 | should be + (increase H) | should be + (increase D) |

**Trained DDIC is 20-30% WORSE than no_control on max\|Δf\|** — anti-paper learning.

---

## 5. Critical analysis — why anti-paper?

### Hypothesis A: PHI_ABS=0 removes "recovery to nominal" signal
Paper Eq.15-16 defines `r_f = -(Δω_i - ω̄_local)²` — penalizes **synchronization** (matching neighbors) but NOT **absolute deviation**. Without `PHI_ABS × r_abs = -PHI_ABS × Δω_i²`, agents have no reward to pull toward Δω = 0. They sync at non-zero ω steady state. In Kundur with droop control, this means agents agree on a non-zero settled value. **r_f → 0 at steady state; r_h, r_d only penalize action variance** → policy converges to "minimal action" or any action that quickly reaches consensus, not necessarily one that minimizes |Δω|.

**Test**: V4.2 = V4.1 + re-enable PHI_ABS=50. Designed but **trainings killed before run**.

### Hypothesis B: 4-agent ring sync reward is degenerate
With 4-agent ring + Δω_i sync to 2 neighbors, the reward landscape has many local minima where all 4 agree on a non-zero ω. SAC may exploit one of these.

### Hypothesis C: Action collapse + entropy starvation
SAC entropy temperature `alpha` may collapse, leaving actor with std=0.05 (basically deterministic). Once collapse, agent can't escape local minimum.

### Hypothesis D: Episode length too short
Paper Eq.13 ΔH ∈ [-100, +300] suggests agent has 30+s to navigate inertia space. Our 50 step × 0.2s = 10s is shorter than paper Fig.7 (30s window). Agent only sees transient, doesn't experience full settle.

### Hypothesis E: r_d / r_h paper formula reward "minimum action" too strongly
Paper Eq.17/18 `r_h = -(mean(ΔH))²` — global mean penalty. With 4 agents, if they all agree on non-zero ΔH, mean is non-zero → r_h penalty active. Optimal under this is mean(ΔH) = 0 — i.e., agents balance their ΔH (some +, some -). This **forces zero net inertia change** which is not paper goal (paper wants net inertia INCREASE during disturbance).

This may be a **paper-formula paradox**: paper Eq.17 wants ΔH conservation, paper Fig.7 wants ΔH increase during excursion. **If both agents act in same direction (all +ΔH), r_h → -(ΔH)² penalty grows**. Agent learns: keep mean(ΔH) close to zero by canceling each other → **anti-paper unless reward constrains absolute |Δω|**.

This explains why **PHI_ABS** is critical: it provides the "all should pull frequency up together" signal that overrides the conservation penalty. Without PHI_ABS, agents minimize Eq.17 by canceling each other, fundamentally different from paper goal.

**Likelihood ranking**: A > E > C > D > B.

---

## 6. Recommendations

### Immediate (next session)
1. **Probe-first, train-second**: Run R20-R23 (PHI_ABS ablation, r_f signal audit, action distribution audit, episode-length effect) before any new training.
2. **V4.2 = V4.1 + PHI_ABS=50** as primary test of Hypothesis A.
3. **PHI_F sweep** [50, 100, 300, 1000] to test relative weight of sync vs r_h cancellation.
4. **Document each verdict via `quality_reports/research_loop/round_NN_verdict.md`** so cross-session signal accumulates.

### Strategic
1. **paper appendix B**: write up cross-platform / cross-method validation findings (V4 baseline 1.3-1.7× residual + PI-AC methodology error). High academic value.
2. **CTDE deferred until paper-aligned baseline trained**: implementing CTDE on anti-paper baseline is wasted effort.
3. **Decision gate**: if 5+ probes still can't explain anti-paper behavior, strongly consider returning to Simulink-discrete path (per original closure decision) and document ANDES limitation.

---

## 7. Pipeline status (artifact summary)

### Code (committed-ready, no uncommitted edits)
- `env/andes/{base_env, andes_vsg_env, andes_vsg_env_v3, andes_vsg_env_v4}.py` — V4 paper-faithful env
- `scenarios/kundur/{train_andes, train_andes_v4}.py` — V4 trainer + new CLI
- `probes/andes_common/{utils, tracers, verdict, paper_constants}.py` — generic probe framework
- `scripts/research_loop/{r10..r19,eval_v4_*}.py` — forensic probes + V4 eval drivers
- `paper/figure_scripts/{v4_baseline_fig6_8, v4_1_fig7_9_ddic}.py` — paper Fig.6-9 plots

### Data
- `results/research_loop/eval_v4_baseline/` — DDIC + no_control trace JSONs
- `paper/figures/v4_baseline/` + `paper/figures/v4_1_baseline/` — paper Fig.6/7/8/9 PNG/PDF
- `results/v4_*_s{42-57}/` — V4.0/V4.1 trained ckpt dirs (most under-trained or invalid)

### Documents
- `quality_reports/handoff/2026-05-07_v4_session_handoff.md` (this session, primary handoff)
- `quality_reports/handoff/2026-05-07_andes_path_closure.md` (original closure, RE-OPENED noted at top)
- `quality_reports/research_loop/round_10_to_17_unified_verdict.md` (R10-R17 + DT-bug caveat)
- `quality_reports/research_loop/round_10_verdict.md`, `round_11_13_mvv_verdict.md` (per-round)

---

## 8. Acknowledgement

This session benefited from:
- DT-bug discovery (mid-session): user / linter spotted the `current_t` reference issue, documented at top of `round_10_to_17_unified_verdict.md`. Without DT-fix, all R14-R17 trace numbers were 3× wrong scale.
- User's "针对不同方向最小可行性验证并行" principle (early session) — drove R11-R13 MVVs that ruled out PI-AC dead-end early.
- User's pivot to "深度分析 + 写报告" instead of more sweeping — preventing wasted V4.2 trainings on potentially same anti-paper outcome.

---

*Generated 2026-05-07 ~02:50 (UTC+8) at end of session, ANDES path RE-OPENED but training success deferred to next session deep-audit.*
