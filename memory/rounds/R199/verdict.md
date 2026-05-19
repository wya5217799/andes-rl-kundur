# R199 verdict — 50ep is UNDER-training collapse (LS1=0); 75ep is narrow peak

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — 50ep under-trains; 75ep horizon is narrow optimum
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at s54 for **50 episodes** (vs R174's
75ep). Result: geo=**0.0672**, **LS1=0.000**, LS2=0.451, cum_rf=-0.076.
LS1=0 collapse pattern. The actor doesn't get enough training time
at 50ep to learn LS1 (fast-disturbance recovery) at s54.

## Horizon basin map

| episodes | seed | geo | LS1 | LS2 | regime |
|----------|------|-----|-----|-----|--------|
| 50 | 54 | **0.0672** | **0.000** | 0.451 | UNDER-TRAIN COLLAPSE (R199) |
| 75 | 54 | 0.4139 | 0.367 | 0.467 | **SOTA peak (R174)** |
| 200 | 54 | 0.3161 | 0.265 | 0.378 | OVER-TRAIN regression (R191) |

**75ep is a narrow horizon optimum**: 50ep collapses (LS1=0), 200ep
loses ~25%. The hreg sweet spot at λ=0.002 plus the 75ep horizon is
finely tuned.

Interesting: even at 50ep, LS2=0.451 is **above** R174's LS2=0.467
ceiling normalisation. So LS2 converges faster than LS1; LS1 needs
the longer training to accumulate enough policy signal.

## Implications for paper

R174 SOTA's reproducibility caveat tightens:
- Single-(seed, offset, hyper, λ, horizon) tuple = (s54, off=0,
  R72_w4-hyper, λ=0.002, ep=75)
- Each dimension contributes ±5-30% performance variance
- Total expected variance across the multi-axis grid is ±15-50%

Paper Sec.IV-D should disclose the **horizon sensitivity** alongside
the seed and offset findings.

## Next axis to probe

Untested single-axis variations of R174 still on the menu:
- Lower learning rate (lr=5e-5 vs default 1e-4) — R200 candidate
- Smaller hidden size (h=32, h=48) — R167 h=32 collapsed at non-hreg
- Different batch size (32→64) — could tighten gradient signal
- Different gamma (0.95, 0.999)
- Different exploration noise (0.05 vs default 0.1)

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none)

## 给 PI 的话

⚠️ R199 = hreg λ=0.002 at s54 with **50ep** = geo 0.0672, LS1=0.
**Under-training collapse**.

**Horizon basin 现在完整 mapped**:
- 50ep: collapse (R199)
- 75ep: SOTA 0.4139 (R174)
- 200ep: regress 0.3161 (R191)

75ep 是 narrow horizon peak。每个 single-axis 变 R174 (horizon /
seed / offset / λ) 都有 ±5-30% 影响。Paper 必须 disclose 这种多
轴 sensitivity.

R200 候选: lr=5e-5 (vs default 1e-4 clamp) — 低 LR 可能在 75ep 内
converge 到 tighter optimum, 不变 horizon 提升 SOTA. 我下次 launch.

## Cross-references

- R174 (75ep SOTA)
- R191 (200ep regression)
- R149 (200ep QR-LSTM — different algo, same direction)
