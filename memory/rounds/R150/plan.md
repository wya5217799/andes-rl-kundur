---
round: R150
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R150 plan — TD3+LSTM+WarmH0+QR (no AFE) s54 — plateau breaker candidate

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "继续 + 找到更好的 agent". After CLM-0275 confirmed (a) QR alone
matches R72_w4 baseline 0.391 at s54, (b) AFE structurally broken at all
seeds: R150 tests the orthogonal combination CLM-0188 warm-h_0 + CLM-0189
QR distributional critic **without AFE**. If this exceeds 0.391, it's a real
plateau breaker.
**Parent**: CLM-0275 (R98 QR validated, AFE falsified) + CLM-0188 (warm-h_0 universal).

## TL;DR

New agent class `TD3LSTMWarmH0QRAgent` (already shipped + 38/38 tests pass):
- Actor: WarmH0RecurrentActor (R107 implementation, learnable h_0 from obs_0)
- Critic: RecurrentQRDoubleQCritic (R98 distributional, canonical Dabney 2018 sum-over-pred)
- No AFE input expansion (CLM-0190 falsified, AFE drags down even working QR)

Train 75 ep paper-faithful s54, compare against R72_w4 baseline 0.3908 and
R142 QR-only baseline 0.3845.

## Gate

- BREAKTHROUGH (geo ≥ 0.45): plateau broken, warmh0+QR exceeds R72_w4 by ≥15%
- CONFIRM (geo ≥ 0.41): warmh0 adds small but real lift over QR-alone
- MARGINAL (0.37-0.40): warmh0 doesn't help beyond QR alone
- REGRESS (< 0.30): warmh0 actor + QR critic incompatible

## Command

```bash
LR=1e-4 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 nohup python -u scripts/train.py \
  --algo td3_warmh0_qr_lstm --qr-n-quantiles 51 \
  --episodes 75 --seed 54 --hidden-size 64 --tau 0.001 \
  --normalize-actions --lstm-lr-warmup-eps 5 \
  --save-dir results/r150_warmh0_qr_s54 --final-eval
```

## Code shipped this round

- `src/andes_rl_kundur/agents/td3_warmh0_qr_lstm.py` — new agent class
- `scripts/train.py` — added `--algo td3_warmh0_qr_lstm` dispatch (import +
  choices + ctde/warmstart mutex + build_agents elif)
- `src/andes_rl_kundur/agents/checkpoint_loader.py` — load dispatch added
- 38/38 unit tests pass (no new tests but no regressions)

## Cross-references

- CLM-0275 (R142 breakthrough, AFE falsified)
- CLM-0188 (R104 warm-h_0 universal feasibility, N=9 ckpts)
- CLM-0157(a) (R86 distributional priority)
- R142 verdict (R98 QR validated at s54)
