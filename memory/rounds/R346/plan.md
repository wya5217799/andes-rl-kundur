---
round: R346
state: aborted
manuscript_line: decoupling-marl-model-first
opened: '2026-08-06'
closed: '2026-08-06'
supersedes_rounds: []
superseded_by_round: null
abort_reason: diagnostic-only objective completed and localized the R345 relaxation-stage
  numerical invalidity; no scientific result or claim/feed, Q-0091 remains open
superseded_note: null
---
# R346 plan - sealed localization of the R345 optimizer invalidity

**Opened**: 2026-08-06
**Driver**: Localize the sealed R345 numerical invalidity without retrying its
scientific analysis or exposing a residual-headroom conclusion.
**Parent**: CLM-0910; Q-0091; aborted R345

## TL;DR

Re-execute only the unchanged sixteen R345 oracle solves under a new
create-only diagnostic seal. Preserve one row per scenario even when a solve
is invalid, serialize only optimizer metadata, and stop after identifying the
failed numerical stage. Do not run the local reconstruction, statistics,
scientific classifier, ANDES, EVAL, or training. Q-0091 remains open in every
branch.

## Snapshot at plan-time (oracle as of 2026-08-06)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0091 [opened R344] Does the frozen deterministic bridge leave material, observable, and physically usable residual headroom before neural training?

## Recently Closed (last 3)

- Q-0090 closed-positive @ R344, by CLM-0910 — Can the fresh-qualified predictor support a deterministic physical bridge before any distributed or learning experiment?
- Q-0089 closed-positive @ R341, by CLM-0900 — Does the selected predictor preserve its registered waveform envelope on an untouched operating-point bank?
- Q-0087 closed-partial @ R339, by CLM-0890 — Which location-dependent input dynamics explain the upstream-load mismatch before any bridge repair?

## Methodology

**Lane**: evidence. The diagnostic reads the protected R344 outcome records and
therefore uses a prospective round even though it creates no new physical
trajectory and cannot change a claim or question disposition.

**Frozen failure chain**:

- R345 analysis seal SHA-256
  `47f1b287316f1475725a2c844f470016058ec06f5759d1d743829c74afbc04f4`;
- R345 attempt SHA-256
  `c93466515c681812164b4a3b3a7a1f79ba86592e0b5f83a15f5130368dcc908d`;
- R345 failure SHA-256
  `8a519fb736151ea793f18cff2b0d08de65d810dd8f49425104cd9f68de08c9a3`;
- unchanged R345 adapter SHA-256
  `97f598cfe63694c5028ee37a2acbb9b31ed94d8d6d1a36635082ff3745c935fb`;
- unchanged R345 probe SHA-256
  `e175020e592064361c40b63ad6cb5f44db430529abd033a6a47a128aebaa344a`;
- unchanged R345 tests SHA-256
  `8f8deccfb79af7a93039cc42402451c2d610cf7215d6b63ae416ceb7a0af5e84`.

The R346 adapter must verify the R345 seal and failure sidecars, then verify
the current adapter, probe, and reused source hashes against the immutable
R345 seal. The expected R344 inputs remain transitively bound by that seal.
The post-attempt R345 plan lifecycle edit is expected and is not used as an
executable source.

**Diagnostic execution**: recover the same exact sixteen cases and call the
unchanged R345 oracle worker once per case. Use at most sixteen single-thread
Windows workers in one process pool. A top-level wrapper catches per-case
exceptions so all sixteen identities return. Before any worker starts, write
one create-only attempt record. After completion, write one create-only
diagnostic and manifest with sidecars. Result rows retain only scenario, point,
channel, sign, worker/process time, optimizer validity, target feasibility,
solver status/message, iteration count, maximum constraint residual, maximum
target shortfall, and objective value. Endpoint values, edge sequences,
commands, state-of-charge paths, local fits, and scientific gates are omitted.

**Execution readiness**: RUN-READY. R344 measured valid whole-host operation up
to 32 single-thread processes; R346 has only sixteen ready jobs, no other
manuscript execution is reserved, and the identical R345 wave ended in about
four seconds. Expected completion is within the quick-run five-minute
envelope. Wait once for the terminal artifact; do not resize, tune, or retry.

**Engineering seam**: the public adapter exposes only `prepare` and
`diagnose`. Tests must freeze the source closure, create-only behavior,
sixteen-job inventory, metadata-only row projection, diagnostic classifier,
and absence of simulation, training, EVAL, local-reconstruction, and
scientific-classification commands.

## Gate

- `RELAXATION-INVALID`: at least one returned row has
  `optimizer_valid=false` and `target_feasible=false`, with no worker
  exception.
- `MINIMUM-NORM-INVALID`: no relaxation is invalid and at least one row has
  `optimizer_valid=false` and `target_feasible=true`.
- `WORKER-EXCEPTION`: at least one scenario raises before returning optimizer
  metadata.
- `NONREPRODUCIBLE-OPTIMIZER-INVALIDITY`: all sixteen unchanged oracle calls
  now report valid optimization.

Every branch sets `scientific_result_authorized=false`,
`question_disposition_authorized=false`, `residual_probe_authorized=false`,
`training_authorized=false`, `distributed_runtime_authorized=false`, and
`eval_authorized=false`. The only output is the numerical stage that a later
separately sealed repair must address. No branch retries or repairs R345.

## 资产保护契约

R341/R344/R345 seals, sources, attempts, failures, traces, manifests,
thresholds, and paper evidence remain byte-unchanged. Add only the R346 plan,
diagnostic adapter, targeted tests, diagnostic seal/results, and terminal
round record. Do not create a claim or feed from a numerical diagnostic, do
not close Q-0091, and do not push publicly.

## Cross-references

- CLM-0910
- Q-0091
- R345 `ANALYSIS-INVALID`
