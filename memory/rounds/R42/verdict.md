# R42 verdict — Code deepening pass (4 candidates, full execution)

**Date**: 2026-05-16
**Status**: **COMPLETE**. All 4 deepening candidates landed; 56/56
pytest cases green; bit-identical behaviour where comparable.
**Type**: infrastructure (architectural refactor, no experiment)
**Wall**: ~4 h (grilling + TDD restart + execution)

## TL;DR

Four architectural deepening refactors identified by
`/improve-codebase-architecture` landed as 5 commits on R42.
`paper_path.run_scenario` collapses the 3-way eval-script copy-paste
into one injectable-policy loop. `agents.checkpoint_loader.load_agents`
is now the single source of truth for the `agent_{i}_{suffix}.pt`
convention + SAC/TD3 detection. `scenarios.kundur.training_checks`
extracts 12 paper-faithful Check Protocol implementations out of
`utils/monitor.py` (cutting it from 1029 → 632 lines); the
`register_check` seam introduced by R37 / CLM-0042 is now load-bearing.
`memory.tools.validate._load_entities` dedups the claim + question
loaders. Full test sweep including the 100-second V4 env regression
stays green.

## What changed

| Commit | Hash | Candidate | Scope |
|--------|------|-----------|-------|
| 1 | `42948db` | C1 | `evaluation/paper_path.py` + 3 eval-script refactors |
| 2 | `46a9281` | C2 | `agents/checkpoint_loader.py` + 3 eval-script switches |
| 3 | `ef473e0` | C4 | `scenarios/kundur/training_checks.py` (12 Check classes) + monitor.py cleanup (1029 → 632 lines) + Check Protocol extension + train.py wire-in + 25 new TDD tests |
| 4 | `2dfbb43` | C3 | `memory/tools/validate._load_entities` private helper |
| 5 | (this) | — | R42 verdict (dogfood of R39 5-section template) |

## TDD discipline restart

C4 was first attempted as a horizontal slice — wrote all 12 Check
classes in one 560-line file before any test. User invoked `/tdd`
mid-stream to enforce the vertical-slice rule from the TDD skill
(*"one test → one impl → repeat; never write all tests first then all
code"*). The speculative file was reverted; C4 then proceeded as 5
TDD batches, each Check getting its tracer test before its impl:

- **Tracer**: `ActionCollapseCheck` (calibration-aware window check —
  most representative pattern)
- **Batch 1** (+2): `RewardComponentRatioCheck`, `ActionSaturationCheck`
- **Batch 2** (+4): `RewardPlateauCheck`, `RewardDivergenceCheck`,
  `TDSFailureRateCheck`, `FreqOutOfRangeCheck`
- **Batch 3** (+3): `PhysicsFrozenCheck`, `AgentRewardDisparityCheck`,
  `LossExplosionCheck`
- **Batch 4** (+2): `EarlyStoppingCheck` (the sole stateful one),
  `RewardMagnitudeCheck`
- **Wiring** (+2): `register_kundur_default_checks` attachment + factory
  fresh-instance discipline

The restart cost ~30 min of repeated work but locked the cleaner
test-driven design. Every Check class now has a positive trigger test
and a negative quiet-state test exercising the public
`log_and_check`/property path of `TrainingMonitor` — no private-state
poking.

## Verification

```
$ pytest tests/                                       # full suite, WSL
============= 56 passed, 1 warning in 100.42s (0:01:40) =============
$ pytest memory/tools/tests/                          # memory tests, host
======================== 38 passed, 1 warning in 0.38s ========================
$ python memory/tools/validate.py
OK: 49 claims, 3 questions, 9 warnings
```

The 100-second test cost is the V4 env regression (1e-9 tolerance
against PRE_REFACTOR baseline JSONs) — paper-cited path stays
bit-identical.

## Behavior parity (C4)

The 12 extracted Check classes preserve the deleted `_check_*()`
methods' triggers literally:
- Same thresholds, same arithmetic, same auto-calibration logic
- The R27 2026-05-07 downgrade of `reward_divergence` from `stop` to
  `warn` is preserved in `RewardDivergenceCheck`
- Plug-in loop cooldown (lifted from `_emit_check`) applies to all
  warn-class triggers exactly like before
- Print formatting (`[STOP]` / `[!]` icons, `TRAINING STOPPED` /
  `WARNING` labels) preserved
- One latent `ZeroDivisionError` fix in `RewardMagnitudeCheck` manual
  mode (when `expected_range` had a 0 boundary) — locked by
  `test_reward_magnitude_check_triggers_in_manual_mode`

The training loop's stop signal is unchanged: `should_stop = monitor.
log_and_check(...)` still returns True iff any registered check returns
`severity='stop'`. `register_kundur_default_checks(monitor)` in
`train.py` attaches the same 12 checks that previously lived inside
the monitor — net training behaviour identical modulo the cooldown
edge case below.

**Cooldown behaviour edge case**: the old plug-in loop did NOT apply
cooldown to user-registered checks. After R42, ALL checks (including
the 12 defaults and any user check) get cooldown. This means a
research-script Check returning `severity='warn'` is now throttled at
50 episodes per check name. This is a small behaviour change; mitigated
by the cooldown being warn-only and `stop` triggers always firing.

## Cross-references

- `memory/rounds/R42/plan.md` — original 4-candidate plan with A/B/C
  trade-off analysis per candidate
- `memory/rounds/R37/verdict.md` — introduced the Check Protocol seam
  (CLM-0042) that C4 finally made load-bearing
- `memory/rounds/R39/verdict.md` — the 5-section verdict template this
  verdict is the second instance of (R40/R41 also use it)
- `src/andes_rl_kundur/evaluation/paper_path.py` — new module (C1)
- `src/andes_rl_kundur/agents/checkpoint_loader.py` — new module (C2)
- `src/andes_rl_kundur/scenarios/kundur/training_checks.py` — new
  module (C4)
- `memory/tools/validate.py` — `_load_entities` extracted (C3)

## Out of scope (per anti-overengineering)

- SAC/TD3 mixin split: Explore agent's deletion test failed it
- Cosmetic naming (`_iter_round_dirs` → `_list_round_dirs`)
- Substring section match (intentional legacy-format tolerance)
- Path traversal guard on `closed_round`/`opened_round` (trusted
  single-user repo)

## Questions opened (this round)

- (none — purely infrastructural; no research uncertainty raised)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)
