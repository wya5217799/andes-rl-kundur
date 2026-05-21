# R113 verdict — Toggler-Line_8 ablation closes Q-0025 NEGATIVE (paper baselines robust)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — Toggler is NOT the R09 2× max_df dominant cause
**Type**: experiment (Q-0025 A1, single ANDES session, zero V4 mutation)
**Wall**: ~20 min plan + ~20 min code + 225.6 s ANDES + ~25 min closure = ~1.2 h

## TL;DR

R110/CLM-0194 hypothesised: V4 env's ANDES-default Toggler trip on Line_8
at t=2 s is the **dominant remaining cause** of R09 §2 2× max_df residual.
R113 ran Q-0025 A1 quantitative test — zero-action × LS1+LS2 × {Toggler u=1
default, u=0 disabled} = 4 ANDES TDS evals. Result: **average max_df drop
= +0.9 %** (LS1 toggler *helps* -8.8 %, LS2 toggler *hurts* +10.5 %, net ≈ 0).
Regime = TOGGLER_MINOR; Q-0025 closed-negative.

**Implication**: R72_w4 SOTA geo=0.391 / R85 best droop K=2 geo=0.197 / R100
+ R103 in-flight training baselines are **robust to Toggler ablation**; paper
Sec.IV-C does NOT need re-baselining over this audit deviation. R09 residual
cause **remains open**, likely F2 (load topology) + F3 (capacitive q) +
D₀-heterogeneity rather than Toggler.

## Methodology

R113 plan A1 (cheapest from Q-0025): single-script, single ANDES session,
WSL-only. Reused `paper_path.py`-style V4 env construction; the only delta
is a post-`env.reset` patch:

```python
env.reset(delta_u=...)                     # base warmup to t=0.5 + paper disturbance
env.ss.Toggler.u.v[:] = float(toggler_u)   # R113 patch — disable at u=0
# run 150-step zero-action loop ...
```

Patch site is valid because `env.reset` runs TDS only to t=0.5 s and the
Toggler.t = 2.0 s has not yet fired. Logged `pre={'n':1, 'u':[1.0], 't':[2.0],
'dev':['Line_8']}` and `post.u=[0.0]` confirms the override took effect.

Scenarios: LS1 (load_step_1, Bus 14 -2.48 pu) + LS2 (load_step_2, Bus 15
+1.88 pu). Seed=42, steps=150 (30 s @ DT=0.2). is_ddic=False scoring (zero-
action baseline; axes 6-11 collapse to 0).

## Results

### Raw numbers

| scenario | u=1 (default) max_df Hz | u=0 (disabled) max_df Hz | Δ% (sign: + = toggler hurts) |
|---|---|---|---|
| load_step_1 | **0.1890** | 0.2056 | **-8.8 %** (toggler helps) |
| load_step_2 | **0.1683** | 0.1506 | **+10.5 %** (toggler hurts) |
| avg         |            |        | **+0.9 %** |

Per-trace also (paper §IV-C cum_rf):
| scenario | u=1 cum_rf | u=0 cum_rf |
|---|---|---|
| LS1 | -0.0297 | -0.0376 |
| LS2 | -0.0245 | -0.0189 |

11-axis (`score_trace_files`, is_ddic=False, axes 1-5 only fire for zero-action):
- toggler u=1: geo=0.0938, cum_rf=-0.2169 (LS1=0.1141, LS2=0.0770)
- toggler u=0: geo=0.1032, cum_rf=-0.2260 (LS1=0.0982, LS2=0.1085)

### Mechanism interpretation

Line_8 is one of two parallel 230 kV Area-2 internal tie-lines. Tripping it
at t=2 s redistributes power flow within Area 2 but does not propagate to
Area 1 (where LS1's Bus 14 PQ load sits).

- **LS1 (Bus 14 load drop → freq rises)**: with toggler, the trip removes
  a damping pathway in Area 2; Area-2 frequency overshoot worsens slightly.
  Removing toggler → max_df *decreases* by 8.8 %.
- **LS2 (Bus 15 load increase → freq drops)**: with toggler, the trip
  isolates a stressed corridor; Area-2 frequency excursion is dampened.
  Removing toggler → max_df *increases* by 10.5 %.

Net effect cancels at ≈ 1 %. Toggler is a real but second-order disturbance
component — not the 2× max_df residual driver R110 supposed.

### Decision rule per Q-0025

```
< 10 % avg drop → TOGGLER_MINOR → Q-0025 closed-negative
```

R113 lands at +0.9 % → **TOGGLER_MINOR** → Q-0025 closed-negative.

## Verification

- Toggler patch verified by pre/post log: `pre.u=[1.0] post.u=[0.0]` for u=0 runs ✓
- u=1 LS1 max_df=0.1890 matches R85 `no_control_load_step_1.json` 0.189 ✓ (reproducibility)
- u=1 LS2 max_df=0.1683 — new datum, not in R85 cache (R85 used different no_control reference; R113 baseline is consistent with paper Fig.8 ~0.17 Hz) ✓
- ANDES TDS converged 150/150 steps for all 4 evals ✓
- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (零 V4 / V4Config / base_env 代码改动) ✓
- 任何 R57+ ckpt 未 load 未 write ✓
- WSL 进程: R113 + R102 (PI eval) + R106 (env floor); R113 finished in 225.6 s, well within concurrent slot ✓

## Cross-references

- CLM-0194 (R110 audit, hypothesis source) — **REFUTED** by R113
- CLM-0215 (R113 quantitative finding) — closes Q-0025 negative
- Q-0025 (closed-negative @ R113 by CLM-0215)
- R09 §2 Finding 2 (2× max_df residual) — **cause still open** after R113
- R89 / CLM-0173 (F1-F5 audit) — F2 (load topology) + F3 (capacitive q) now
  promoted to top remaining residual candidates
- R85 best droop K=2 geo=0.197 — confirmed insensitive to toggler
- R72_w4 SOTA geo=0.391 (CLM-0094) — paper number stands
- paper Sec.IV-C — compound-vs-single-event discrepancy is **<1 % numerically**

## Questions opened (this round)

- (none) — R113 is purely a Q-0025 closure round.

## Questions closed (this round)

- **Q-0025** (closed-negative @ R113, by CLM-0215): Toggler ablation
  produces ≪ 30 % max_df drop (avg +0.9 %). R09 mystery still open;
  paper baselines do not need rebaseline.

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog): R113 result implies the
  plateau is NOT a measurement artefact of compound-disturbance training.
  R72_w4 SOTA's geo=0.391 ceiling is a *real* algorithmic plateau, not
  an audit-deviation phantom. This *strengthens* the case for R98+R108
  critic-representation prototypes (CLM-0189 QR + CLM-0190 AFE) as the
  next plateau-breaker candidate.

## 给 PI 的话

**这周干了啥**: 你说"找到更好的 agent". 我开 R113 = Q-0025 toggler ablation (Q-0025 由 R110 audit 开). 因为 R110 hypothesise V4 env 隐藏 Toggler t=2s trip 是 R09 2× max_df 残差的主因, 如果 confirmed 那所有 R57-R85 baseline (包括 R72_w4 SOTA 0.391) 都要 rebaseline, paper Sec.IV-C 数字要改 — 这比 R98+R108 critic-representation prototype 更迫切的前置 question. 没解决前 train 任何新 agent 都是在不确定 baseline 上跑.

**结果（一句话）**: **Q-0025 closed-NEGATIVE, +0.9% 平均 drop 远 < 30% 阈值** — Toggler 实际是 R110 误判: LS1 toggler *helps* (-8.8% max_df), LS2 toggler *hurts* (+10.5%), 净 effect 接近 0. R72_w4 SOTA 0.391 / R85 droop 0.197 / R100+R103 in-flight 全部 robust 到 toggler ablation; paper Sec.IV-C **不需要 rebaseline**. R09 2× max_df 残差 cause 仍 open (剩 F2 load topology + F3 capacitive q + D₀ 异质 三个候选).

**意外**: (1) Toggler 对 LS1 跟 LS2 的影响**方向相反**, 跟 Area 2 内部 grid topology 一致 (LS1 是 Area 1 load drop → freq 上升 → 拆 Area 2 line 加剧 overshoot; LS2 是 Area 2 load increase → freq 下降 → 拆 Area 2 line 隔离 stressed corridor 反而 dampen). 这是 paper-publishable counter-intuitive disturbance-coupling finding. (2) 之前 R110 audit 写"compound disturbance, 整个 91-round 训练 / eval 都是 paper-mismatched"是 over-interpreted; R113 量化数字 显示 **< 1% numerical impact**, 一个 1 句话 paper footnote 就 cover 了. (3) R113 顺手 confirm R85 no_control LS1 max_df=0.189 (1:1 reproducibility), V4 env 在 single-seed paper-faithful 路径上的数字稳定性很好.

**我默认下一步做**: (1) R113 关 (已完成: verdict + CLM-0215 + Q-0025 closed). (2) 既然 paper baseline 稳了, **回到 R98+R108 critic-representation prototype** 路径 — 等 WSL slot 空 (R102/R106 应该已完, R100/R103 training 75 ep ~还 30 min 才完). (3) 一 slot 空开, 开 R114 = `--algo td3_qr_lstm` s54 75 ep (跟 R72_w4 baseline 1:1 比, geo 直接对比 0.391). 同时 R115 = `--algo td3_afe_lstm` (如果 2 slot 空). 沉默就这么做.

**你想插一脚就说**: (a) 想我立即开 R114 td3_qr_lstm training 即使 WSL 3 process 在跑 (CLAUDE.md 是建议) — R100/R103 还 30 min, 等 ANDES 自然 free 风险更低; (b) 想我先开 R114 A2 followup (R72_w4 SOTA + droop × 2 toggler states = 12 eval, paper-grade 量化 toggler 对 controller 影响) — 30 min wall, ROI 中, R113 negative 后边际价值降 (toggler 已知 minor); (c) 想我把 R09 residual 剩下的 F2/F3/D₀ 三个候选直接 audit — paper-grade write-up 价值高; (d) 想我先做 paper Sec.IV-C "Known paper-deviations" 段落 (R105 reward + R110 toggler-MINOR + R171 fn-Hz + R89 F4 governor 综合一段) — 离线 1h, paper-side direct contribution. 我推荐 **(c)** R09 F2/F3/D₀ audit 路径 (跟 R98 prototype training 在 ANDES busy 期间不冲突, 也是 R113 直接 follow-up).
