---
round: R191
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R191 plan — td3_lstm_hreg λ=0.002 s54 with 200ep horizon (test if hreg fixes long-horizon LSTM drift)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop; 200ep horizon retry on R174 hyper)
**Driver**: R174 (75ep) = single-policy SOTA geo 0.4139. R149 (200ep
QR scalar baseline) collapsed to 0.18 — hypothesis was LSTM hidden-
state drift compounding over the longer horizon. hreg λ=0.002 caps
that drift. R191 tests whether hreg stabilises 200ep training.
**Parent**: handoff suggestion (R191 candidate, low ROI but clean
ablation), CLM-0325 (hreg sweet spot), CLM-0330 (R174 SOTA), R149
(200ep scalar collapse).

## TL;DR

Train `td3_lstm_hreg` λ=0.002 at s54 with `--episodes 200`, all other
hypers identical to R174. Three outcomes:

- **Strict break (geo > 0.42)**: hreg unlocks 200ep regime → new SOTA;
  paper headline number updates.
- **≈ R174 (geo 0.41 ± 0.01)**: hreg holds at 200ep but no extra
  benefit; convergence in R174's first 75ep is already saturated.
- **Collapse (geo < 0.40)**: even hreg can't stabilise 200ep; horizon
  is intrinsic limit, not architectural.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --h-norm-reg 0.002 --episodes 200 --seed 54 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --save-dir results/r191_w1_hreg_200ep_s54
```

ANDES WSL ~40-50 min train + ~5 min eval.

## Cross-references

- R174 (SOTA, 75ep): CLM-0330
- R149 (200ep scalar collapse to 0.18)
- CLM-0325 (hreg dose-response peak λ=0.002)
- Handoff `C:\Users\27443\AppData\Local\Temp\handoff-l7X7S1.md`
  (low-ROI completeness candidate)
