---
round: R145
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R145 plan — Focused multi-input magnitude-PD ceiling test (replaces dead R137)

**Status**: DONE
**Opened**: 2026-05-19
**Driver**: R137 wait-chain (multi-input mag-PD 8-combo grid) was killed
by WSL VM reboot at 08:00 (1.5/8 evals completed: base_p_only=0.2602,
plus_dM/LS1 partial). Rather than full 8-combo replay (~40 min), R145
runs only the 2 most informative combos (~12 min wall) to answer the
single key question:
**does adding neighbor obs to classical mag-PD close the 1.50× RL gap?**
**Parent**: R102 (P-only mag-PI = 0.260, CLM-0230), R133 (D5-fair confirm
0.260 same, CLM-0256). R145 is the third axis of fair RL-vs-classical
comparison: input space.

## TL;DR

2 combos × LS1+LS2 × dm_max=600 (D5-fair to R72_w4 training):

1. `plus_nM_nD`: P + neighbor-avg input on both ΔM and ΔD (Kp=2,5 + Kn=1,1)
2. `full`: P + derivative + neighbor on both (Kp=2,5 + Kd=1,1 + Kn=1,1)

Gates:
- best multi-input ≥ 0.30 → multi-input narrows gap, RL advantage <1.30×
- best multi-input ≈ 0.26 → single-input ceiling real, RL retains 1.50×
- best multi-input < 0.20 → multi-input HURTS classical (over-control)

Cache reuse: copies `results/r137_multiinput_mag_pd/base_p_only/no_control_*.json`
where available (D5-fair compatible since same V4Config), saves ~2 evals.

## Cross-references

- CLM-0230 R102 mag-PI 0.260 baseline
- CLM-0256 R133 D5-fair confirmation
- CLM-0094 R72_w4 SOTA 0.391
- R137 dead chain (replaced)
- Paper Eq.11 (obs structure with m=2 neighbors)
