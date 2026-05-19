---
round: R60
state: active
opened: '2026-05-17'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R60 plan — S-tier dual-track: Q-0007 cheap probe + Q-0006 LSTM×anti-smoothness pilot

**Date**: 2026-05-17
**Type**: probe (low-cost open-Q advancement)
**Wall budget**: ~20 min (eval 0.5 min + Q-0006 pilot 12 min + verdict)

## Trigger

User after R58 commit: "启动高价值". Two cheapest open-Q probes
identified from memory scan:
- **Q-0007** (best-by-eval-score): could lift R57-α s50 from 0.109
  to its true ep75 value, pushing 5-seed mean past H1α 0.40 without
  retraining.
- **Q-0006** (LSTM × anti-smoothness reward): only remaining
  structural-pivot lever from R55, never tested. Single-seed pilot
  is 12 min wall, kill-switch design.

## Track A — Q-0007 cheap probe (no training)

**Mechanism**: R57-α s50 `best.pt` is saved at ep10 (pre-training,
random env-warmup). `final.pt` is ep75 (true trained weights).
Cheapest validation of Q-0007's claim: directly eval `final.pt` and
compare 6-axis vs `best.pt = 0.109`.

```bash
/home/wya/andes_venv/bin/python scripts/score_run.py \
    --label r60_q7_lstm_warmup5_s50_final \
    --ckpt-dirs results/td3_lstm_h64_warmup5_s50 \
    --suffix final
```

**Decision criteria**:
- final.pt 6-axis > 0.30: Q-0007 claim validated; final.pt > best.pt
  by 3×+; recommend full Q-0007 implementation in R61.
- final.pt 6-axis between 0.11 and 0.30: Q-0007 directionally
  correct but ep75 still suboptimal; periodic snapshot would be
  needed for full Q-0007 win.
- final.pt 6-axis ≈ 0.10-0.11: Q-0007 claim wrong; s50 is
  *intrinsically* a bad seed (training failure, not selection
  failure). Need to revisit Q-0005 mechanism.

Cost: ~30 sec (1 ANDES proc, 2 scenarios). Runs alongside sanity
(2 ANDES procs total — under 3-proc WSL limit).

## Track B — Q-0006 single-seed pilot (12 min wall)

**Mechanism** (per Q-0006): R55/CLM-0062 established anti-smoothness
reward `r_smooth = -λ·Σ(Δa-Δa_prev)²` with λ=-100 hijacks memoryless
TD3 via exploration-noise channel (deterministic policy → constant).
LSTM bypasses noise-hijack via structurally time-varying policy
(R56/CLM-0063). **Open**: does LSTM + anti-smoothness reach a
HIGHER ceiling (synergistic) or no improvement (antagonistic)?

```bash
LAMBDA_SMOOTH=-100 SMOOTHNESS_WINDOW=1 \
/home/wya/andes_venv/bin/python scripts/train.py \
    --algo td3_lstm --normalize-actions --episodes 75 --seed 51 \
    --hidden-size 64 --lstm-lr-warmup-eps 5 \
    --save-dir results/r60_q6_pilot_lstm_smoothw1_s51 \
    --log-interval 10
```

Then eval:
```bash
/home/wya/andes_venv/bin/python scripts/score_run.py \
    --label r60_q6_pilot_lstm_smoothw1 \
    --ckpt-dirs results/r60_q6_pilot_lstm_smoothw1_s51
```

**Decision criteria** (vs R57-α s51 = 0.526):
- pilot geo > 0.55: **synergistic** → expand to 3-seed sweep
  (s49/s50/s51) + W=10 variant. Possibly new V4 SOTA.
- 0.45 ≤ pilot geo ≤ 0.55: **neutral** → reward shape orthogonal to
  policy class. Close Q-0006 as "no significant effect".
- pilot geo < 0.45: **antagonistic** → LSTM somehow still vulnerable;
  abandon. Close Q-0006 negative.

Cost: 12 min training + 30 sec eval. With sanity still running,
total ANDES procs = 2-3 (sanity + train + brief score_run overlap).

## Hypotheses

- **H1** (Q-0007): final.pt > best.pt for s50 by ≥ 3×
- **H2** (Q-0006): LSTM + λ=-100 > 0.526 (synergistic)

H1 is high-prior (R57 mechanism literally predicts this). H2 is
genuinely unknown — first test of the policy×reward interaction.

## Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Parallelism | sanity + Q-0006 train + brief Q-0007 eval | 3 ANDES procs at peak ~30s, within limit |
| Q-0007 implementation | **Defer** to R61+ if H1 positive | Cheap probe sufficient to advance Q; full impl needs eval-hook in train.py |
| Q-0006 W variant | Start W=1 (R50 setting); W=10 if H2 positive | W=10 was R55 candidate |
| Seed for Q-0006 pilot | s51 only | best R56/R57 seed; kill-switch design |

## Risk register

| Risk | Mitigation |
|---|---|
| Q-0006 pilot collides with sanity for ANDES license/proc limit | Stagger: sanity at ~40% done, pilot starts now; both finish ~equal time |
| Q-0007 final.pt eval blocked by sanity | score_run is fast (~30s); negligible interference |
| H1 fails (final.pt ≈ best.pt for s50) | Reframes Q-0005 (seed-50 intrinsic failure) as primary; close Q-0007 negative |
| Pilot diverges (LSTM + anti-smoothness breaks) | Hypothesis-confirming antagonistic outcome; still a finding |

## Schema plan

- **CLM-0073** (conditional, from sanity if it completes) — s51
  paper_strict_pure 500-ep result
- **CLM-0074** (finding/V) — Q-0007 cheap-probe result: R57-α s50
  final.pt 6-axis vs best.pt 0.109
- **CLM-0075** (finding/V) — Q-0006 pilot result: LSTM + λ=-100 W=1
  s51 6-axis vs R57-α s51 0.526
- Q-0006 status: closed (positive | negative | neutral)
- Q-0007 status: advanced or closed depending on H1

## What R60 does NOT establish

- Full Q-0007 implementation (eval-hook in train.py) — deferred R61+
- Multi-seed robustness of Q-0006 result — pilot is kill-switch only
- 500-ep convergence (Q-0008) — separate round
