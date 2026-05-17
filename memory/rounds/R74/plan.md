# R74 plan — s51 transition probe + 5-seed expansion + dual-eval enhancement

**Date**: 2026-05-18
**Type**: marginal sweep + tooling enhancement (TDD)
**Wall budget**: ~30 min

## Trigger

R73 closed positive (R73 W3 s54+warmup=20 single SOTA 0.4099 + warmup=20 4-seed
mean 0.3525). User: "继续挤". Plus user asked "评估默认是论文 + 6 维一起吗"
→ proposed score_run.py dual-eval enhancement, user said "做".

## Waves

**W1**: s51 + warmup=20 + EXPLORE_NOISE=0.05 (try fix s51 collapse)
**W2**: s56 + warmup=20 (new seed for 5-seed warmup=20 expansion)
**W3**: s54 + warmup=20 + tau=0.0007 (tau micro-tune)
**W4**: s57 + warmup=20 (6-seed expansion attempt)
**W5**: s51 + warmup=10 (s51 transition probe)
**W6**: s51 + warmup=15 (s51 transition)

**Plus TDD enhancement**: score_run.py dual-eval (cum_rf + 6-axis together)
