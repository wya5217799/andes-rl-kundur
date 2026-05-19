---
round: R100
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R100 plan — LSTM hidden-norm regularisation training, falsify CLM-0181/0182

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究，一直继续，别问我了". R93 zero-ANDES forensics
(CLM-0180/0181/0182) identified divergent LSTM internal dynamics as the
mechanism behind R72_w4's bang-bang policy (76% action saturation
documented at CLM-0170). R93-W2 spectral analysis: g-gate spectral
radius = 1.54 (> 1.0), ||c'_0|| = 0.50 (zero state not a fixed point).
R94 PRIORITY 1 per CLM-0182 = LSTM hidden-norm regularisation. R94-R99
got eaten by parallel sessions, R100 reserved.

**Parent**: CLM-0170 (76% saturation), CLM-0181 (LSTM-drift empirical),
CLM-0182 (g-gate spectral radius > 1).

## TL;DR

Train 1 wave at R72_w4 same hyper + seed 54 + 75 ep using new
`td3_lstm_hreg` algo (subclass of `td3_lstm` adding L2 penalty on
actor LSTM hidden-state norm: `actor_loss += λ_h * mean(||h_actor||²)`).
λ_h = 0.01 baseline; falls back to vanilla td3_lstm if 0. Falsifies
the LSTM-drift mechanism: if reg lifts geo above 0.391, CLM-0181 +
CLM-0182 confirmed; if reg degrades geo or stays at 0.391, drift is
not load-bearing.

## Methodology

### New agent class `TD3LSTMHRegAgent` (already implemented)

`src/andes_rl_kundur/agents/td3_lstm_hreg.py` — subclasses TD3LSTMAgent,
unchanged everywhere except `update()`:

```python
# Inside actor-update roll:
h_norms_sq.append((h_a_actor[0] ** 2).sum(dim=-1).mean())
...
h_reg_loss = torch.stack(h_norms_sq).mean()
actor_loss = actor_q_loss + self.h_norm_reg_lambda * h_reg_loss
```

Wired into `scripts/train.py` as `--algo td3_lstm_hreg` + `--h-norm-reg LAMBDA`.

### Training command (Wave 1, λ_h = 0.01)

```
python scripts/train.py \
    --algo td3_lstm_hreg --h-norm-reg 0.01 \
    --episodes 75 --seed 54 \
    --hidden-size 64 \
    --lr 0.001 --tau 0.001 \
    --normalize-actions \
    --lstm-lr-warmup-eps 5 \
    --save-dir results/r100_w1_hreg_lambda0p01_s54
```

(R72_w4 hyper recap: td3_lstm, hidden=64, lr=0.001→ clamped to 1e-4 by
default unless LSTM_LR_UNCLAMP=1, tau=0.001, warmup_eps=5,
normalize-actions, 75 ep, seed 54.)

ANDES WSL slot needed (~15 min wall).

### Eval (final eval automatic in train.py)

Wave outputs final_eval_summary.json with 11-axis geo (paper convention)
plus monitor_data.csv per-episode action stats.

## Gate criteria

- **CONFIRM (geo ≥ 0.42)**: above R72_w4 baseline 0.391 by ≥ 7% (≥ +0.03).
  LSTM-drift mechanism confirmed; CLM-0181/0182 promoted to V+T trust.
  R101 paper-grade multi-seed sweep recommended.
- **MARGINAL (geo ∈ [0.34, 0.42])**: in baseline noise range. Inconclusive.
  R101 should test larger λ_h (0.03, 0.1) before drawing conclusions.
- **REGRESS (geo < 0.34)**: regularisation hurts. LSTM drift is part of
  what makes R72_w4 work; CLM-0181 mechanism story incomplete.
  Pivot to R101 = widen action bounds (orig R93-W1) or different actor
  head architecture.

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / R72_w4 ckpt / 任何
R57+ ckpt. 新建:
- `src/andes_rl_kundur/agents/td3_lstm_hreg.py` (DONE)
- `scripts/train.py` 4 处增量: import + --algo choice + --h-norm-reg
  arg + new elif branch + 2 处 algo-name 包含 list (DONE)
- `memory/rounds/R100/{plan.md, verdict.md}`
- `memory/claims/CLM-≥0190` (avoid 0183-0189 race buffer)
- `results/r100_w1_hreg_lambda0p01_s54/` outputs

## Cross-references

- CLM-0170 (76% saturation, R92-W1)
- CLM-0181 (LSTM-drift empirical, R93-W0b)
- CLM-0182 (g-gate spectral radius > 1, R93-W2)
- CLM-0149/0153/0154 (R84 critic-affine, definitively superseded)
- CLM-0144 (R57-R82 91-round plateau, falsifies if R100 lifts geo)
- Q-0014 (algo backlog — recommend close after R100)
