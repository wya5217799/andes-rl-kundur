# R152 verdict — Independent verification of R153 HAWE ensemble (parallel race)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (redundant with R153 / CLM-0280; provides independent verification)
**Type**: experiment (ensemble eval, no training)
**Wall**: ~30 min (4 eval waves)

## TL;DR

R152 launched the same 3-way HAWE ensemble eval that parallel-session R153
also launched. Both independently discovered the **same plateau breaker**:
3-way mean ensemble of {R72_w4 baseline, R142 td3_qr_lstm, R143 td3_qr_lstm
mean-loss-fix} = geo **0.4043** (+3.5% over R72_w4 0.3908). R152 confirms
R153's findings with separately-computed eval runs and slightly different
weighted-aggregator weight choices.

## Methodology

`scripts/eval_ensemble.py` — HAWE (Heterogeneous Actor Weighted Ensemble)
with `mean / weighted / median` aggregation. Ckpt-dirs:
- `results/r72_w4_lstm_tau001_warmup5_s54` (baseline)
- `results/r142_w1_qr51_s54` (QR critic, buggy loss)
- `results/r143_w1_qr51_s54_fixed` (QR critic, mean-loss-fix)
- `results/r150_warmh0_qr_s54` (warmh0 + QR, weak; used for 4-way only)

V4 paper-faithful LS1+LS2, seed=42, steps=150, deterministic actors,
recurrent hidden-state reset per scenario.

## Results

5 ensemble configurations tested:

| Config | geo | LS1 | LS2 | cum_rf | Δ baseline |
|--------|-----|-----|-----|--------|------------|
| R72_w4 single (ref) | 0.3908 | 0.354 | 0.431 | -0.0750 | — |
| R142 single | 0.3845 | 0.362 | 0.408 | -0.1015 | -1.6% |
| R143 single | 0.3843 | 0.362 | 0.407 | -0.1015 | -1.7% |
| R150 single | 0.3498 | 0.338 | 0.362 | n/a | -10.5% |
| **R152-W1 3-way mean** | **0.4043** | **0.376** | 0.435 | -0.0844 | **+3.5%** ⭐ |
| R152-W2 3-way weighted (0.5/0.3/0.2) | 0.3996 | 0.364 | 0.439 | -0.0786 | +2.3% |
| R152-W3 3-way median | 0.3844 | 0.363 | 0.408 | -0.1015 | -1.6% |
| R152-W4 4-way mean (+ R150) | 0.3973 | 0.376 | 0.420 | -0.0884 | +1.7% |
| R152-W5 2-way mean (R72_w4+R142) | 0.3997 | 0.364 | 0.439 | -0.0786 | +2.3% |

**Findings (cross-verifies R153 / CLM-0280)**:

1. **3-way uniform mean is the sweet spot** (0.4043). Any deviation
   (weight skew, median agg, member addition/removal) regresses.
2. **2-way (R72_w4+R142) = 0.3997**: R143 contributes specifically to
   LS1 (0.364 → 0.376, +1.2pp); LS2 negligibly affected. R143's
   independent QR-loss-fix produces just enough policy variation to
   bump LS1.
3. **Weighted (best-heavy 0.5/0.3/0.2) < uniform** by 1.2pp:
   down-weighting the QR variants reduces the diversity-bonus that
   averages away R72_w4's bang-bang quirks. Equal weighting wins.
4. **Median collapses to ~R142 level** (0.3844): per-action median of
   3 actors selects the 2 QR-LSTM ckpts in agreement against the 1
   scalar-critic ckpt. Median ≈ R142 single.
5. **4-way (+R150 weak member) regresses** to 0.3973: adding a
   member that didn't fully converge to bang-bang pulls the
   averaged policy away from the local optimum. Diversity is
   **not unconditionally good**; constituents must each be near-optimal.

## Mechanism interpretation

The 0.4043 lift is purely on LS1 axis (+6.1pp over R72_w4 single).
LS2 is essentially unchanged (0.435 vs 0.431, +0.4pp). The 3 ckpts
all converge to similar bang-bang policies at deterministic eval, but
the QR-critic-trained variants (R142/R143) shape a slightly different
value landscape → minor per-step action perturbations during LS1
transient → averaging smooths the bang-bang spikes that hurt LS1's
P_balance and dD_smoothness axes.

cum_rf -0.084 is **worse** than R72_w4 single -0.075 (paper-metric
slightly degrades), so the geo lift trades 11-axis structural metrics
for paper-metric path cost. Paper writeup must disclose this trade-off.

## R152 vs R153 (parallel duplication)

Both rounds independently arrived at the same plateau-breaker. R153's
CLM-0280 is canonical; R152 serves as **independent verification** —
same code (`eval_ensemble.py`), same ckpts, slightly different
parameter choices (R152 used weighted 0.5/0.3/0.2, R153 used 0.45/0.3/
0.25; both report ~0.40 = uniform-mean dominates weighted variants).

The duplication is harmless: same conclusion reached twice strengthens
the finding. R152 records the independent eval files under
`results/r152_ensemble/` (5 summaries), R153 records them under
`results/r150_ensemble_test/` (4 summaries). Both directories are
useful for paper figure data redundancy.

## Cross-references

- CLM-0280 (R153 canonical claim, this round verifies)
- CLM-0275 (R142 QR baseline-equivalent)
- CLM-0144 (91-round plateau)
- R142/R143/R150 verdicts (constituent ckpts)
- R85 / CLM-0184/0186 (RL 2× advantage over classical)

## Questions opened (this round)

- (none directly; CLM-0280 already opens cross-seed ensemble + member
  selection rule as next R154+ candidates)

## Questions closed (this round)

- (none directly; R152 closes itself as redundant verification)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**: PI 默认推荐 R150 verdict (c) — 3 个 ckpt ensemble eval。我 reserve R152 + launch 5 wave (3-way mean / 3-way weighted / 3-way median / 4-way / 2-way). 同时 parallel session 拿到 R153 并 launch 同样实验。两条线 race。

**结果（一句话）**: 两 session **独立 confirm 同样发现** — 3-way mean ensemble {R72_w4 + R142 + R143} = **geo 0.4043 (+3.5% above R72_w4 0.391)**, 是 R57-R152 100+ training run 之后 **第一次** single-axis intervention 把 geo 推到 0.40+. 我 R152 5 wave 给完整 ablation: 3-way mean wins, 2-way (drop R143) = 0.3997 lose 1.1pp on LS1, 4-way (add weak R150) = 0.3973 lose 1.7pp, weighted (0.5/0.3/0.2 best-heavy) = 0.3996 lose 1.2pp, median = 0.3844 collapses to R142 single level. **diversity 必须 with uniform weighting + near-optimal constituents**.

**意外**: (1) parallel session 同 round (R153) 同时做 + 同 CLM ID (0280) 写 — 撞车. 我 R152 写 verdict 时发现 CLM-0280 已被 R153 占, 转 R152 为 "independent verification" 角色, 数据互相 backup. (2) **median 比预期更糟** — 我以为 median 会跟 mean 一样好, 实际 median 给 3 actor 时选 2-vs-1 majority 投票, R72_w4 (1 vote) 输给 R142/R143 (2 votes 同算法) → median 失去 baseline diversity → 退化到 R142 single 水平. ensemble agg 选择对结果敏感. (3) **R143 contribution 全在 LS1** — 2-way mean 跟 weighted (down-weight R143) 都给 0.3997, 加 R143 才到 0.4043; R143 给 LS1 +1.2pp 但 LS2 几乎 0. R143 (mean-loss-fix) 在 LS1 transient 上有 unique 政策 angle.

**我默认下一步做**: (1) R152 close 完成, CLM-0280 (R153 already canonical) 已 cite. (2) **R154 = cross-seed ensemble** — CLM-0280 "what's still open" 第一项. 训 R72_w4 same hyper at s49 (单 ANDES wave ~15 min), 再 ensemble {R72_w4_s54 + R72_w4_s49 + R142_s54}. cross-seed averaging 通常给 larger lift than cross-algo same-seed (well-known ensemble theory). (3) R149 200ep s54 还在跑 (~ep 80/200 last checked), 等出来后可加进 ensemble. (4) 期间 zero-ANDES 副诊: per-action sign analysis 看 3 个 ckpts 在哪些 step 不 agree (这是 ensemble lift 的来源).

**你想插一脚就说**: 我 autonomous mode 默认 (2)+(3)+(4). 沉默 = 立刻 launch R72_w4 hyper s49 训练 (R154-W1).
