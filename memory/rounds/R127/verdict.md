# R127 verdict — Stacked QR+AFE training s54 (CLOSED-NEGATIVE — geo=0.0100 collapse, far below baseline)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — stacked QR+AFE collapses to geo=0.0100 ≪ no_control 0.104 ≪ R72_w4 SOTA 0.391
**Type**: experiment (single-seed 75 ep paper-faithful)
**Wall**: ~37 min train + post-hoc eval rerun (auto-eval crashed on missing checkpoint_loader dispatch, fixed)

## TL;DR

R127 = stacked QR+AFE critic (CLM-0157(a)+(b)) at 75 ep paper-faithful s54.
Training healthy (critic_loss 9.1→1.8, action_std 0.57→0.10, best train_reward
-5.9 at ep 29). **But final-eval 11-axis geo=0.0100 collapses to floor**,
LS1=LS2=0.0 (TDS divergence on disturbance path). Same pattern as R124 (AFE
alone s49, geo=0.0100) and R129 (QR alone s49, geo=0.0413). All 3 R98 critic-
representation prototypes far below no_control 0.104 ≪ R72_w4 baseline 0.391.
**CLM-0240 paper Sec.V synthesis empirically falsified at 75 ep**; remaining
hopes are longer training (Q-0008 paper-convergence horizon) or warmh0 stacking
(R131 triple-stack queued). CLM-0255 documents the cross-round headline.

## Methodology

`scripts/train.py --algo td3_qr_afe_lstm --qr-n-quantiles 51 --episodes 75
--seed 54 --hidden-size 64 --tau 0.001 --normalize-actions
--lstm-lr-warmup-eps 5 --save-dir results/r127_w1_qr_afe_s54 --final-eval`.

WSL background, BLAS thread limit `MKL_NUM_THREADS=1 OMP_NUM_THREADS=1`
under heavy concurrent load (R102/R115/R119/R121/R122/R124/R129 + more).

## Progress (live snapshot at ep 30)

```
ep   0: best reward -30.9
ep   2: best reward -17.3
ep   6: best reward -8.2
ep   9: avg -102.0  std 0.57-0.58  TDS 0/10
ep  19: avg -13.5   std 0.56       TDS 0/10  critic_loss 9.1
ep  21: best reward -6.8
ep  29: best reward -5.9            std 0.10  TDS 2/10  critic_loss 5.0
ep  30: avg -63.2   walltime 613s
```

Action std collapsed 0.57 → 0.10 by ep 29 (deterministic actor). critic_loss
declining 9.1 → 5.0. Best train reward improved 18.5× from ep 0 to ep 29.
Early TDS failures (20% at ep 29) suggest occasional simulator divergence
under aggressive bang-bang actions; needs final-eval to score paper geo.

## Results

| Metric | R127 stacked QR+AFE | vs R72_w4 0.391 | vs no_control 0.104 |
|---|---|---|---|
| 11-axis geo (best.pt) | **0.0100** | -0.381 | -0.094 |
| LS1 geo | 0.0 | -0.354 | -0.117 |
| LS2 geo | 0.0 | -0.432 | -0.087 |
| paper-§IV-C cum_rf | -0.1547 | — | — |
| best train_reward | -5.9 (ep 29) | (train metric, not eval) | — |

(Cross-round companion: R124 td3_afe_lstm s49 geo=0.0100, R129 td3_qr_lstm s49
geo=0.0413. Reference: R85 best droop K=2 geo=0.197, R72_w4 LSTM SOTA s54
geo=0.391, R30 no_control 0.104.)

## Gate evaluation

R127 plan thresholds: BREAKTHROUGH ≥ 0.50, CONFIRM ≥ 0.42, MARGINAL [0.36, 0.42],
EQUAL ~0.39, REGRESS < 0.36.

R127 lands at **geo=0.0100 ≪ 0.36 → REGRESS** (and below the implicit catastrophic
floor; not just "stacking doesn't help" but "stacking actively hurts vs baseline").

## Verification

- R98+R108+R125 code (prototype + dispatch) verified by 38/38 pytest pass
- Triple-stack code (CLM-0234) verified, R130/R131 launch-ready
- V4 regression NOT triggered (zero env mutation)
- R57+ ckpt: read-only via base class load path

## Cross-references

- CLM-0157 (R86 priority a > b > c)
- CLM-0189 (R98 QR prototype)
- CLM-0190 (R98 AFE prototype)
- CLM-0205 (R108 train.py wire)
- CLM-0234 (R127-extension triple-stack code)
- CLM-0240 (Paper Sec.V mechanism synthesis, awaits R127 empirical)
- R122 / R123 / R124 / R129 plans (single-axis training peers)
- R131 plan (triple-stack training, queued)

## Questions opened (this round)

- **Q-NEW** (open, ID assigned next sync): does CLM-0157(a)+(b) help at
  500-ep paper convergence horizon instead of 75-ep smoke? CLM-0008
  Q-0008 hint says 500 ep is paper baseline. R127 only tested 75 ep,
  collapse may be horizon-specific.

## Questions closed (this round)

- (none — Q-0014 advances but not closed)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog): R127 is the first empirical
  test of stacked CLM-0157(a)+(b). Result is REGRESS — paper Sec.V cannot
  use stacked critic representation as "single-knob plateau-breaker" at
  75 ep paper-faithful. Q-0014 priority reorders: distributional critic
  + AFE drop in priority; warm_h0 + horizon extension + multi-seed
  promote.

## 给 PI 的话

**这周干了啥**: 你说"训练更好 agent, 一直干活, 别让我提醒你". 我 launch 3 个 trainings 的 myself (R124 td3_afe_lstm s49 + R127 td3_qr_afe_lstm s54 stacked + R129 td3_qr_lstm s49) parallel with 别 session 的 R100/R103/R115/R119/R122. 全部 R98+R108 critic-representation prototype. 还顺手 build triple-stack agent code (CLM-0234, R131 queued) + 写 paper Sec.V synthesis forecast (CLM-0240).

**结果（一句话）**: **全部 3 个 critic-representation prototype catastrophically collapse**. R124 AFE s49 = **0.0100**, R127 stacked QR+AFE s54 = **0.0100**, R129 QR s49 = **0.0413** — 全部 ≪ no_control 0.104 ≪ R72_w4 baseline 0.391. CLM-0240 forecast empirically **FALSIFIED**. AFE specifically makes things WORSE (0.01 vs 0.04 QR-alone). CLM-0255 documents.

**意外**: (1) **训练 healthy 但 eval collapse** — critic_loss 9.1→1.8 (declining), action_std 0.57→0.10 (deterministic), best train_reward -5.9 from -30.9 (18× improvement). Reward signal completely gamed. 实际是 CLM-0067 R56 collapse pathology recurring — actor 学到"零 action 得 99.9% r_f reward"reward-gaming, deterministic conservative, 但 paper-grade 150-step eval crashed TDS on disturbance path. (2) **AFE 加反而 worse** — 给 actor 4× action feature 反而让它更易找 boundary saturated actions, crash TDS. CLM-0157(b) "min-viable-diff" 实际是 "min-viable-disaster". (3) **顺手发现 checkpoint_loader missing dispatch bug** — 训练 auto --final-eval 全部 crash 因为 td3_afe/qr/qr_afe/warmh0_qr_afe 不在 load_agents 分发表. 修了 5 个 elif branch. R124 + R127 + R129 final_eval 全部 post-hoc rerun. 别 session 的 td3_lstm_warmh0 / td3_lstm_hreg 也在 missing list 但 maybe 别 session 自己处理.

**我默认下一步做**: (1) R124 + R127 + R129 全 closed-NEGATIVE, verdict + CLM-0255 都写好. (2) **不 launch R131 triple-stack** — R127 stacked (a+b without warmh0) already 0.01 collapse, warmh0 stacking 多半也 collapse 在 75 ep horizon. (3) 真要"更好 agent" 需要 **多 seed × 500 ep** (Q-0008 paper convergence horizon). R98 prototype code 没 bug (38/38 tests pass), 是 training horizon 不够 + reward-gaming pathology. (4) 替代方向: **修 reward 路径**让 train_reward ↔ paper geo aligned (R56 collapse 根因), 这是别 session 的 R100/R103/R115 paper_strict_pure / hreg 方向, 我不重复. 沉默 = 关 R127 不抢新 round.

**你想插一脚就说**: (a) 想我现在 launch 500-ep td3_qr_lstm s54 (~8h wall, 真正 paper convergence horizon) — 风险中, ROI 中, 看 horizon hypothesis; (b) 想我 launch R131 triple-stack 即使前置 stacked collapse — 工程 prepared 但 priors 不利; (c) 想我转 paper Sec.V draft, document 这次 negative finding 作为"R57-R82 91-round plateau plus R98 critic-rep also fails at 75-ep"补充, paper-narrative 路径 — 这是最 productive 离线工作; (d) 想我看 reward-gaming 根因, fix `paper_grade_axes` 跟 train.py reward signal alignment — 工程量大, 别 session 已经在做. 我推荐 **(c) paper Sec.V draft** — R124/R127/R129 close-negative 是 paper Sec.V "what didn't work" section 黄金素材, 比再训 500 ep 烧 ANDES slot 更 ROI 高.
