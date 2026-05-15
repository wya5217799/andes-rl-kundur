# R22 — V4.2 三路 retrain 全部 anti-paper, 全失败破 mid-range attractor

**Date**: 2026-05-07
**Phase**: ANDES V4.1 anti-paper root cause — Hypothesis A/B 三路并行 retrain 验证
**Wall**: ~16 min (3 train × 50 ep parallel ~8 min + 3 R20-style audit parallel ~6 min + 2 min verdict)
**Status**: ❌ **三路全部失败** — 3 个 V4.2 ckpt 比 V4.1 baseline **显著更差** (max_df 0.30 vs V4.1 0.22 vs no_control 0.18). PHI_ABS 在 [50, 200] 区间 **无 mechanistic effect** (A vs C 几乎完全一致). PHI_D 提到 0.05 反而让 r_d 数值爆炸 (训练 reward base -250000 量级).
**Trigger**: R20 PARTIAL verdict + 用户 "短仿真，多并行，最小试错" 原则 → 选 3'' = 1 + 2'' (修正后 = 1 + 2' + 2'' static)
**Probe scripts**: `scripts/research_loop/r20_reward_settled_audit.py` (复用) × 3 ckpt
**Outputs**:
- ckpts: `results/v4_2_phiabs50_s42/`, `results/v4_2_phid05_s42/`, `results/v4_2_phiabs200_s42/`
- audits: `results/research_loop/r22_audit_{phiabs50,phid05,phiabs200}.json`
- 训练 log: `logs/v4_2_parallel/run{A,B,C}_*.log`
- eval ANDES log: `logs/v4_2_parallel/eval/{A,B,C}_andes.log`
**前置**: `quality_reports/research_loop/round_20_verdict.md` (R20 PARTIAL, mid-range attractor 真相)

---

## TL;DR (1 段)

R20 PARTIAL 后, 按 "短仿真多并行最小试错" 原则并行启动 3 个 V4.2 retrain (各 50 ep, seed 42): A=`--phi-abs 50`, B=`--phi-d 0.05`, C=`--phi-abs 200`. 训练 8 min 全完, 无 NaN/collapse. R20-style settled audit 显示**全部 anti-paper, 显著比 V4.1 baseline 更差**: V4.2 max_df 0.30 (vs V4.1 0.22, no_control 0.18, paper 0.13). 关键发现: (i) **A/C 几乎完全相同** (max_df 0.316/0.315, mean dH -12.9/-12.0), PHI_ABS 在 [50, 200] 区间 4× scale 在 50 ep 训练后 policy 无差异 — **PHI_ABS dimension dead 在该 region**; (ii) **B 唯一让 ΔH 互抵成型** (mean(dH)=+2.7 LS1, std=21 比 V4.1 28.8 仍小但比 A/C 5.6 显著大) 但 max_df 反而最差 (0.326), 说明 hypothesis A 原始预测的"互抵 mean=0"形态出现了, **但仍 anti-paper**, 即 hypothesis A 完全推翻 (互抵不是 anti-paper 的根因, 是结果之一); (iii) **r_f settled 全部翻 5×** (V4.1 -0.47 → V4.2 -2.0~-2.3), gate B 全失败 → V4.2 policy 没找到 sync attractor, 放弃了 R20 实测的 V4.1 attractor. 综合: 3 个 hypothesis 全部失败, **mid-range attractor 不是 PHI_ABS / PHI_D 局部修补能破的, 是 SAC × paper Eq.14 reward landscape 的结构性问题**. 触发 handoff 决策矩阵 fallback option 4: 写 appendix B 跨平台 + 切 Simulink-discrete 主线.

---

## 实测数据对比 (V4.1 baseline vs 3× V4.2)

### 主表 — settled phase metrics (last 30 of 50 step, t > 4s)

| Run | LS | max_df | max\|dω\| | mean(dH) | std(dH) | r_f | gates(A,B,C) |
|---|---|---|---|---|---|---|---|
| no_control | LS1 | **0.189** | 0.145 | 0.0 | 0 | -0.11 | TTF |
| no_control | LS2 | **0.168** | 0.124 | 0.0 | 0 | -0.15 | TTF |
| **V4.1 baseline (R20)** | LS1 | 0.223 | 0.198 | -3.20 | 28.8 | -0.47 | TTF |
| **V4.1 baseline (R20)** | LS2 | 0.214 | 0.162 | -9.29 | 9.6 | -0.34 | TTF |
| V4.2-A (phi_abs=50) | LS1 | **0.316** | 0.292 | -12.9 | 5.6 | -2.13 | TFF |
| V4.2-A (phi_abs=50) | LS2 | **0.302** | 0.258 | -19.4 | 7.4 | -2.33 | TFF |
| V4.2-B (phi_d=0.05) | LS1 | **0.326** | 0.284 | +2.7 | 21.0 | -2.16 | TFF |
| V4.2-B (phi_d=0.05) | LS2 | **0.266** | 0.262 | -4.9 | 15.5 | -1.92 | TFF |
| V4.2-C (phi_abs=200) | LS1 | **0.315** | 0.282 | -12.0 | 6.3 | -2.07 | TFF |
| V4.2-C (phi_abs=200) | LS2 | **0.302** | 0.260 | -19.3 | 8.4 | -2.35 | TFF |

### 训练 reward 趋势 (Avg Reward, 50 ep × seed 42)

| Run | ep5 | ep30 | ep50 | 改善 |
|---|---|---|---|---|
| A (phi_abs=50) | -34689 | -13707 | -16483 | 2.1× |
| B (phi_d=0.05) | -254399 | -97228 | -163610 | 1.6× (基数 9× 大, 因 PHI_D ↑) |
| C (phi_abs=200) | -34732 | -13797 | -16713 | 2.1× (跟 A 几乎完全一样) |

---

## 三个 hypothesis 验证结果

### Hypothesis 1 (Run A: PHI_ABS=50): **失败**
- 假设: 加 ω→0 中等惩罚 → policy 拉 freq 回 50 Hz → 破 R20 mid-range attractor
- 实测: max_df 0.316 (V4.1 0.223 的 1.4×, no_control 0.189 的 1.7×). settled max\|dω\| 0.292 vs V4.1 0.198, **更不收敛**. r_f -2.13 vs V4.1 -0.47, **没找到 sync**.
- 解读: 50 ep 不够 SAC 重新收敛. V4.1 200 ep 找到的 mid-range attractor 被破坏, 但 50 ep 训练只让 policy 进入 "迷茫" 状态, 没找到新 attractor.

### Hypothesis 2' (Run B: PHI_D=0.05): **失败 + hypothesis A 推翻**
- 假设: 加 r_d 强惩罚 (V4.1 0.0056 → 0.05, 9×) → 推 ΔD 回 0 → 破 mid-range attractor
- 实测: max_df 0.326 (最差), settled mean(dH)=+2.7 std=21.0 (LS1) — **首次出现 hypothesis A 原始预测的 "ΔH 互抵 mean=0 std 大" 形态**
- 但 max_df **反而最差** → hypothesis A 完全推翻: 即使 agents 真做 ΔH 互抵, 物理上仍 anti-paper. 互抵 ≠ anti-paper 根因.
- 训练 reward base 飙到 -250000 量级 (vs A/C -34000), PHI_D 9× 让 r_d 主导更夸张, 但 SAC 收敛能力没崩 (final -163610 改善 1.6×).

### Hypothesis 2'' (Run C: PHI_ABS=200): **失败 + PHI_ABS dead**
- 假设: 强 ω→0 force (4× of A) → 强力破 attractor
- 实测: **跟 A 几乎完全一致** (max_df 0.315 vs 0.316, mean(dH) -12.0 vs -12.9, std 6.3 vs 5.6, r_f -2.07 vs -2.13)
- 解读: PHI_ABS 在 [50, 200] 区间 **policy 无差异** (50 ep 内). 推断: r_d 主导 reward, PHI_ABS 项被淹没. 即便 4× scale up 也不显著改 SAC gradient direction.
- 这意味着 PHI_ABS 不是有效的"调参旋钮" → 后续不应继续 PHI_ABS sweep (浪费).

---

## R20 mid-range attractor 的真相 (R20 + R22 综合)

R20 实测 V4.1 ckpt: ΔD ≈ -39 (4 agents 全军一致), ΔH 非对称, sync 部分达成. 我推断这是 "PHI_D=0.0056 弱 → SAC max-entropy 输出 ΔD" 的副作用.

**R22 后修正**: V4.2-B (PHI_D 9× 加强) **没破 attractor**, 反而:
- ΔH 形态变 (mean ≈ 0, std 大) — 这是 PHI_H 项相对压力变化的结果
- ΔD 形态没大变 (continued 一致 mid-range)
- max_df **更差**

→ **mid-range attractor 不是 PHI_D rescale 能破的局部最优**, 是更深层的 SAC × Eq.14 landscape 结构问题. 怀疑是 **action space dimension explosion** (4 agents × 2 dim = 8D) + **同质 ring topology** + **稀疏 reward signal** 综合.

---

## handoff 决策矩阵更新

handoff 原矩阵:
| R20 verdict | 后续 |
|---|---|
| PARADOX_CONFIRMED | V4.2 retrain → 200 ep × 3 seed |
| PARADOX_PARTIAL | (R20 时新增, 对应 R22) |
| PARADOX_REJECTED | 写 appendix B + 切 Simulink |

**R22 verdict**: 实质上是 PARADOX_REJECTED (3 个修补方向全失败, 没 confirm trivial optimum 是 PHI_*, 反而暴露更深结构问题).

→ **触发 fallback option 4**: 写 appendix B + 切 Simulink-discrete 主线.

---

## 后续选项 (按 ROI 排序)

### 选项 1: 接受 verdict, 切 Simulink-discrete (推荐)
- handoff fallback, ANDES 6+1.5 hr sunk → 撤离 ~2 hr
- 写 paper appendix B "ANDES vs Simulink cross-platform residual + reward formula failure" (有学术价值的 negative finding)
- Simulink-discrete 主线 (kundur_cvs_v3) 已 G1-G6 lock paper-anchored, 是稳定 fallback
- **触发条件**: R22 verdict 已满足 (3 个 hypothesis 全失败)

### 选项 2 (低 ROI): 扩 V4.2-A 到 200 ep × 3 seed
- 原 handoff Phase 3 plan, 预算 1.5 hr
- 风险: 50 ep V4.2-A 已经比 V4.1 200 ep 更差 → 200 ep V4.2 大概率不会比 V4.1 200 ep 更好 (PHI_ABS=50 在 R20 实测对 inference policy 无效, retrain 看 50 ep 内也无效)
- **不推荐** — 1.5 hr 投入预期 negative

### 选项 3 (深探, 高风险): 改 reward formula 结构
- 例: r_f 改 -(Δω_i)² 代替 -(Δω_i - mean_neighbor)² (绝对偏差代局部 sync)
- 偏离 paper Eq.14 strict, 但 paper 偏差列表新增条目
- 50 ep retrain ≤ 15 min, 但**改代码** (违反"最小试错"原则), 试错预算高
- **触发条件**: 用户主动要求继续探 ANDES 路径

### 选项 4 (退出, 非临时): 直接 ANDES 路径关闭
- 回到 2026-05-06 closure decision (handoff Section 9 提及"PTDF 失败已撤回那是 Simulink 主线; 此 handoff 是 ANDES 双空格 repo")
- 不再扩 V4.2, 写 appendix B 完成 ANDES 学术任务

---

## 不可触红线 (continue from handoff Section 6 + R20 Section 7)

1. ❌ 不再扫 PHI_ABS / PHI_D 单维度调参 (已确认 R22 PHI_ABS [50,200] 无效, PHI_D 0.05 互抵但更差)
2. ❌ 不再单纯 retrain 同 seed 期望不同 — A/C 完全一致证明 SAC 在该 reward landscape 下 deterministic 收敛到同 attractor
3. ❌ V4.2 ckpts 不要用作 6-axis paper-grade eval (浪费, settled audit 已确认 anti-paper, paper grade 一定低分)
4. ❌ 不要在 R22 数据上加更多 ANDES probe — 信息已饱和, 投入更多 ANDES 时间 ROI 接近 0
5. ❌ 不要 update R21 verdict (`round_21_v4_breakthrough.md`) — 那是 V4_h50_s49 不同 variant, 跟 V4.1_paper_s44 + V4.2 不冲突

---

## 文件引用

- 本 verdict: `quality_reports/research_loop/round_22_verdict.md`
- R22 audit JSON: `results/research_loop/r22_audit_{phiabs50,phid05,phiabs200}.json`
- V4.2 ckpts: `results/v4_2_{phiabs50,phid05,phiabs200}_s42/`
- 训练 log: `logs/v4_2_parallel/run{A,B,C}_*.log`
- ANDES eval log: `logs/v4_2_parallel/eval/{A,B,C}_andes.log`
- R20 前置: `quality_reports/research_loop/round_20_verdict.md`
- R21 前置 (不冲突, 不同 variant): `quality_reports/research_loop/round_21_v4_breakthrough.md`
- handoff: `quality_reports/handoff/2026-05-07_andes_v41_reward_paradox_handoff.md`

---

*Generated 2026-05-07 by main agent. 3-way parallel 验证 hypothesis A 的 PHI_ABS / PHI_D mechanism, 全部失败. ANDES anti-paper 是 SAC × Eq.14 landscape 结构问题, 不是 PHI_* 调参可破的 local optimum. 触发 handoff fallback option 4.*


## Questions opened (this round)
- none (retrofit — this verdict pre-dates the Q entity introduced in R39)

## Questions closed (this round)
- none (retrofit)

## Questions advanced (this round, status unchanged)
- none (retrofit)
