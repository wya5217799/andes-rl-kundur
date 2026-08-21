# Coordination note — two live sessions, one harness (2026-08-19 ~23:50)

Both conversations share this workspace and WSL. Division of labor to
avoid duplicate rounds/claims (each side verifies the other's close-out):

- Session A (archived conversation, still live): owns **R436** fix loop +
  close-out. It found a third defect (soc/previous_power not tracked across
  steps in eval paths) and is preparing a third eval pass. Do not touch
  scripts/run_r436_energy_residual_sac.py, results/research_loop/
  r436_energy_residual_sac/, or R436 claim/feed until its close-out lands.
- Session B (this session): owns **R439, R440, R438** close-outs + repo
  infra (session_context budget, contract paths, LINE budget, tmp/andes
  cleanup). R436 execution amendment already written at
  memory/rounds/R436/execution_amendment_20260819.md (covers defect 1+2;
  Session A must extend it for defect 3 before closing).

In-flight processes for budget accounting:
- R438 training: 10 shard workers + 1 driver (launched 22:14, ETA ~01:30+).
- R439 eval: 4 shard workers + 1 driver (Session B, launching ~23:55).
- R440 eval: 10 shard workers + 1 driver (Session B, queued until R438
  training completes to stay inside 32-core / 27 GiB budget).
- R436 eval pass 3: Session A (8-10 workers, expected shortly after its
  verification). Session A's re-launch budget should declare R438+R439
  workers as other_reserved_processes.

Rules reminder: claim ids only via reserve_claim.py (atomic); create-only
outputs mean whoever writes first wins — check FileExistsError instead of
double-running.
