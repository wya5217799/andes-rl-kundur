---
round: R188
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R188 plan — hreg λ=0.002 s49 + seed-offset=100 (test env/replay-side Q-0005 hypothesis)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, direct env-side mechanism test)
**Driver**: CLM-0350 closed Q-0005 as partial: s49 collapse mechanism
ruled out for actor (hreg) and critic (QR), narrowed to env/replay-side.
R188 directly tests this via `--seed-offset 100`: same logical seed
s49 but **different env/replay trajectory**. If it rescues, env-side
mechanism CONFIRMED; if it still collapses, mechanism is deeper.
**Parent**: CLM-0350.

## TL;DR

Train td3_lstm_hreg λ=0.002 at s49 with --seed-offset=100, 75ep. The
trick: `--seed-offset` affects env reset and replay-buffer sampling
RNG without changing the logical seed label. Three outcomes:

- **RESCUED (geo ≥ 0.30)**: env/replay-side mechanism CONFIRMED.
  Paper Sec.IV-D gets a clean three-mechanism story (actor / critic /
  env-replay), and the "lucky seed s54" caveat reduces to a "lucky
  RNG path" caveat — addressable by warmup randomisation.
- **PARTIAL (0.05 < geo < 0.30)**: env-side helps but doesn't fully
  rescue → mechanism is multi-factor.
- **STILL COLLAPSE (geo ≤ 0.05)**: env-side rules out → s49 has a
  truly s49-specific issue beyond RNG path; possibly initial network
  weights from the seed.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 49 --seed-offset 100 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r188_w1_hreg_s49_offset100
```

ANDES WSL ~15 min train + ~5 min eval.

## Why this is the right next test

After R183/R185/R186 narrowed Q-0005 to env/replay-side, the cleanest
single test is to perturb env/replay while keeping algorithm and
logical seed identical. `--seed-offset` does exactly this — it changes
the env-reset RNG sequence and replay-buffer sampling order without
touching network init or training hyper.

If offset=100 changes the outcome, it proves the mechanism is path-
dependent (env stochasticity), not seed-dependent (initial conditions).

## Cross-references

- CLM-0350 (Q-0005 closed-partial; s49 narrowed to env/replay)
- CLM-0345 (R183 hreg s49 collapse)
- R186 verdict (QR s49 collapse)
- R174 (single-policy SOTA at s54, same hyper)
