# R96 verdict — Cross-ckpt RETRACTS CLM-0163 headline; methodology lesson

**Date**: 2026-05-19
**Status**: DONE — single-wave closure with consequential correction
**Type**: cross-ckpt validation / negative finding / methodology audit
**Wall**: ~107 s ANDES + regression + report

## TL;DR

R96-W1 ran the [[CLM-0163]] D3 obs→return + obs→action regressor pipeline
on **4 SOTA ckpts** (R72 W4 LSTM warmup=5, R75 W2 LSTM warmup=20, R63 W4
TD3-MLP combo, td3_norm h64 — across two algorithm classes and two
hyper basins). **Same R72_w4 ckpt, second run, gave R²=+0.659 at γ=0.99
instead of CLM-0163's −0.410**. Cross-ckpt median at γ=0.99 = +0.642
(all positive). **CLM-0163's "value-horizon mismatch at paper γ=0.99"
mechanism story is RETRACTED** by [[CLM-0168]] — was MLP regression
noise (N_train=80 + 64×2-layer MLP, torch RNG unseeded, agent3 R²=−1.7
outlier in R91 pulled median negative).

**What survives**: obs is highly predictive of action across all ckpts
(median R² = 0.97), confirming policy is near-myopic. The plateau
mechanism question is **back open**: not critic ([[CLM-0160]]), not
obs-for-action ([[CLM-0168]]), not value-horizon (now refuted).
Surviving candidates: env stochasticity (R84-D4, unrun), reward shape
(PHI_ABS=50 dominance), policy class / non-convex landscape.

## Methodology

`scripts/r96_d3_cross_ckpt.py`. Same regressor pipeline as R91 (4 R1
γ ∈ {0, 0.9, 0.99, 1.0} obs→return MLPs + 1 R2 obs→action MLP, 80/20
split, 64×2 hidden, dropout 0.1, 300 epochs Adam lr=1e-3). Per ckpt,
1 ANDES rollout LS1+LS2 × 50 steps × 4 agents = 400 records, cross-agent
median test R².

ANDES occupancy: 4 × ~25s = ~100s total, single slot, no other
contention during R96 run (R85-classical and R94-widen training did
not conflict).

Skipped R3 (obs+h)→action and R4 obs→next_obs for cross-ckpt simplicity;
TD3 MLP ckpts have no LSTM h_actor.

## Per-ckpt R²

| Ckpt | Algorithm | R² γ=0 | R² γ=0.9 | R² γ=0.99 | R² γ=1.0 | R² obs→action |
|---|---|---|---|---|---|---|
| r72_w4_lstm_warmup5_s54  | TD3+LSTM   | +0.887 | +0.418 | **+0.659** | +0.299 | +0.897 |
| r75_w2_lstm_warmup20_s59 | TD3+LSTM   | +0.904 | +0.340 | +0.625 | +0.539 | +0.952 |
| r63_w4_td3_combo_s49     | TD3 MLP    | +0.980 | +0.141 | +0.386 | +0.611 | +0.988 |
| td3_norm_h64_s49         | TD3 MLP    | +0.973 | +0.416 | +0.757 | +0.625 | +0.992 |
| **median**               |            | +0.939 | +0.378 | **+0.642** | +0.575 | +0.970 |

R72_w4 row at γ=0.99: **+0.659** (R96) vs **−0.410** (R91 in CLM-0163).
Same ckpt, same script logic, same scenario+seed+steps. The two runs
diverge purely on **torch RNG state at MLP init** (neither R91 nor R96
seed torch's RNG). N_train=80 with ~10k MLP params + dropout +
random batch order → R² has run-to-run variance comparable to its
signal magnitude. R91's agent3 hit a particularly bad-fit local optimum
(R²=−1.7), pulling the median negative.

## What survives vs what retracts

**Survives** (CLM-0168):
- **R2 obs→action R²=0.970 cross-ckpt** (range 0.897-0.992). Policy is
  essentially memoryless on all 4 ckpts, independent of recurrence.
- **CLM-0160 on-manifold critic confidence** (separate finding, not
  touched by this methodology problem — R96 didn't re-run D2b).
- **The R57-R82 91-round plateau evidence** (CLM-0144) — orthogonal.

**Retracted** (CLM-0163, superseded by CLM-0168):
- R²=−0.41 at γ=0.99 as evidence of value-horizon mismatch.
- "Plateau is value-horizon mismatch at paper γ=0.99" mechanism story.
- R85 PRIORITY 1 = γ ablation, which was justified on the mismatch
  hypothesis.

**Now open / candidates re-promoted**:
- R84-D4 env stochasticity floor (never run).
- Reward shape ablation (paper_strict_pure on R72_w4 hyper).
- Policy class / non-convex optimization landscape.
- Multi-seed MLP D3 redo with proper variance reporting.

## Infrastructure changes (R96)

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建:
- `scripts/r96_d3_cross_ckpt.py`
- `results/r96_d3_cross_ckpt/summary.json`
- `results/r96_d3_cross_ckpt_stdout.log`
- `memory/rounds/R96/{plan.md, verdict.md}`
- `memory/claims/CLM-0168.md` (correction, supersedes CLM-0163)

V4 regression test 不需重跑 (零 env 改动). 4 SOTA ckpts read-only loaded.

## Cross-references

- [[CLM-0163]] (retracted by CLM-0168 via this round)
- [[CLM-0160]] (on-manifold critic confidence — independent, stands)
- [[CLM-0164]] (Q-0015 closure — independent, stands)
- [[CLM-0144]] (R57-R82 91-round plateau — mechanism back to open)
- R91 plan / R91 verdict (D3 wave that produced the retracted finding;
  R91's regressor methodology is the audit subject)
- R86 plan (cross-ckpt synthetic monotone — different methodology, also
  produces large run-to-run variance under prior obs)

## Questions opened (this round)

- (none new — the methodology lesson is in CLM-0168, not Q-form)

## Questions closed (this round)

- (none — no open Q was directly resolved)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algo backlog) — plateau mechanism back to open after
  CLM-0163 retraction. Q-0014 advanced negatively: the "value-horizon"
  candidate is no longer a candidate.

## 给 PI 的话

**这周干了啥**：你说 autonomous-loop "继续研究". 本来想做 cross-ckpt 验证
CLM-0163 (R91 D3) 的 "γ=0.99 R²=−0.41" 是不是 R72_w4 specific 或 paper
setup universal. 在 4 个 ckpt 上 re-run 完全相同的 regressor pipeline.

**结果（一句话）**：**CLM-0163 被自己的 cross-ckpt RE-run 推翻**. 同
R72_w4 ckpt, R96 跑出 γ=0.99 R²=**+0.659**, 不是 R91 的 **−0.410**.
所有 4 ckpt cross-ckpt 在 γ=0.99 都给正 R² (0.39 到 0.76, 中位 +0.64).
"obs 不能预测 paper γ discounted return" 这条 headline 是 **MLP 不稳定
artifact**, 不是真信号. 写 CLM-0168 (correction, supersedes CLM-0163).

**意外**：(1) **N_train=80 + 64×2 hidden MLP + 未 seed torch RNG = R²
run-to-run variance 大到能 flip sign**. R91 那次 agent3 撞 R²=−1.7 拉低
median 到 -0.41, R96 不同 torch init 同 ckpt 同数据给 +0.66. 这是 critical
methodology lesson, 写在 CLM-0168 里, 未来 D3-style regressor 必须 (a)
多 seed ensemble + 报 mean±std, (b) 用 ridge 而非 MLP, (c) 至少 5×
samples. (2) **R2 obs→action 在所有 4 ckpt 都 R²>0.90**, median 0.97 —
policy 几乎 memoryless 在所有算法 class 都成立, 这条 R91 finding **是真
universal**, paper 可以引用. (3) **plateau mechanism 回到 open 状态** —
CLM-0160 推翻 critic 病, CLM-0168 推翻 value-horizon, 剩下 R84-D4 env
stochasticity / reward shape / policy class / non-convex landscape 候选.

**我默认下一步做**：(1) R96 closure + CLM-0168 retraction 写完 ✓.
(2) 不开新 round, **停下来交付 retraction PI 简报**, 让你知道 CLM-0163
是错的, 别基于它写 paper. (3) 如果你继续 "继续研究", 我建议开 R97 =
**R84-D4 env stochasticity floor** (单 SOTA × 多 disturbance/IC seed ×
deterministic eval, 量化 σ_geo / mean_geo), 因为这条还没人测过, 也是
RL 项目最常 deceiving 的隐藏 ceiling. 沉默 = 开 R97.

**你想插一脚就说**：(a) 想我现在立刻 multi-seed MLP D3 redo (R72_w4
× 10 torch seed × 4 γ × 4 agent = 160 fits, ~5 min wall) 看 γ=0.99 R²
真分布是 [-0.4, +0.7] 还是更窄区间 — 推荐, 是 CLM-0168 retraction 的
最 rigorous 收尾. (b) 想直接转 R84-D4 — 也可以, 但 retraction 没数据
支撑会显得仓促. (c) 想接受 CLM-0168 retraction 然后跑 R72_w4 hyper
× paper_strict_pure reward × 75 ep s54 (PRIORITY 2 from CLM-0168) —
1 个 training run, ~30 min wall, 占 1 slot. 我推荐 (默认) 先 (a) 把
retraction 数据稳了, 再决策 (b) 或 (c).
