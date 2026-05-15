# R37 verdict — Refactor complete; silent V2 inheritance bug surfaced

**Date**: 2026-05-16
**Branch**: `refactor/clean-arch-2026-05-16`
**Wall**: ~6 h (planning + execution)
**Status**: **COMPLETE**. All 14 architecture decisions implemented.
Regression test green at 1e-9; 0 per-step differences across both
LS1 + LS2 traces.

---

## TL;DR

> 14 architecture decisions executed across two phases. Pre/post
> bit-identical: 0 difference across 150 steps × 5 trace keys × 2
> scenarios. **One silent bug surfaced**: `ZERO_G4_INERTIA` was
> inherited as `True` from V2 into V4 through the class chain, while
> V4's own docstring claimed "G4 inertia preserved". Every paper number
> (R21 = 0.444, HAWE = 0.439, no-control = 0.104) was therefore
> computed with G4 zeroed. Pinned `True` explicitly in the new self-
> contained V4 to preserve reproducibility; new CLM-0040 records the
> discrepancy and what re-running with G4 preserved would imply.

---

## What changed

### Logical cleanup (Phase 1)

| AD | Change | Commit |
|----|--------|--------|
| AD-06 | Fixed `utils/monitor.py`: dropped broken import to non-existent `utils.training_callback`; deleted unused `agents/ma_manager.py` | 30d767f |
| AD-05 | Stripped ~80 lines of V1-era dead params from `config.py`; kept only 8 SAC hyperparameters | 1c22317 |
| AD-04 | Consolidated `SCENARIOS` to `probes/andes_common/paper_constants` (was duplicated in 6 eval scripts) | ee0b7cc |
| AD-02 | Archived 18 round / experiment / utility scripts under `scripts/_archive/round_scripts/` | c948700 |
| AD-01 | V4 env self-contained; V1/V2/V3 + NE39 envs moved to `_legacy/env/andes/`. **G4 inertia bug surfaced** | e0bc8b8 |
| AD-03+07 | Clean `scripts/train.py` (replaces 3 old shims); `BaseAgent` Protocol | 4abadea |

### Physical reorg (Phase 2)

| AD | Change | Commit |
|----|--------|--------|
| AD-09 | All library code under `src/andes_rl_kundur/` with full namespace prefix on imports | 2630c78 |
| AD-10 | `paper/` and `dissertation/` under `artifacts/` | (same) |
| — | Added `pyproject.toml` with src-layout config + ruff/black/pytest sections | (same) |
| — | `scenarios/kundur/NOTES_ANDES.md` → `docs/eng-notes/NOTES_ANDES.md` | (same) |

### New file: regression test

`tests/test_v4_env_regression.py` runs a ~90 s end-to-end no-control
roll-out and compares the first step's `freq_hz` against the
PRE_REFACTOR baseline at 1e-9 absolute tolerance.

### Documentation refresh

- `CONTEXT.md` — 14 ADs documented with glossary
- `docs/adr/0001-src-layout.md` — long-form rationale for AD-09
- `CLAUDE.md` / `README.md` — refreshed for new layout
- `_legacy/env/andes/README.md`, `_legacy/scenarios/kundur/README.md`,
  `scripts/_archive/round_scripts/README.md` — explain what each
  frozen subtree contains

---

## The silent V2 inheritance bug (G4 inertia)

While merging V1→V2→V3→V4 into one class, the regression test caught
a ~1e-3 Hz drift in the t=0 post-disturbance frequency. Root cause:

- V1 declared `ZERO_G4_INERTIA = False` (wind-farm proxy off)
- V2 silently overrode to `ZERO_G4_INERTIA = True` (wind-farm proxy on)
- V3 + V4 did not re-declare, so MRO returned `True`
- V4's module docstring read "G4 inertia preserved (V1 default change,
  `ZERO_G4_INERTIA=False`)" — directly contradicted by runtime behavior

Every paper number — R21 = 0.444, HAWE w9802 = 0.439, multi-seed
attractor 0.137, no-control 0.104 — was computed with G4 zeroed (not
the documented paper-faithful Kundur 4-SG baseline).

Decision: **pin `ZERO_G4_INERTIA = True` in the new self-contained V4**
to preserve bit-identical reproducibility of those headline numbers.
The discrepancy is documented in:
- The class-level comment in `src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py`
- The module docstring
- `CLM-0040` (this round)

A future round can investigate whether the R15 forensic baseline ("G4
preserved drops max_df 26 %") would, under V4's H₀=100s + φ rescale +
paper-faithful action range + IEEEG1+EXST1 DAE-active configuration,
change the headline ranking. That experiment is **not** part of R37.

---

## Verification

```
$ /home/wya/andes_venv/bin/python -m pytest tests/
============================= test session starts ==============================
tests/test_v4_env_regression.py::test_first_step_freq_hz_matches_baseline[load_step_1] PASSED
tests/test_v4_env_regression.py::test_first_step_freq_hz_matches_baseline[load_step_2] PASSED
========================= 2 passed in 92.87s (0:01:32) =========================
```

Bit-identical JSON diff (custom helper, post Phase 2):

```
load_step_1: cum_rf_total match=True, max_df match=True, per-step diffs across 5 keys x 150 steps = 0
load_step_2: cum_rf_total match=True, max_df match=True, per-step diffs across 5 keys x 150 steps = 0
```

---

## New claims this round

- `CLM-0040` — V4 silent V2 inheritance bug (G4 inertia, paper-grade
  reproducibility preserved by pinning `True` explicitly)
- `CLM-0041` — paper-cited `paper_grade_axes.py` relocation
  `evaluation/` → `src/andes_rl_kundur/evaluation/`, byte-identical
  logic (zero `git diff` on the file's content; only path changes)
- `CLM-0042` — R37 deepening pass extending the 14-AD baseline

## Deepening pass — 5 candidates + reviewer fixes

The 14-AD refactor produced the structural baseline. A follow-up
`/improve-codebase-architecture` review identified 7 deepening
candidates; 5 were implemented in this round (Cand 5 contextmanager
was absorbed by Cand 1, Cand 6 paper_grade_axes tests already shipped
in the prior commit `429ef48`).

| Cand | Commit | Module | Tests |
|------|--------|--------|-------|
| 7 | `13cf76a` | `probes.andes_common.LSFigureBenchmark` (rename) | +1 |
| 1 | `994bb2d` | `env.andes.v4_config.V4Config` (injection seam) | +5 |
| 4 | `95ee4c4` | `agents.episode_result.EpisodeResult` (typed roll-out) | +3 |
| 3 | `e4d757d` | `agents.sac_base._SACBase` (shared concrete base) | +4 |
| 2 | `dbed45d` | `utils.checks.Check` Protocol + `register_check()` | +3 |

Two independent reviewer agents (code-reviewer, security-reviewer)
ran on the final branch. Findings landed in `6aae9a8`:
- CRITICAL: `deviation_summary()` reported `"preserved"` even when
  ZERO_G4_INERTIA=True — same silent-disagreement class as CLM-0040.
  Fixed; regression test locks it.
- HIGH (security): `torch.load(weights_only=False)` in the warmstart
  path could execute arbitrary code from an adversarial checkpoint.
  Changed to `weights_only=True`.
- HIGH (robustness): `V4Config.__dict__` on a frozen dataclass —
  replaced by `dataclasses.replace()` and `dataclasses.asdict()`.

Final state: **21 tests pass**, `eval_no_control` still bit-identical
(max_df 0.189 / 0.168) to the PRE_REFACTOR baseline.

---

## Cross-references

- `CONTEXT.md` (root) — 14 AD log
- `docs/adr/0001-src-layout.md` — src-layout decision long-form
- `tests/test_v4_env_regression.py` — regression sediment
- `_legacy/env/andes/README.md` — what V1/V2/V3 + NE39 envs were
- `_legacy/scenarios/kundur/README.md` — what the three old train shims were


## Questions opened (this round)
- none (retrofit — this verdict pre-dates the Q entity introduced in R39)

## Questions closed (this round)
- none (retrofit)

## Questions advanced (this round, status unchanged)
- none (retrofit)
