# R474 code review A — diff/data-flow audit

**Reviewer**: independent subagent (diff/data-flow focus)
**Round**: R474 (same-time-permutation placebo, 60 P-cell retrain)
**Commits reviewed**: 8cc2ccb (initial), 1712eeb (wiring), 04b1bd0 (review fixes), 6b40175 (closeout)

**Decision**: PASS (after fixes)

## Round 1 (FAIL) — findings and fixes

- **BLOCKER-1** import dropped `.sha256` sidecars of donor `base_state.pt`/`manifest.json`
  -> every downstream `_read_hashed_json`/`formal_manifest` would crash.
  FIXED: import now hardlinks the sidecars with missing-sidecar `RuntimeError` and
  existing-target `FileExistsError` guards; pinned by `test_import_copies_donor_sidecars`.
- **BLOCKER-2** routing check assumed a slot convention the env does not implement
  (`COMM_ADJ` order asymmetric; per-slot pool equality unsatisfiable).
  FIXED: `routing_check` uses the real `COMM_ADJ = {0:(1,3),1:(0,2),2:(1,3),3:(2,0)}`
  with per-feature-channel (d_omega block cols 3,4; omega_dot block cols 5,6) source-pool
  equality and realized-slot identity vs the true per-column wiring; operationalization
  recorded in plan.md.
- **MAJOR-1** seal sources omitted the structural parents (reward/env/contract chain).
  FIXED: prepare() now seals r451/r438/r431/r430/r429/r428 runners + base_env.py +
  v4_config.py.
- **MINOR-1** `fresh_eval_shards` 10 -> 20 (matches EVAL_SHARDS entries). FIXED.

## Re-review (PASS) — remaining MINORs (non-blocking, recorded)

- Inherited aggregate classification scope still reads "frozen R470 learner/bank/projector
  only" ("bank" is stale for R474; wording-only, recorded in feed at close-out).
- Fresh train manifests record `base_state_path` pointing at the ancestor round's donor
  path (valid: same inode as the hardlinked R474 copy).
- Phase order (reuse -> rehearse -> route -> prepare -> import) is not enforced by `_main`
  (orchestrated by the detached pipeline script).

## Invariants vs R470/R473 (all VERIFIED)

learner, reward, optimizer, replay, schedule, RNG stream, environment, endpoints,
thresholds, and the aggregate protocol are byte-identical; the only diffs in
train/eval are donor-read removal, the new `source_rows` signature, the
`p_source_semantics` manifest field, and `donor_episode: None`.
