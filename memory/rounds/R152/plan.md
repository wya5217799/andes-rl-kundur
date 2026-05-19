---
round: R152
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R152 plan — 3-way ensemble eval of plateau-saturating ckpts

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI brief (R150 verdict, recommendation (c)): "建 ensemble eval of
{R72_w4, R142, R143} ckpts — combined policy might exceed individual 0.39".
Zero training, single ANDES wave.
**Parent**: CLM-0275 (R142 QR matches baseline), R150 (warmh0+QR underperforms),
R142+R143 (both ~0.385).

## TL;DR

3 ckpt-dirs (R72_w4 LSTM baseline 0.391, R142 QR-LSTM 0.385, R143 QR-LSTM
loss-fixed 0.384) ensembled with mean action aggregation. Tests whether
**different policy families** (vanilla TD3-LSTM scalar critic vs
distributional 51-quantile critic) average to a policy that escapes the
~0.39 attractor. Sometimes ensembles break plateaus by averaging away
mode-specific quirks.

If geo > 0.42: ensemble breaks plateau, paper Sec.V can write "ensemble
escapes single-policy plateau". If geo ≤ 0.41: ensemble doesn't help,
confirms env-ceiling story.

## Methodology

```
PY=/home/wya/andes_venv/bin/python
$PY scripts/eval_ensemble.py \
    --ckpt-dirs \
        results/r72_w4_lstm_tau001_warmup5_s54 \
        results/r142_w1_qr51_s54 \
        results/r143_w1_qr51_s54_fixed \
    --suffixes best best best \
    --agg mean \
    --label r152_ens3_mean_baselines \
    --out-dir results/r152_ensemble
```

Single ANDES WSL slot, ~15 min, deterministic eval, V4 paper-faithful
LS1+LS2.

## Gate

- **BREAK (geo ≥ 0.42)**: ensemble escapes; paper Sec.V Ensemble section.
- **MARGINAL [0.40, 0.42]**: small lift; depends on cost-of-policy story.
- **NULL [0.37, 0.40]**: ensemble = baseline; no surprise.
- **REGRESS (< 0.37)**: averaging hurts (action signs may cancel).

## 资产保护契约

零 training, 零 ckpt mutation. R72_w4 / R142 / R143 read-only. New
files: `scripts/r152_ensemble.sh` (or inline), `memory/rounds/R152/{
plan.md, verdict.md}`, 1 CLM.

## Cross-references

- CLM-0144 (91-round plateau)
- CLM-0275 (R142 QR baseline-equivalent)
- R150 verdict (recommends this as (c))
- R85 / CLM-0184 / CLM-0186 (RL 2× advantage over classical)
