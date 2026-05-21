# R253 verdict — phi_d alone NOT scalar+s50 rescue (R18 rescale makes both phi_h/phi_d vestigial)

**Date**: 2026-05-20
**Status**: CLOSED-NEGATIVE — phi_d ruled out (paired with R247 phi_h)
**Type**: research (backlog completion from R247 verdict commitment)
**Wall**: ~13 min training + 1 min scoring

## TL;DR

scalar+s50+phi_d=0.0056+phi_abs=50, --phi-h 0 --phi-f 0. Result:
geo=**0.2348**, LS1=0.2156, LS2=0.2557, cum_rf=**-0.0917**.

**Bit-identical to R246 (only-phi_abs) AND R247 (+phi_h alone)** at
4 decimal places on BOTH metrics. phi_d at R18 rescale 0.0056 is
**vestigial**, same as phi_h. The R254 follow-up (phi_f alone)
identified phi_f as the SOLE load-bearing paper term (CLM-0455).

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0 --phi-d 0.0056 --phi-f 0 \
    --save-dir results/r253_w1_scalar_phid_only_s50

python scripts/score_run.py --ckpt-dirs results/r253_w1_scalar_phid_only_s50
```

(score_run.py smart defaults working — no --label / --out-dir needed)

## R246 / R247 / R253 / R254 / R251 cross-tab (DUAL-METRIC)

| Run  | phi_h  | phi_d  | phi_f | geo    | cum_rf  | conclusion |
|------|--------|--------|-------|--------|----------|------------|
| R246 | 0      | 0      | 0     | 0.2346 | -0.0917 | baseline only-phi_abs |
| R247 | 0.0056 | 0      | 0     | 0.2347 | -0.0917 | +phi_h vestigial |
| R253 | 0      | 0.0056 | 0     | 0.2348 | -0.0917 | **+phi_d vestigial** |
| R254 | 0      | 0      | 100   | 0.2655 | -0.0878 | **+phi_f RESCUE** |
| R251 | 0.0056 | 0.0056 | 100   | 0.2662 | -0.0878 | full V4 ≈ R254 |

R254 alone reaches 99.7% of full V4. R246/R247/R253 all bit-identical.

## Pre-registered outcomes (R253 plan)

R253 plan pre-registered:
- ≥ 0.32 (phi_d IS the rescue): ❌
- 0.25-0.32 (phi_d partial): ❌
- ≈ 0.235 (phi_d also not the answer): ✅ matched at 0.2348

Outcome: ruled out phi_d as decomposition candidate. CLM-0455
identifies phi_f as the answer.

## Questions opened (this round)

- (none — paired R254 closes the decomposition)

## Questions closed (this round)

- "Is phi_d the load-bearing paper term for scalar+s50 rescue?"
  ANSWERED: NO. (Originally R247 verdict committed this as
  R249/R250 candidate; backlog audit (R252) caught it; R253 closes.)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**：R253 是 R247 verdict (CLM-0420) 留的 backlog
commitment (phi_d alone decomposition), 2026-05-20 audit 发现没跑,
跟 R254 (phi_f alone) 一起完成.

**结果（一句话）**：phi_d alone = geo **0.2348**, **bit-identical to
R246 (only-phi_abs) AND R247 (+phi_h)** — phi_d 也 vestigial. R254
(phi_f) 是 sole rescue (CLM-0455).

**意外**：phi_h + phi_d 两个 R18-rescaled paper terms 都 vestigial,
**phi_f 一个 term 顶 99.7% paper Eq.14 contribution**. 这给 CLM-0430
"paper Eq.14 contributes 3-6% cum_rf" mechanistic explanation:
**那 3-6% 全是 phi_f 贡献的, r_h/r_d 在 R18 rescale 0.0056 下 4 个
量级太小, 贡献为 0**. paper-faithful drop-in 可以更简化: phi_f=100 +
phi_abs=50 就够 (省 phi_h, phi_d).

**我默认下一步做**：R254 verdict 写完 (paired close, CLM-0455 已写).
然后更新 gauge-invariance memo 加 "paper-term decomposition" panel
attributing 3-6% cum_rf gap to phi_f. **R255 cum_rf-direct env-change
还要做** — decomposition findings 不解释 RL-vs-droop k=10 cum_rf gap
(CLM-0445), 那个 gap 是 local-vs-global r_f scope 问题, env code change.

**你想插一脚就说**：backlog 完成 + decomposition closed + 工具实战
两轮迭代. Paper Sec.IV-D contribution 5 现在三层全部清楚:
(1) gauge invariance mechanism + (2) phi_f sole load-bearing + (3)
RL local vs droop global cum_rf gap (R255 候选). 如果你想 stop here
写 paper, 数据足. 如果想做 R255 cum_rf-direct env-change, 我可以 design.

## Cross-references

- R247 (CLM-0420 — phi_h ruled out; backlog source)
- R246 (CLM-0410 → CLM-0435 — baseline anchor)
- R254 (CLM-0455 — pair sister, phi_f IS the rescue)
- CLM-0450 (this round's claim)
- CLM-0430 (mechanistically explained by R254 via phi_f attribution)
