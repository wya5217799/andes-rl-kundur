---
round: R186
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R186 plan — td3_qr_lstm at s49 (Q-0005 critic-side mechanism test)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, Q-0005 critic-side test)
**Driver**: R183 + R185 split the Q-0005 collapse picture: hreg
rescues s50 (actor-state mechanism) but not s49 (critic-saddle
mechanism). R186 tests **pure critic-side intervention** at s49:
does QR distributional critic alone rescue what hreg couldn't?
**Parent**: CLM-0345 (R183 hreg s49 collapse), R185 verdict (s50 rescue).

## TL;DR

Train `td3_qr_lstm` (distributional critic, no hreg) at s49 75ep.
Bypasses the parallel-session R184 QR+hreg loader bug by using the
already-tested `td3_qr_lstm` agent class (R142 / R181 worked).

Three outcomes:
- **RESCUED (geo ≥ 0.30)**: QR critic alone rescues s49 → mechanism
  confirmed as critic-gradient-saddle; paper Sec.IV-D gets a clean
  two-mechanism story (actor vs critic; hreg for one, QR for the other).
- **PARTIAL (0.10 ≤ geo < 0.30)**: QR partly mitigates → mechanism is
  composite; R187 candidate = QR+hreg at s49 after loader fix.
- **STILL COLLAPSE (geo < 0.10)**: Neither actor nor critic
  intervention alone is sufficient; mechanism is env/replay-side.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_qr_lstm \
    --episodes 75 --seed 49 --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --save-dir results/r186_w1_qr_lstm_s49
```

ANDES WSL ~15 min train + ~5 min eval.

## Why pure QR (not QR+hreg)

Parallel session R184 trained `td3_qr_lstm_hreg` at s54 but
`checkpoint_loader.py` cannot load it (eval crashed with
GaussianActor key mismatch — same loader-not-updated bug as
R168 CTDE / CLM-0320). Using `td3_qr_lstm` instead:
- Avoids loader bug
- Cleanly isolates the critic-side question
- If QR alone works, the QR+hreg stack can be tested separately
  once loader is patched

## Cross-references

- CLM-0345 (R183 s49 still collapse with hreg)
- CLM-0275 (R142 td3_qr_lstm at s54 = geo 0.3845)
- CLM-0320 (R168 SAC CTDE loader fix — same pattern)
- R185 verdict (s50 rescue picture)
