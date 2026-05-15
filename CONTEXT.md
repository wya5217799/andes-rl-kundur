# CONTEXT — andes-rl-kundur

**Purpose:** canonical glossary + architecture decisions for this repo.
**Last updated:** 2026-05-16

This file captures terms and decisions that are not derivable from the code
alone. For research-state facts (numerical results, round verdicts, claims),
see `memory/STATE.md`. For research-process rules, see `CLAUDE.md`.

---

## Glossary

### `paper path`
The end-to-end execution flow that produces the paper's headline numbers:
`train.py` (V4 env, SAC agent) → checkpoint → `eval_no_control.py` +
`eval_ddic.py` → JSON traces → `paper_grade_axes.py` → 6-axis geo-mean.
Any file outside this flow is research scaffolding, not load-bearing for
the paper.

### `V4 env`
`andes_vsg_env_v4.py`. The only env in active use. Paper-faithful:
H₀=100, Eq.14 strict, φ_d rescaled to 0.0056 (lower clamp from R18–R19).
V1/V2/V3 are historical ancestors; V4 will be made self-contained
(no inheritance) during the 2026-05-16 refactor.

### `Asset 4 / ranker`
`paper_grade_axes.py`. Paper-cited. Computes the 6-axis geometric mean
that produces the paper headline. Locked at v4.0 (post-r30/N1c fix).
**Logical changes require a new round + claim per `CLAUDE.md`.**
Physical relocation (path-only change) also requires a documenting
round — see R37 entry below.

### `HAWE`
Heterogeneous Actor Weighted Ensemble. Inference-time combination of
actor outputs from independently-trained checkpoints. No retraining.
Reproducible recovery of 99.3% of R21's lucky-basin score (0.439 vs 0.444).
Paper's Asset 5.

### `lucky basin`
A point in policy space that achieves anomalously high 6-axis score
(>0.40) but cannot be reached by re-running training from a different
seed. R21's V4_h50_s49 (0.444) is the canonical example. R23–R27's
22 ckpts all stalled ≤ 0.22.

### `multi-seed attractor`
The 6-axis score that SAC reliably converges to under V4 + paper-faithful
reward: ~0.137 ± 0.005, regardless of H₀ ∈ {40,70,100,200} or seed.
The "real" performance ceiling of SAC on this problem, modulo lucky basins.

### `claim` / `question` / `round` / `ledger`
Four-entity research memory system (active oracle since R39):
- **Claim** (`memory/claims/CLM-NNNN.md`): atomic, append-only, citable
  finding / decision / correction.
- **Question** (`memory/questions/Q-NNNN.md`): the forward-action unit.
  An open research uncertainty that a future round may address. Status
  is one of `open` / `in-flight` / `closed-positive` / `closed-negative`
  / `abandoned`. Closure cites a closing claim + round.
- **Round** (`memory/rounds/RNN/`): plan.md + verdict.md, bundles an
  experiment or infrastructure change. Verdict has 3 mandatory
  Q-sections (opened / closed / advanced).
- **STATE.md** (`memory/STATE.md`): auto-rendered 6-section active
  oracle (headlines / in-flight / open Qs / recently closed / latest
  round / stats). Reads claims + questions + rounds.
- `memory/handoffs/` is **out of schema** — informal session-end
  scratchpad, not read by `validate.py` or `render.py`. See
  `memory/handoffs/README.md`.
Full design rationale: `memory/rounds/R39/plan.md`.

### `WSL-only` (ANDES)
ANDES (the power system DAE simulator) is installed inside WSL only:
`/home/wya/andes_venv/bin/python`. Any Windows-side `andes` install is
a historical mis-install; do not use. Hard limit: ≤3 parallel ANDES
Python processes (R23 finding — TDS internal stiffness mis-judges
under contention).

### `paper-cited / paper-grade / paper-faithful`
Three different concepts:
- **paper-cited**: file or checkpoint is directly referenced from the
  paper's reproducibility appendix. Cannot be deleted/moved without
  new round. Currently: `paper_grade_axes.py`, contents of
  `results/whitelist/`.
- **paper-grade**: code that passes the 6-axis evaluation framework
  (Asset 4). Not the same as paper-cited.
- **paper-faithful**: matches the original paper's equations and
  parameter regime (H₀=100, Eq.14 strict). V4 env is paper-faithful;
  V1–V3 are not.

---

## Architecture decisions

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

---

## What this CONTEXT.md is not

- Not a status report — see `memory/STATE.md` for current numerical claims.
- Not a how-to — see `CLAUDE.md` for research-process rules and
  `scenarios/kundur/NOTES_ANDES.md` for ANDES engineering notes.
- Not a changelog — see git log + `memory/rounds/` for history.
- Not an audit trail — see `_legacy/CONTEXT.md` (frozen 2026-05-08).
