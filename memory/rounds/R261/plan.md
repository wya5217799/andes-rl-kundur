---
round: R261
state: completed
opened: '2026-07-24'
closed: '2026-07-24'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: correctness
---
# R261 plan — WSL correctness audit: frequency calibration, failed traces, recurrent targets

**Status**: ACTIVE
**Opened**: 2026-07-24
**Type**: correctness (probe-first; real ANDES WSL + deterministic regressions)
**Driver**: Repository audit found three correctness risks. The PI confirmed
ANDES is available in WSL and authorized live validation plus code fixes, with
the existing round/claim/verdict research-record contract preserved.
**Parent**: CLM-0171 (known 60/50 Hz calibration defect), CLM-0014
(ranker decision requiring NaN/`tds_failed` guards), NOTE-0011/NOTE-0012
(recurrent burn-in/update design).

## TL;DR

Reproduce three risks independently before changing production code:

1. Real ANDES Kundur reports `GENROU.fn=60` while the project contract is 50 Hz.
2. `paper_path.run_scenario()` may drop `tds_failed` and return a scoreable
   partial trace.
3. TD3-LSTM Bellman targets may skip the current `(obs_t, action_t)` when
   advancing recurrent target state.

Only confirmed failures will be fixed. Existing V4 checkpoints and legacy
training semantics remain immutable; any frequency correction must be explicit
and must not silently reinterpret stored results.

## Snapshot at plan-time (oracle as of 2026-07-24)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0008 closed-negative @ R252, by CLM-0415 — Verify paper-metric ranking persists at 500-ep paper convergence horizon
- Q-0021 closed-positive @ R252, by CLM-0231 — V4 env TGOV1 governors u=1.0 in ANDES JSON but R08 Finding 3 says "completely ineffective" — which is true post-R37 refactor?
- Q-0005 closed-partial @ R186, by CLM-0350 — Why does TD3+LSTM seed 50 collapse while seeds 49/51 converge?

## Methodology

### Feedback loops

1. **WSL ANDES calibration loop**: Ubuntu 2,
   `/home/wya/andes_venv/bin/python`, `andes==2.0.0`; run
   `tests/test_v4_fn_consistency.py` against the real simulator and capture
   the observed model/environment nominal frequencies.
2. **Failed-trace loop**: fake environment returns `tds_failed=True` before
   the normal horizon. Assert that the canonical scenario record preserves
   failure state and that summary/ranker code refuses to score it.
3. **Recurrent-target loop**: deterministic tagged sequence with instrumented
   actor/critic inputs. Assert that the target state at transition `t` contains
   the history required for `Q_target(next_obs_t, next_action_t)`.

### Fix policy

- Preserve one variable per probe and add the failing regression before its fix.
- Propagate explicit validity metadata instead of inferring success from JSON
  shape or a non-empty trace.
- If recurrent alignment is confirmed, fix the shared implementation and every
  overriding variant found by usage search; do not claim historical checkpoints
  were trained with corrected targets.
- For 60/50 Hz, preserve legacy V4 training/observation semantics. Prefer an
  explicit physical-reporting seam or an opt-in corrected environment/config;
  do not silently overwrite the frozen V4 contract.

### Verification

- Targeted Windows unit tests for each fix.
- Full Windows `pytest`, Ruff, and compile checks.
- WSL real-ANDES calibration/regression test and the WSL-safe relevant test
  subset.
- `memory/tools/validate.py`, `dual_metric_lint.py`, and `render.py`.

This round is not a reward ablation and does not compare performance
baselines. `cum_rf` and 11-axis geo are therefore N/A as outcome thresholds;
any diagnostic trace instead reports validity, `tds_failed`, and `n_steps`.

## Pre-registered outcomes

| Probe result | Decision |
|---|---|
| Real ANDES `fn=60`, contract `fn=50` | CONFIRM CLM-0171 live; land only an explicit calibration/reporting fix that preserves legacy V4 semantics |
| Same frequency on both sides | REFUTE stale CLM-0171; remove `xfail` and record environment/version change |
| Early `tds_failed` record is scoreable | CONFIRM pipeline bug; propagate failure and hard-reject partial trace |
| Failure already survives and is rejected | REFUTE static-audit concern; test only |
| Tagged recurrent target skips current transition | CONFIRM algorithm bug; fix all affected recurrent agents and qualify historical LSTM results |
| Tagged sequence is temporally aligned | REFUTE concern; retain regression test and document why |

No performance/SOTA claim is allowed in this round: this is correctness
validation, not a training comparison.

## 资产保护契约

- Do not overwrite V1–V5 baselines, historical checkpoints, or existing result
  JSON.
- Do not change the default V4 reward, action range, disturbance distribution,
  or stored checkpoint schema without a backward-compatible loader.
- New diagnostic artifacts, if needed, go under `results/r261_*`.
- Historical claims remain current only within their recorded legacy semantics;
  corrections are linked rather than silently editing old evidence.
- Remove temporary `[DEBUG-*]` instrumentation before close.

## Cross-references

- R89 verdict / CLM-0171 — 60/50 Hz calibration defect and 17% scale impact.
- ADR-0002 — paper-strict versus paper-faithful-modified terminology.
- ADR-0004 / NOTE-0017 — new-subclass and explicit paper-deviation rules.
- NOTE-0011 / NOTE-0012 — original TD3-LSTM sequence design contract.
- CLM-0014 — ranker validity guards are a locked project decision.
- CLM-0250 — fresh scoring is authoritative; stale or partial summaries must
  not be treated as current evidence.
