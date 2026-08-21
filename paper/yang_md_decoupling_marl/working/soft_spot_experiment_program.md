# Soft-spot experiment program — overnight mission file (R411+)

This file is the mission contract for the follow-up long task. The shared
rules live elsewhere and are followed, not restated: round lifecycle,
capacity ladder, and ledger rules are `CLAUDE.md` +
`skills/kundur-round/SKILL.md`; the C-class verdict evidence is
`working/deep_research_c_class_necessity.md`; the venue-ROI rationale is
`working/deep_research_experiment_value.md`.

Working words (repeat the token, not the meaning):

- **frozen-first**: plan carries the pre-registered decision tree; every
  protocol number is frozen before execution.
- **one factor**: each round changes exactly one scientific factor versus
  its registered predecessor; concurrency is the only free knob.
- **round discipline**: reserve -> plan -> preflight -> capacity ->
  rehearsal -> seal -> execute -> feed -> claim -> publication gate ->
  verdict -> close.
- **quiet progress**: heartbeat at milestones only (reserved, sealed,
  classified, closed).
- **budget-frozen**: the seal's process budget is immutable once sealed.
- **saturate-or-skip**: estimate serial wall time first; minutes -> run the
  plain seam and move on; hours -> measure the capacity ladder first, build
  the one shared shard driver, then run at the measured rung.

## Mission contract

- **Outcome**: close the default deck below and stop; the override deck
  runs only on an explicit owner order.
- **Authority**: `working/route_owner_decision_soft_spot_program_2026-08-16.md`;
  LINE.md `stop_when` already permits program rounds.
- **Terminal condition**: every started round closed with
  `repo_health.py check --no-baseline`, `validate.py`, `render.py`, and the
  full pytest suite green — or a pause condition reached.
- **Pause-for-user conditions** (stop and ask):
  1. an item's pre-registered decision rule lands on its pause branch;
  2. a round aborts after seal (abort is terminal for that round);
  3. capacity evidence rejects the sealed worker rung;
  4. a result would need to enter the manuscript after the 2026-09-07
     final-paper freeze — route it to the extension and say so.
- **Deadline boundary**: submission work outranks the program. After
  2026-08-28 registration, only results whose full lifecycle completes
  before the 9/7 freeze may enter the paper.
- **Gates are reminders, not rulers**: every hard gate pairs with a pause
  checkpoint where the owner decides; adjust gate strength through the
  calibration log, never improvise mid-round.
- **Hardware authority (owner-granted, 2026-08-16)**: the whole host is
  available to this mission. The round's sealed budget is the capacity
  ladder's selected rung (rungs 1/2/4/8/12/16; 5% marginal-throughput rule
  + half-memory rule) — evidence decides, not a fixed 4-worker habit.
  Freeze the budget only after the ladder runs (budget-frozen).
  `other_reserved_processes` stays 0; `native_threads_per_process` stays 1.

## Creative-mode policy (owner-granted, 2026-08-16)

In creative mode the owner stays out of the loop; the single objective is
a stronger paper.

- **Operational freedom**: choose order, methods, extra experiments, and
  the override deck without per-item orders; full hardware per the
  parallelism gate. The base argument logic is fixed; supplementary
  evidence only strengthens it.
- **No interruption**: the four pause conditions degrade to auto-continue —
  apply the pre-registered branch, record the decision in the calibration
  log, keep going. A flipped canary still updates the manuscript per the
  evidence.
- **The floor**: round discipline, green validators, and re-checkable
  numbers remain — they produce the paper's credibility, which is the one
  objective. Adjust them only through the calibration log.
- **Deadline boundary unchanged**: results enter the paper only when their
  full lifecycle completes before the freeze; the rest feeds the extension.

## Pre-mission checks (all four true before reserving any round)

- [x] `session_context.py --json --line yang-md-decoupling-marl` reports no
      active round and `mode` is not `manuscript-refresh`.
- [x] WSL live: `/home/wya/andes_venv/bin/python -c "import andes"` exits 0.
- [x] R410 result root exists and stays read-only.
- [x] `scripts/run_r410_message_repair.py` read as the execution template.

## Parallelism gate (apply per item, before writing any shard code)

saturate-or-skip decides, anchored by R410 measurements: one eval record
costs ~12 s serial; one training run costs ~2.4 h serial.

1. Estimate the item's serial wall: records x ~12 s (eval items) or runs x
   ~2.4 h (training items).
2. Serial estimate <= 20 min: run the existing single-process seam (the
   R408/R409 harness or the R410 runner's eval seam) exactly as-is; write
   no parallel code. Completion criterion unchanged.
3. Serial estimate > 20 min, or any training item: invest first, then run:
   a. measure the capacity ladder at rungs 1/2/4/8/12/16 with the item's
      representative tasks; the 5% marginal-throughput rule + the
      owner-authorized headroom memory rule select the rung (900 MB
      live-training RSS floor per worker; projected concurrent RSS must
      not exceed WSL MemAvailable minus a fixed 4 GiB OS headroom —
      owner decision 2026-08-17, replaces the half-of-available rule);
   b. write the shared eval-shard driver ONCE (parameterized runner module
      + shard list; generalize the R410 eval-shard pattern), reused
      unchanged by A2/A3/A4 — never per item;
   c. seal the ladder-selected budget, then launch at that rung; overlap
      the last training run with eval shards as R410 did.
4. Expected shape: A1 (~720 records, ~2.4 h serial) triggers the long
   branch and the driver; A2/A3/A4 reuse it. Eval records scale with
   workers nearly linearly (independent ANDES processes); training scales
   worse (shared host contention) — which is exactly why the ladder
   measures instead of assuming.

## Default deck (run in order, then stop)

Eval-only; each item = one evidence round; shard-parallelize inside each
round's sealed budget (R410 eval-shard pattern).

### A1. Probe-amplitude ladder — DONE (R411, CLM-1220, 2026-08-17)
- **Why**: perturbation-amplitude checks are standard small-signal practice
  (impedance/perturbation studies sweep injected amplitudes); the signed-pair
  normalization assumes an odd response and one amplitude grid tests that
  assumption.
- **Frozen protocol**: amplitude factors 0.5/0.7/1.0/1.3/1.5 on the
  registered probe magnitudes; re-evaluate the R410 frozen checkpoints
  (9 arm-seeds + deterministic) read-only through a new eval adapter that
  scales `probe_magnitude` per record; same estimators, guards, create-only.
- **Completion criterion**: one hashed JSON with per-amplitude endpoint
  ratios and guard status for every arm-seed-profile block.
- **Cost**: ~720 records ≈ 40–60 min at 4 shards. Pause branch: none.

### A2. Topology-variant robustness of the constructive controller — DONE (R413 successor of aborted R412, CLM-1225, 2026-08-17)
- **Why**: N-1/contingency robustness is the standard evaluation axis for
  grid-forming devices (IEEE contingency planning works).
- **Frozen protocol**: freeze a variant bank (line outages + tie-impedance
  changes, N ≈ 12) on the modified Kundur; outages only through
  `apply_line_outage()` / ANDES `Model.set`; every paper-facing EIG passes
  the CLM-0665 hard gate (`TDS.test_ok`, `exit_code=0`, init residuals,
  finite spectrum, positive-real guard). Re-evaluate the frozen K=3.5
  bandpass + references with R409 thresholds/guards.
- **Completion criterion**: per-variant pass/fail table in a hashed JSON
  with every EIG gate value recorded.
- **Cost**: ~1–2 h. Pause branch: none — a failing variant is recorded as a
  fail; stop only if the base case itself is unsound.

### A4. Energy-port extra unseen banks — DONE (R415 successor of aborted R414, CLM-1230, 2026-08-17)
- **Why**: test-set diversity for the one constructive result (today it has
  one disclosed dev bank + one one-use unseen bank).
- **Frozen protocol**: freeze a new unseen condition bank (probe /
  disturbance / M-D parameter perturbations, ~30–60 records) for the frozen
  K=3.5 controller; reuse the R408/R409 harness; create-only.
- **Completion criterion**: `r_d`, `r_cross` against the frozen thresholds
  on every record in a hashed JSON.
- **Cost**: ~1–2 h. Pause branch: none.

### A3 (optional, only if time remains). Deterministic-law family expansion + oracle — DONE (R416, CLM-1235, 2026-08-17)
- **Why**: strengthens the "no measured headroom" claim beyond the nine
  registered laws.
- **Frozen protocol**: extended candidate set (densified gain grid + one
  PI-type law, ~20 total); development selection + outcome-seeing oracle on
  the same evaluation profiles, same guards.
- **Completion criterion**: oracle headroom delta in a hashed JSON with all
  guard statuses.
- **Cost**: ~1 h. Pause branch: none.

## Override deck (owner order only; post-submission by default)

Training items; pre-seal capacity ladder (rungs 1/2/4/8/12/16, the
owner-authorized headroom memory rule) with the ladder-selected budget;
overlap the final training run with evaluation shards exactly as R410
did.  **Mission status (2026-08-17): B1 DONE via the feedback loop
(R419, CLM-1245; negative objective-repair extension R420, CLM-1250);
B2 / B3 / C1-SAC remain queued (B3 next, C1-SAC owner-order only).**

### B1. Slew-state-aware fully repaired bundle — DONE (R419, CLM-1245, 2026-08-17; negative objective-repair extension R420, CLM-1250)
- **Why**: actuator saturation/slew interaction is a recognized RL-control
  failure class (RL + actuator-saturation literature) and the audit's
  leading hypothesis for the guard failures: the bundle executes a stateful
  slew projection while the actor state omits the previous executed action
  and targets optimize unslewed outputs.
- **Frozen protocol**: one factor = add the previous executed action to the
  actor observation and align target-action semantics; keep the R410 mask
  repair; 3 arms x seeds 401/402/403, R402-identical hyperparameters; new
  learner class + runner + seal; reference fix
  `working/r402_causal_validation_final_bundle/source/reference_fixes/slew_aware_td3_interface.py`
  is a design aid only.
- **Pre-registered decision rule**: guards + endpoints vs R410 and vs the
  deterministic reference, plus the message contrast under the repaired
  bundle. Pause branch: any arm passes the physical guards or the
  classification flips — stop at the claim gate and ask the owner.
- **Cost**: 9 runs ≈ 7 h at 4 workers + eval.

### B3. Diagnostics-instrumented rerun
- **Why**: complete training curves are a reproducibility norm (Henderson et
  al., *Deep RL that Matters*, AAAI 2018); today only final-20
  costs/multipliers are retained, so no failure mechanism can be identified.
- **Frozen protocol**: log-only runner around the unchanged R410 learner
  (logging never consumes the RNG stream — bit-comparable to R410); rerun
  the repaired no-message and message arms at 3 seeds; persist critic/actor
  losses, gradient norms, Bellman residuals, replay coverage.
- **Completion criterion**: per-run diagnostic CSVs + hashed summary JSON;
  a bounded mechanism-hypothesis note in the feed (hypotheses, not causes).
- **Cost**: 6 runs ≈ 5 h.

### B2. Seed-count extension
- **Why**: three seeds sit below the power needed for statistical comparison
  statements (Colas et al., arXiv:1806.08295; arXiv:1904.06979).
- **Frozen protocol**: 5 seeds per arm for the R410-repaired bundle; reuse
  401/402/403 where bit-repro holds, train 404/405 fresh; same budget and
  guards.
- **Completion criterion**: 5-seed median/spread table in a hashed JSON;
  updated canary verdict per the frozen tree.
- **Cost**: 6 extra runs ≈ 5 h. Pause branch: none (reporting-only).

### C1-SAC. Exact Yang-2023 SAC reproduction
- **Trigger**: explicit owner order only. **Why**: the manuscript positions
  against [1] (Yang et al., TPWRS 2022, MADRL-SAC); an exact reproduction
  turns the "engineering baseline" caveat into a direct comparison. This is
  a targeted single experiment, never an algorithm sweep.
- **Frozen protocol**: matched bundle (same profiles, seeds, budgets,
  guards) with the SAC interface of [1] reproduced exactly; new learner +
  runner + seal.
- **Cost**: ≈ one B1-scale night. Pause branch: same as B1.

## Post-mission closeout

- [x] Every started round closed: feed_check, validate, render, pytest,
      repo_health all green (R411 completed, R413 completed, R415
      completed, R416 completed; R412/R414 aborted on sealed-runner
      defects with successors, per the round rules).
- [x] Mark each item done / paused / skipped in the section header.
- [x] Gate calibration: one line per item in
      `working/gate_calibration_log.md` — which gate ran too hard / too
      soft / right, plus the concrete adjustment (codify per SKILL.md j2).
- [x] Deliver the 给 PI 的话 of the last closed round verbatim, nothing
      else appended.
