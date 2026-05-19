---
round: R42
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R42 plan — Code deepening pass (4 candidates)

**Date**: 2026-05-16
**Type**: infrastructure (architectural refactor, no experiment)
**Status**: in-progress

## Trigger

`/improve-codebase-architecture` skill identified 4 deepening
opportunities post-R39 (memory active oracle). User authorised full
execution including the higher-risk C4.

## Decisions (locked via grilling)

Order of execution: **1 → 2 → 4 → 3** (per leverage × distance to
current pain). Designed to land as 4 commits + 1 verdict.

### C1 — `paper_path.py` extraction (HIGH leverage)
- New module `src/andes_rl_kundur/evaluation/paper_path.py`
- Exports `run_scenario(scen_name, delta_u, *, action_fn, label,
  seed=42, steps=150) -> dict`
- `action_fn(step, obs_dict, n_agents) -> dict[int, np.ndarray]` is
  the policy interface (injected by caller)
- Centralises: env construction, scenario loop, trace formatting,
  cum_rf / max_df / osc computation, JSON-shape dict assembly
- `eval_no_control.py` / `eval_ddic.py` / `eval_ensemble.py` retain
  argparse + their unique action_fn; delegate the eval loop
- Function-not-class per anti-overengineering
- Does NOT call `paper_grade_axes` (separation of concerns: eval
  produces traces; ranker analyses)

### C2 — `agents/checkpoint_loader.py` extraction (MEDIUM leverage)
- New module `src/andes_rl_kundur/agents/checkpoint_loader.py`
- Exports `load_agents(ckpt_dir, suffix='best', n_agents=None,
  hidden_sizes=None) -> list`
- Centralises: `agent_{i}_{suffix}.pt` naming, `_detect_algo()`
  (SAC vs TD3 from ckpt's `algo` field), instantiation branching
- `eval_ddic.py` / `eval_ensemble.py` / `eval_all_seeds.py` switch to it
- Function-not-class (anti-overengineering)

### C4 — `scenarios/kundur/training_checks.py` extraction (HIGH risk)
- New module `src/andes_rl_kundur/scenarios/kundur/training_checks.py`
- 12 `Check` Protocol implementations, each holding its own
  thresholds + internal state
- Extend `Check` Protocol: `run(monitor_view) -> CheckResult` where
  `monitor_view` is a Protocol exposing `recent_rewards(window)`,
  `recent_action_stats(window)`, `recent_env_health(window)`,
  `calibration_data` property, `user_check_config(name)`
- `TrainingMonitor` implements `MonitorView` Protocol; existing
  `register_check()` seam is reused
- `_DEFAULT_CHECKS` dict + 12 `_check_*()` methods + `_run_all_checks` +
  `_run_manual_checks` deleted from `monitor.py`
- Default check registration: `monitor = TrainingMonitor(); for chk in
  KUNDUR_DEFAULT_CHECKS: monitor.register_check(chk)` becomes
  the new default factory
- **Regression contract**: identical TDD synthetic-episode tests
  trigger the same warnings before/after — no full-training rerun
  needed (anti-overengineering: trust the unit tests)

### C3 — `_load_entities` dedup in `memory/tools/validate.py` (LOW leverage)
- Extract private `_load_entities(dir, prefix, *, extras=None)`
- `load_claims` / `load_questions` become 5-line wrappers
- Trivial; reduces 42 lines to 25; same tests stay green

## Execution (5 commits)

| Commit | Scope | Verification |
|--------|-------|--------------|
| 1 | C1: `evaluation/paper_path.py` + refactor eval_no_control/eval_ddic/eval_ensemble | Manual review (eval scripts have no test infra); functional smoke test if WSL available |
| 2 | C2: `agents/checkpoint_loader.py` + eval scripts switch | Manual review; TDD on the loader itself |
| 3 | C4: `scenarios/kundur/training_checks.py` + extend Check Protocol + delete from monitor.py | TDD synthetic-episode tests asserting same triggers fire before/after |
| 4 | C3: `_load_entities` dedup | Existing 38 memory tests stay green |
| 5 | R42/verdict.md (5-section template dogfood) | `validate.py` accepts verdict structure |

## Verification gates

After each commit:
- `cd memory/tools && python -m pytest tests/ -v` → 38+ tests green
- `python memory/tools/validate.py` → 44+ claims clean
- `python memory/tools/render.py` → STATE.md regenerates

For C4 specifically:
- New unit tests for each of the 12 Check classes (synthetic input
  → expected trigger or no-trigger)
- The unit tests are the regression contract; no full training rerun

## Out of scope

- SAC/TD3 mixin split (Explore agent's deletion test failed it)
- `_iter_round_dirs` rename (cosmetic)
- Substring section match in validate (intentional tolerance)
- R43 onwards (any new experiment after this infrastructure round)

## Risks

- **C4 is paper-cited path-adjacent**: training warnings/stops control
  whether a run is interrupted. If trigger logic drifts, training
  behaviour drifts. Mitigated by TDD synthetic-episode comparison.
- **Parallel session collision**: R38–R41 + R42-menu were committed
  by Codex during the grilling pass. The 4 deepening targets are
  orthogonal to TD3 / V4Config work — no expected conflicts, but
  rebase carefully if HEAD moves during execution.
- **Eval-script regression risk**: C1 refactor changes call structure
  but trace JSON shape is preserved (same dict keys, same metrics).
  Reviewable via diff of one before/after JSON if a baseline ckpt
  is handy.

## Addresses Questions

- (none — this is infrastructure)
