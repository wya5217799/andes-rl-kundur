# R46 plan — Architectural deepening (4 candidates, 3 executed + 1 deferred)

**Date**: 2026-05-16
**Type**: infrastructure (refactor, no experiment)
**Status**: COMPLETE — see `verdict.md`
**Estimated wall**: ~1.5 h actual

## Trigger

`/improve-codebase-architecture` second pass after R42. R42 already
landed 4 deepening commits (C1 paper_path / C2 checkpoint_loader / C3
_load_entities / C4 monitor checks) and **grilling-rejected** the SAC
mixin split. Explore agent + Grep verification surfaced 4 remaining
open candidates:

1. `eval_all_seeds.py` reverse-imports `eval_ddic`'s back-compat alias
   layer (shallow wrappers; pre-package-layout artefact)
2. 6 top-level `_r{38,40,41,42}_score_*.py` violate AD-02 (round-driver
   scratch sitting next to paper-path entry points)
3. `AndesBaseEnv` only has one live adapter (V4); NE39 / REGCA1 dead
   in `_legacy/`. Per LANGUAGE.md "one adapter = hypothetical seam"
   the abstraction is degenerate
4. `probes/andes_common/verdict.py` collides with the round ledger
   `memory/rounds/RNN/verdict.md` first-class entity

## Phase split

**Phase A — zero/low risk (executed)**:
- Commit 1 (C2): archive the 6 scratch scripts
- Commit 2 (C1): drop eval back-compat aliases; `eval_all_seeds.py`
  imports the package directly
- Commit 3 (C4): rename `verdict.py` → `probe_classifier.py` with
  class/function renames + `__init__.py` re-export update

**Phase B — medium risk (DEFERRED)**:
- Quantification done (V4 inherits 12/14 non-abstract base methods =
  86 %, over the 70 % plan gate)
- **Execution deferred** because AD-11 `test_v4_env_regression.py`
  1e-9 bit-identical regression runs ONLY in WSL (`andes` import) and
  this session lives on the Windows host. Refactoring a paper-cited
  path without being able to run the regression test = violates the
  plan's verification gate
- Q-0004 opened to hand off the GO-recommendation to a WSL-capable
  session

## Round-number note

Commit messages tag these as "R45 commit 1/2/3" — that label was
mid-flight before the conflict with the user's R45 plan (Q-0001
escalation + s52 reproducibility + SAC long, 70-min experimental
round) was discovered. The actual round number is **R46**. Commit
hashes:

- 5d86705 chore(scripts): archive 6 round-driver score scripts
- 34f5d9f refactor(scripts): drop eval_ddic/eval_ensemble back-compat aliases
- 4777ecb refactor(probes): rename verdict.py -> probe_classifier.py

Full plan body lives at `.claude/plans/distributed-booping-clover.md`
(harness plan file).

## Out of scope

- AndesBaseEnv absorption into V4 (Phase B candidate ③): execution
  deferred pending WSL verification — see Q-0004
- SAC mixin split: stays rejected per R42 grilling (Explore agent's
  deletion test failed)
- V4Config (`env/andes/v4_config.py`): immutable load-bearing seam
  for R41/R43 `action_penalty_mode` switching (physical / normalized),
  CLM-0042/0047/0048 references; NOT touched
- `artifacts/dissertation/main.tex` line 1217 still references
  `\verb|VerdictRule|`: dissertation is frozen artefact, fix at next
  re-compile
- `memory/handoffs/2026-05-07_handoff_v13.md`: out-of-schema
  scratchpad, not touched
- _legacy/* paths and CLM-* historical claims: untouched
