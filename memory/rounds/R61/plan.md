---
round: R61
state: active
opened: '2026-05-17'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R61 plan — SAC HAWE eval + Q-0007 full implementation

**Date**: 2026-05-17
**Type**: implementation (Q-0007) + eval (SAC HAWE)
**Wall budget**: ~30 min code + tests + 15 min HAWE eval + 3 min 4-seed final.pt eval + verdict

## Trigger

R60 PI briefing "我默认下一步做" — user replied "做立即做的". Two SS-tier
tracks from R60 verdict:

- **Track A — SAC HAWE on R58 radsec ckpts** (~5 min eval, zero training)
- **Track B — Q-0007 full implementation** (~30 min code)

## Track A — SAC HAWE ensemble on R58 strict_radsec

5 ensemble configs over R58 SAC s49/s50/s51 (paper_strict_pure_radsec):
- mean (1/3 each)
- median (4-actor)
- s50-anchor (0.2/0.6/0.2)
- top2 s50+s51 (0/0.6/0.4)
- top2 s50+s49 (0.4/0.6/0)

Eval on R58 paper_strict_eval 20-scen test set under paper-faithful
config. Compare to R58 SAC s50 single ckpt = -0.397 total / -0.518
3-seed mean.

## Track B — Q-0007 full implementation

Add `--eval-every-n-eps N` flag to `train.py`. Every N episodes
during training (after warmup), run paper-metric eval probe (LS1+LS2
anchors, ~5 s) and save `agent_i_best_eval.pt` on score improvement.

Changes:
1. `paper_strict_eval.py`: add `evaluate_agents_paper_metric()` helper
2. `monitor.py`: add `best_eval_callback` + `update_eval_score()` method
3. `train.py`: add CLI flag + eval probe call in training loop
4. `tests/test_q0007_eval_tracked_best.py`: 10 TDD tests

Default disabled (N=0). Typical N=5 → ~5 % wall overhead.

## Track C (added in-round) — R57 final.pt 5-seed Q-0007 probe

After Track B implementation, sanity-check the Q-0007 mechanism by
running `score_run.py --suffix final` against all 5 R57-α seeds
(s49/s50/s51/s52/s53). This refines the R60 cheap-probe finding
(CLM-0074) which had only s50.

## Hypotheses

- **H_A**: SAC HAWE config beats s50 single (-0.397). R44/R48
  experience says ensemble usually +5-10 %.
- **H_B**: Q-0007 full impl will lift 5-seed mean past H1α 0.40.

## Schema plan

- **CLM-0077** (decision/S) — Q-0007 full implementation
- **CLM-0078** (finding/V) — SAC HAWE result (vs s50 single)
- **CLM-0079** (finding/V) — R57-α 5-seed final.pt scan, refines CLM-0074
