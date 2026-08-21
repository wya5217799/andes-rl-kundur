# CONTEXT legacy AD-01 … AD-14 — 2026-05-19 migration snapshot

Moved out of `CONTEXT.md` during the writing-for-agents disclosure pass.
Not current decision authority; current decisions live in `docs/adr/`.

## Legacy architecture decision index

The AD-01 … AD-14 block below is a preserved 2026-05-19 migration snapshot,
not the current decision authority. It may describe paths that were later
changed or never completed. Current decisions live in `docs/adr/`; a
contradiction requires a new ADR that explicitly supersedes the old one.

Status legend: ✅ decided, ⏳ pending, ⛔ rejected.

### AD-01 — V4 env self-contained, V1/V2/V3/NE39 to `_legacy/`  ✅
V4 currently inherits via V1 → V2 → V3 → V4. Reading V4 requires
reading all four. Decision: merge the inheritance chain into a single
`AndesMultiVSGEnvV4` class containing all needed attributes/methods.
Move V1/V2/V3, `andes_ne_env.py`, `andes_ne_regca1_env.py` to
`_legacy/env/andes/`. NE39 envs were never completed (M₀<20 → TDS
divergence; REGCA1 → 6 algebraic+state var DAE bloat).

### AD-02 — `scripts/research_loop/` round + experiment scripts archived  ✅
Of ~41 scripts, only the `eval_v4_*` family is on the paper path
(`eval_v4_no_control.py`, `eval_v4_ddic.py`, `eval_v4_all_seeds.py`,
`eval_v4_ensemble.py`). All `r01_*`–`r36_*` round drivers and
`experiment_*.py` move to `scripts/research_loop/_archive/round_scripts/`.
Research-value preservation is already handled by `memory/rounds/*/verdict.md`.

### AD-03 — Training entry rewritten as `scenarios/kundur/train.py`  ✅
Current state: `train_andes.py` (21 KB, broken `from env.andes_vsg_env import`
that only works via monkey-patch from `train_andes_v4.py` shim) +
`train_andes_warmstart.py` (12.6 KB copy-paste fork). Decision:
clean rewrite as `scenarios/kundur/train.py` accepting all flags including
`--resume <ckpt>` (warmstart is a flag, not a separate file). Old files
move to `_legacy/scenarios/kundur/`.

### AD-04 — `SCENARIOS` dict consolidated  ✅
Currently redefined in 7 eval scripts. Single source of truth is
`probes/andes_common/paper_constants.py`. All eval scripts switch to
`from probes.andes_common.paper_constants import SCENARIOS`.

### AD-05 — `config.py` V1 dead params removed  ✅
Delete `DH_MIN/DH_MAX/DD_MIN/DD_MAX/H_ES0/D_ES0` (V1-era, inconsistent
with V4). Keep `HIDDEN_SIZES/LR/GAMMA/BUFFER_SIZE/BATCH_SIZE` (still in
active use by eval scripts).

### AD-06 — `monitor.py` and `ma_manager.py` resolved by reference graph  ⏳
Both files' status is uncertain (`monitor.py` has broken import to
non-existent `utils/training_callback.py`; `ma_manager.py` may be a
no-op wrapper). Decision: scan reference graph as the first executable
step. Each file is either deleted (no live references) or fixed
(repair import / merge functionality).

### AD-07 — `agents/` gets BaseAgent abstraction  ✅
Define `agents/base_agent.py` with `BaseAgent` abstract class
(`act`/`update`/`save`/`load`). `SACAgent` inherits. `train.py` accepts
`--algo sac` (default) and routes to the right class. Reserved capacity
for future TD3/PPO without rewriting train loop.

### AD-08 — `infra/` abstraction conditional on monitor outcome  ⏳
If `monitor.py` is alive, abstract it (and callback/logger) into
`src/andes_rl_kundur/infra/`. If dead, skip this layer. Decision
deferred to AD-06 outcome.

### AD-09 — `src/andes_rl_kundur/` Python package layout  ✅
Adopt standard src-layout. Package name `andes_rl_kundur` (matches
repo). Library code under `src/andes_rl_kundur/`. Entry scripts under
top-level `scripts/`. Add `pyproject.toml`. All internal imports gain
`andes_rl_kundur.` prefix.

### AD-10 — `artifacts/` for frozen products  ✅
Move `paper/` (IEEE manuscript) and `dissertation/` (UNNC FYP) under
`artifacts/`. `memory/`, `results/`, `docs/`, `_legacy/` stay at root.

### AD-11 — Verification by JSON bit-identical comparison  ✅
Before refactor: run `eval_v4_no_control` and one `eval_v4_ddic` on a
known checkpoint, save output JSONs.
After each phase: re-run, diff JSONs. Tolerance: bit-identical (or
< 1e-6 float drift). Sediment the comparison as
`tests/test_regression.py`.

### AD-12 — Two-phase execution  ✅
Phase 1 (logical cleanup): all changes in AD-01..AD-08 done in-place
(no directory moves). Verify with AD-11. Commit boundary.
Phase 2 (physical reorg): AD-09, AD-10. Verify with AD-11. Commit
boundary. Documentation updates (AD-13) happen after phase 2.

### AD-13 — Feature branch `refactor/clean-arch-2026-05-16`  ✅
All work on this branch. Merge to main only after both phases pass
verification.

### AD-14 — R37 round records the refactor  ✅
`paper_grade_axes.py` relocates to `src/andes_rl_kundur/evaluation/`.
This is a path change, not a logic change. Open R37 with verdict
containing the `git diff` proving logic is byte-identical. Issue a new
claim (`CLM-00XX`) documenting "ranker physical relocation, v4.0
unchanged."

