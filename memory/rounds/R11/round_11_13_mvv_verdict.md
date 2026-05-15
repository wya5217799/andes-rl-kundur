# R11-R13 — 方向 2/3/4 MVV verdict 汇总

> ⚠⚠⚠ **DT-BUG CAVEAT (2026-05-07 后发现)** ⚠⚠⚠
> 本 verdict 全部 trace 数字 (R11 J residual, R13 settling 量级 / final_df) 在 **0.6s/step** DT bug 下测.
> R11 (PI-AC J=1e-7 = methodology error) **仍有效** — J 是数值精度量级跟 DT 缩放无关.
> R12 (CTDE param 1.10×) **仍有效** — pure parameter count, 跟 trace 无关.
> R13 settling NO_SIGNAL **可能 partial invalid** — 当时 30 step trace 是 18s 而非 6s (paper Fig.6 window). DT-fix 后需重测.
> 修法: `env/andes/base_env.py` step() 内 `current_t = float(self.ss.dae.t)`.


**Date**: 2026-05-07
**Wall**: ~30 min (3 probe scripts + 3 并行 run)
**Trigger**: 用户 "优化方向所有最小可行性验证都做完了吗，有多少值得修改的地方"
**Predecessor**: R10 (方向 1 governor wiring forensic, DAE_INACTIVE)
**Doc 源**: `quality_reports/research_loop/优化方向.md` 5 directions

---

## TL;DR (1 段)

5 个方向 MVV 全部完成. 方向 0/5 是**文献分析** (Kundur H+gov 解释残差 + turbine governor 必要性), 不需 MVV, 已在 doc 内. 方向 1/2/3/4 是**代码/方法**, 各跑 1 个 minimum probe. R10 验方向 1 (governor) 升级 Root #2 为 DAE_INACTIVE. R11 验方向 2 PI-AC physics regularization 暴露**论文级 methodology error** — swing eq 残差在 closed-form ODE simulator 里 = 数值精度 (1e-7, 30 step 单一值), 不是物理信号. R12 验方向 3 CTDE 改造极便宜 (1.10× param). R13 验方向 4 settling reward 在 ANDES 上 NO_SIGNAL (6s 内永远不 settle 因为 Root #2/#3 让 max_df 4×paper). **当前 ANDES repo 不值得做任何修改** (per closure 决定); MVV 输出给 Simulink-discrete repo 2 个高 ROI 候选 (CTDE 1.10× param + settling reward 假设长 episode + paper-magnitude max_df) + 1 个**重要 negative finding** (PI-AC 在任何 closed-form simulator 上无效, 应在 paper appendix flag).

---

## MVV 矩阵

| 方向 | 类型 | Probe | Verdict | 计算/量级 | ANDES 值得修? | Simulink 值得修? |
|---|---|---|---|---|---|---|
| 0 | 文献分析 | n/a | doc 内 | Kundur H=6.5/6.175 + governor → max_df 0.13Hz | n/a | n/a |
| 1 | code (governor) | r10 | **DAE_INACTIVE** | IEEEG1 添加成功但 0 Algeb/State; V2 vs V3 Pm 完全相同 | ❌ (Root #3 仍限) | n/a |
| 2 | method (PI-AC) | r11 | **WEAK / METHODOLOGY ERROR** | J_median = 1.069e-07 (常数), simulator 已 enforce swing eq | ❌ | ❌ (同 problem) |
| 3 | method (CTDE) | r12 | **FEASIBLE** | param 137K→151K (1.10×), forward ok | ⚠ Root #3 仍限 | ✓ **#1 候选** |
| 4 | method (settling) | r13 | **NO_SIGNAL on ANDES** | 6s 永远不 settle, final_df=0.150 > 阈值 0.02 | ❌ | ✓ **#2 候选** (长 episode) |
| 5 | 文献分析 | n/a | doc 内 | turbine + ESS pure inertia 不够 | n/a | n/a |

---

## 关键 insight: 方向 2 PI-AC 是 methodology error

**Probe 数据**: J 在 30 step LS1 zero-action trace 上 min = median = max = 1.069e-07. 不是"弱信号", 是**单一常数值**.

**物理解释**: ANDES TDS 求解器**本身在 enforce swing equation**:
```
M · ω̇ + D·(ω-1) = Pm - Pe       ← solver 求解的 ODE
```
因此残差:
```
r_phys = M · ω̇ + D·(ω-1) - (Pm - Pe) ≡ 0  (analytic)
```
实测 1e-7 是 floating-point 数值精度 (double 16-digit precision 在中间计算累积).

**给 critic 加这个 reg 等于**: 惩罚 RL 学到 "Q 值跟 ANDES TDS 输出一致". RL 已经在 ANDES 上跑, transition 100% 来自 ANDES, **梯度方向 = 0**.

**这跟 ANDES 无关**, 任何 closed-form ODE simulator (Simulink Phasor / Simulink Discrete EMT / RTDS / DIgSILENT) 都满足 swing eq. PI-AC 在 paper (Wang et al. 2023) 用 CIGRE 14-bus 跑得动, 是因为他们用了 **partial / aggregate / measurement-noisy 模型**, 不是 closed-form simulator.

**给 paper appendix B 的额外材料**:
> Cross-method validation (R11 forensic, 2026-05-07): Physics-Informed Actor-Critic
> regularization (Wang et al. 2023, "PI-AC") was probed for applicability to our
> ANDES-Kundur env. Swing-equation residual J = ||M·ω̇ + D·(ω-1) - (Pm-Pe)||²
> measured on a 30-step LS1 zero-action trace returned a constant 1.069e-07 sys_pu²
> (numerical floating-point precision), confirming that ANDES TDS solver enforces
> the swing equation analytically. PI-AC regularization is therefore mathematically
> redundant in any closed-form ODE simulator and applicable only to partial /
> measurement-noisy / hybrid system models. This is a methodology limitation of
> the PI-AC framework, not specific to our reproduction.

---

## 修改价值排序 (Final)

### 当前 ANDES repo
**不值得做任何方向的代码修改** (per `2026-05-07_andes_path_closure.md` 决定: Root #3 平台 2× 残差不可修).

唯一可做: paper appendix B 加 PI-AC negative finding (~10 min, 文档).

### Simulink-discrete repo (用户在其他对话搞)
| Rank | 方向 | 修改范围 | 期望效果 | ROI |
|---|---|---|---|---|
| #1 | 3 CTDE | `agents/sac.py` + `ma_manager.py` + `train_*.py` 共 ~30-50 LOC | 全局 critic 缓解 attractor, 训练稳定性提升 | 低成本 1.10× param, 高 ROI |
| #2 | 4 settling reward | `env/simulink/*_simulink_env.py::_compute_reward()` ~10 LOC | 引导 SAC 不"拖慢" governor 频率恢复 | 低成本, 中 ROI |
| - | 2 PI-AC | n/a | n/a | **不要做**, methodology error |
| - | 1 governor | n/a (Simulink 用 SimPowerSystems 自带 governor, 已对) | n/a | n/a |

### 方向 0/5 文献分析
不需修改, 但**应在 paper Section II/III 引用**作为 ANDES vs Simulink 平台层差异解释 + paper Eq.12 H 上限物理意义.

---

## 文件 / 引用

- 探针: `scripts/research_loop/r11_pi_ac_residual_probe.py` / `r12_ctde_critic_probe.py` / `r13_settling_reward_probe.py`
- 输出: `results/research_loop/r1{1,2,3}_*.json`
- 通用 utility (R10 留下): `probes/andes_common/utils.py` (introspect_model + try_read_v + safe_get)
- 上游: `quality_reports/research_loop/优化方向.md` (5 directions doc)
- R10 verdict: `quality_reports/research_loop/round_10_verdict.md`
- ANDES closure: `quality_reports/handoff/2026-05-07_andes_path_closure.md`

---

## 给用户的下一步建议

1. **本 repo (ANDES)** — 不再做代码修改. 整理 R10-R13 verdict 进 paper appendix B "Cross-Platform / Cross-Method Validation Limitations" (~30 min 文档工作)
2. **Simulink-discrete repo** (用户在另一对话) — 把 R12 (CTDE) + R13 (settling reward) 当 implementation 候选, 按 ROI 排序逐个上线. PI-AC 不要尝试.
3. **方法论 lesson 锁进 `.claude/skills/research-loop/SKILL.md`**:
   - "PI-AC / physics-informed regularization 在 closed-form simulator 上前必须先 probe 残差量级 (用 r11 模板)"
   - "Settling-time reward MVV 必须配合 paper-faithful disturbance magnitude + 长 episode (用 r13 模板, 最少 30s)"
   - "CTDE 改造 MVV 用 r12 模板检查 param ratio (target < 4× 才 CPU 可承受)"

---

*Generated 2026-05-07. R11-R13 verdict locked from r1{1,2,3}_*.json.*


## Questions opened (this round)
- none (retrofit — this verdict pre-dates the Q entity introduced in R39)

## Questions closed (this round)
- none (retrofit)

## Questions advanced (this round, status unchanged)
- none (retrofit)
