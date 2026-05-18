# Phase 3 — R77 review-round experiments

Five experiments requested by the 5-reviewer round (commit 4a3fa72):

| # | Experiment | Wall | Status |
|---|---|---|---|
| E1 | 3 seeds × 500-ep convergence study | ~21 h | running (sequential after E4) |
| E2 | s59 wu20 re-train ×3 for within-version SD | ~3 h | running (first up) |
| E3 | Code-drift bisection R58→R65 (8 commits) | ~8 h | TODO (needs git worktree setup) |
| E4 | Critic-init re-roll on 5 dead seeds (full-RNG re-roll proxy) | ~5 h | running (after E2) |
| E5 | Simulink LS1 cross-render on s54 | 1 day | DEFERRED (user opted out) |
| E6 | NE-39 second benchmark | 1 week+ | BLOCKED (ADR-01: M₀<20 TDS divergence) |

## Launch (E1+E2+E4 sequential, background)

```bash
nohup bash artifacts/paper_r77/phase3/launch.sh \
    > results/r77_phase3/nohup.log 2>&1 < /dev/null & disown
```

Status file: `results/r77_phase3/STATUS.txt` (one line per major step,
human-readable timestamps).

## Outputs

Per-experiment checkpoint + train.log under
`results/r77_phase3/<exp>_<config>/`:

- E2: `e2_s59_rerun_{1,2,3}_off{100,200,300}/`
- E4: `e4_reroll_s{49,53,57,58,60}_off1000/`
- E1: `e1_500ep_s{54,56,59}/`

After all done, run `score_run.py --label r77_phase3 --ckpt-dirs ...`
to collect v3.1 scores and update Table I + new appendix tables.

## E3 (manual, when ready)

See `results/r77_phase3/e3_TODO.md` — bisection procedure across 8
commits (R58 e8427df → R65 4c5327a) to isolate the 19% LSTM
regression. Leading suspect: R61 monitor extension (atexit handler).

## E5 / E6 status

- **E5** deferred by user request (this Phase 3 batch skips Simulink work).
- **E6** blocked: per ADR-01, NE-39 envs never completed because all 10
  SGs include some with $H < 10$ s and the V4 environment requires
  $M_0 \geq 20$ for TDS convergence. Either retire the $M_0$ floor (env
  change), enable an NE-39 env class from `_legacy/`, or move to a
  different second benchmark (WSCC 9-bus, IEEE 68-bus reduced).
