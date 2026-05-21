---
round: R195
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R195 plan — hreg + widened action bounds (DM/DD-max=1200) at s54

**Status**: ACTIVE (training in flight, started 2026-05-19 15:15)
**Type**: research (autonomous loop; closes R119 dead branch under hreg)
**Driver**: Handoff Task #18 (R119-W1 widen-bound, killed by previous
session, never completed). Per handoff: "low priority per R100
mechanism story, but re-launch candidate if PI wants completeness."
R195 tests action-bound axis at SOTA hyper family (hreg λ=0.002) to
close that dead branch.

## TL;DR

Train `td3_lstm_hreg` λ=0.002 at seed=54 with widened action bounds
DM-max=1200, DD-max=1200 (default presumably 1.0). All other hypers
match R174 SOTA.

Three outcomes per handoff "R100 mechanism story":
- **NEW SOTA (geo > 0.42)**: action bound was load-bearing; closes
  R119 question with positive answer; paper claim updates.
- **≈ R174 (geo 0.41 ± 0.01)**: action bound is not load-bearing under
  hreg; R119 dead-branch closed-negative under the SOTA algorithm
  family. Most likely outcome per R100 critic-monotone story.
- **Collapse (geo < 0.40)**: widened bound destabilises; argues
  bounded-action is essential constraint.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --h-norm-reg 0.002 --episodes 75 --seed 54 \
    --hidden-size 64 --tau 0.001 \
    --dm-max 1200 --dd-max 1200 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --save-dir results/r195_w1_hreg_widebound_s54
```

ANDES WSL ~15 min train + ~5 min eval (longer under CPU contention
with R194 in parallel).

## Cross-references

- R119 (action-bound dead branch, killed by previous session)
- R100 (CLM-0148/0149 critic-monotone-on-action: argmax at ±1 boundary
  with default bound, suggests bound is the binding constraint)
- R174 (SOTA at default bound) - CLM-0330
- Task #18 in TaskList (R119-W1 widen-bound DEAD)
- Handoff `C:\Users\27443\AppData\Local\Temp\handoff-l7X7S1.md`
