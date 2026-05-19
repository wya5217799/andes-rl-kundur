---
round: R37
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R37 plan — Code-architecture refactor + silent V2 inheritance bug audit

**Date**: 2026-05-16
**Type**: refactor + audit
**Trigger**: User goal pivoted from "write paper" to "develop better
agents". Existing codebase is a research-process geological layering,
not a maintainable workbench. /grill-with-docs session produced 14
architecture decisions (see `CONTEXT.md` § AD-01..AD-14).

## Goals

1. Collapse the V1→V2→V3→V4 env inheritance chain into a single
   self-contained `AndesMultiVSGEnvV4`.
2. Adopt the standard Python src-layout
   (`src/andes_rl_kundur/...`) with the package installable via
   `pip install -e .`.
3. Flatten entry-point scripts to top-level `scripts/`; archive
   round-specific drivers under `scripts/_archive/`.
4. Move frozen products (paper, dissertation) to `artifacts/`.
5. Surface any hidden bugs that the inheritance chain was masking.
6. Preserve **bit-identical** physics: `eval_no_control` JSON output
   must match the PRE_REFACTOR baseline byte-for-byte.

## Method

Two-phase execution (see `CONTEXT.md` § AD-12).

**Phase 1 — logical cleanup (in-place)**:
- AD-06 fix `utils/monitor.py` (broken `from utils.training_callback`)
- AD-05 strip `config.py` V1-era dead parameters
- AD-04 consolidate `SCENARIOS` import to single source of truth
- AD-02 archive non-paper-path scripts
- AD-01 merge V4 inheritance chain into self-contained class
- AD-03 rewrite `train.py`, drop monkey-patch shim and warmstart fork
- AD-07 add `BaseAgent` Protocol

**Phase 2 — physical reorg**:
- AD-09 migrate to `src/andes_rl_kundur/`
- AD-10 move `paper/` and `dissertation/` under `artifacts/`
- Add `pyproject.toml`

## Verification

Before refactor: snapshot
`results/research_loop/eval_v4_baseline_PRE_REFACTOR/no_control_load_step_{1,2}.json`
on the V1→V2→V3→V4 inheritance chain.

After each phase: re-run `scripts/eval_no_control.py` and diff. Tolerance
**1e-9** (bit-identical, or floating-point equivalent).

Sediment the comparison into `tests/test_v4_env_regression.py`.

## Exit criteria

- `pytest tests/` GREEN
- `scripts/eval_no_control.py` produces JSON byte-identical to baseline
- Top-level directory layout matches `CONTEXT.md` AD-09/AD-10
- All paper-cited file relocations documented as new claims
