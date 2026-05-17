# R73 plan — s54 cross-warmup sweep + s55 warmup=20 verify

**Date**: 2026-05-18
**Type**: per-seed hyper optimization
**Wall budget**: ~30 min (6 trainings × 3 parallel)

## Trigger

R72 W4 s54 + warmup=5 v3.1=0.3908 was new canonical. s54 only tested at warmup=5;
need to map s54 U curve like s50/s51/s52 to find true s54 peak.

## Waves

- W1-W3: s54 + warmup ∈ {10, 15, 20}
- W4-W5: s54 + warmup ∈ {25, 30} (cliff probe — s50 cliff at >20)
- W6: s55 + warmup=20 (cross-seed verify warmup=20 family)

## Hypotheses

- H1: s54 peak might shift right (like s50 at warmup=20)
- H2: s54 might have cliff like s50 at warmup≥25 OR might be more robust
- H3: s55 at warmup=20 may beat its warmup=5 score (matching s50 pattern)
