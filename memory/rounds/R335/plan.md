---
round: R335
state: aborted
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: pre-execution verifier expected a nonexistent inherited case field;
  no formal attempt or physical trajectory started
superseded_note: null
---
# R335 plan - four-channel physical disturbance package

## TL;DR

Answer Q-0086 with the smallest physical package that can represent all four
unknown-input coordinates used by the immutable deterministic model. Fit one
full cross-coupled physical-load-to-coordinate map on HS0 only, validate it on
untouched HS1 records, and stop before every controller or learning path. Do
not force a diagonal map or tune after holdout access.

## Authority and workload

- Direct question: `memory/questions/Q-0086.md`; parent finding `CLM-0880`
  identifies only the Bus14 active-load column.
- Scientific authority: immutable R316 order-10 realizations, immutable R329
  four-coordinate unknown-input object, R334 physical event and source-binding
  lessons, the selected manuscript `LINE.md`, and installed ANDES 2.0.0.
- Workload: `evidence`, because the round creates new physical trajectories,
  fits a prospectively declared map, reads an untouched validation split, and
  may dispose Q-0086. The conference title remains byte-for-byte unchanged.
- Research Supervisor route: one prospective package-adequacy question under
  project-native evidence governance; no literature, venue, controller, or
  manuscript-drafting branch.
- Ask Matt engineering work order: academic goal = make the four physical
  disturbance directions falsifiable; acceptance = valid full-rank package
  plus untouched-response agreement; blocker = R334 supports one channel and
  one waveform only; authority/write scope = this round plus the selected
  line's feed; verification = focused TDD, preflight, seal, single formal WSL
  execution, deterministic replay, publication audits, and repository tests;
  deliverable = one pure classifier, one reusable profile contract, one thin
  runner, and public-seam tests; return gate = the sealed package judgment.

## Methodology

Use one prospectively separated development-and-holdout study. Build the
reusable profile/event seam and pure classifier through focused red-green
slices, prove the create-only and holdout-order boundaries, run one HS0 canary,
then seal before any formal trajectory. Fit exactly one cross-coupled map from
the formal HS0 split, hash it before the HS1 split is admitted to analysis, and
classify once under the frozen outcome tree.

## Frozen physical bank

- Use the unchanged HS0 and HS1 operating-point settings: per-device M/D
  `177.5/88.75` and `202.5/101.25`, tie R/X scales `1.10/1.35`, initial SOC
  `0.41/0.51`, 0.2-s control periods, five TDS subdivisions per period, and 25
  recorded periods. HS0 is development/fit only; HS1 is untouched validation.
- Use exactly four existing PQ devices and their physical buses:
  `PQ_0@Bus7 -> node 0`, `PQ_1@Bus8 -> node 1`,
  `PQ_Bus14@Bus14 -> node 2`, and `PQ_Bus15@Bus15 -> node 3`.
- Freeze a common plant baseline in every record: active/reactive system-p.u.
  values `11.59/-0.735`, `15.75/-0.899`, `2.48/0.0`, and `0.05/0.0` in that
  device order. The last value creates a 5-MW nonnegative centre around the
  inherited zero Bus15 load; it is present in both zero and signed records.
- Use one matched zero record per point and, for each device, both signs of two
  R329-required waveforms. The system-base active-power profiles are
  `impulse=[0.05]` and `triangle=[0.02,0.04,0.05,0.04,0.02]`; negative records
  negate the profile. Restore the exact common baseline after the final active
  sample. Reactive power is unchanged. Total formal inventory is 34 records.
- Pre-setup absolute P/Q baselines and timed absolute P assignments are the
  only disturbance mechanism. Every M/D action and every requested,
  projected, internal, and achieved ESD1 power remains zero; Line_8 and G4
  remain in service. Record event callbacks, exact-event pre-row semantics,
  readback/restoration, replacement pointers, tie R/X, M/D, SOC, solver state,
  exact time grid, all four delivered frequency outputs, and inherited reward
  diagnostics.

## Frozen identification and validation

- Preserve the complete R316 state-space dynamics at each point. For each HS0
  physical channel, form the odd response `0.5*(r_positive-r_negative)` after
  subtracting the common zero record. Fit one four-coordinate column by a
  deterministic unregularized least-squares solve jointly over impulse and
  triangle records. Stack the four columns into one full cross-coupled map.
- The fit may retain every off-diagonal term. No diagonal projection, sign
  repair, scale correction, time shift, output selection, regularization,
  candidate grid, channel removal, threshold change, or post-holdout refit is
  permitted.
- Apply the one HS0-fitted map unchanged to all HS1 signed records using the
  HS1 R316 realization. HS1 may be opened only after the fit payload and its
  hash have been created. The classifier must verify this ordering and that no
  HS1 value enters fitting, selection, or package construction.

## Frozen gates and outcome tree

- Validity requires exact source/parent/round/question identity; the strict
  34-record inventory; one formal attempt; baseline/event readback and restore
  within `1e-12` system p.u.; exact event count and grid; constant-power status;
  unchanged topology and operating point; zero control/ESD1 paths; finite
  states; successful solver; algebraic residual at most `1e-6`; explicit
  development/holdout ordering; deterministic two-pass analysis; and declared
  reward computation/storage with no reward use for action, fitting, selection,
  training, classification, or claims.
- Each signed response must have signal-to-zero-drift energy ratio at least
  `10` and the required common-frequency sign. Each device/shape/point signed
  pair must have normalized L2 midpoint residual at most `0.10`; this supports
  approximate odd symmetry only for the registered pairs.
- Every HS0 fitted signed record and every untouched HS1 signed record must
  have total NRMSE at most `0.15` and global-peak-normalized maximum vector
  residual at most `0.20`.
- Transform fitted coordinate columns back to the four node injections. Each
  positive-load column must conserve active power within 20%, i.e. its node
  weights sum to `-1 +/- 0.20`. The four-column map must have rank four and
  smallest-to-largest singular-value ratio at least `0.10`. Off-diagonal
  coupling is measured and retained, not penalized.
- `INVALID-PHYSICAL-DISTURBANCE-PACKAGE`: any identity, source, inventory,
  execution, ordering, exclusion, replay, or numerical validity guard fails;
  interpret no scientific metric.
- `BLOCK`: execution is valid but any channel is unobservable, has wrong sign,
  fails development fit, fails untouched validation, or violates active-power
  conservation.
- `QUALIFY`: every individual channel and untouched-response rule passes, but
  the four-column map fails the frozen rank/conditioning coverage gate. This
  authorizes only the measured lower-dimensional subset and no closed loop.
- `ALLOW`: every individual, holdout, conservation, rank, and conditioning gate
  passes. This permits only a separately sealed deterministic physical-bridge
  question; it does not itself execute or validate a controller.

## Engineering seam and asset protection

- Public test seam: a pure `analyse_r335_disturbance_package` function accepts
  the sealed contract, formal records, parent realizations, a pre-holdout fit
  payload, and expected hashes, then returns the complete deterministic
  judgment. Tests observe only this interface and formal runner commands.
- Use vertical red-green slices for contract rejection, strict inventory,
  fit/holdout separation, retained cross-coupling, metric recomputation,
  conservation/rank classification, reward independence, source closure,
  create-only artifacts, and deterministic replay. Expected test values must
  come from worked synthetic records, not the implementation under test.
- Add only a new profile-contract module, R335 probe, thin adapter, and tests.
  Do not modify any R316-R334 scientific source, plan, result, feed, claim, or
  verdict. Seal every Python file under `src/andes_rl_kundur`, all R335 files,
  inherited helpers actually imported, `andes_scratch.py`, `artifact_io.py`,
  installed ANDES sources, and the executed Kundur case.
- Formal attempt, execution, pre-holdout fit, provenance, run manifest, and
  analysis are create-only and carry sidecars. The attempt marker precedes the
  first trajectory; interruption or formal failure forbids automatic retry.

## Verification and stopping conditions

- Before implementation, run round preflight. Then use focused red-green tests,
  lint, compilation, source-closure checks, a development-only physical canary,
  relevant regression tests, and two pre-seal reviews. The canary may use HS0
  only and is never a formal result.
- Run up to four records concurrently inside one split, each in its own
  simulator working directory with native numerical-library threads fixed to
  one. Preserve deterministic registered record order. The HS0 split, persisted
  fit, and HS1 split remain strictly serial; parallelism never crosses that
  boundary.
- After sealing, run the 34-record bank exactly once in WSL through
  `scripts/andes_scratch.py`. Create and hash the HS0 fit before reading HS1
  into formal analysis, replay twice deterministically, and do not amend any
  scientific contract after outcome access.
- Run independent evidence and power-system publication audits before claim
  registration. Use no EVAL: this round tests a deterministic physical input
  representation, not a learned or distributed policy, so EVAL cannot change
  the decision.
- Stop after the package judgment. No controller, closed loop, residual-
  headroom test, distributed runtime, reward design, agent, neural training,
  topology change, stability, safety, or title-result claim is authorized.

## Cross-references

- Direct question: `memory/questions/Q-0086.md`.
- Narrow physical parent: `memory/claims/CLM-0880.md`.
- Immutable dynamic-model parent: `memory/claims/CLM-0790.md`.
- Immutable estimator-development object: `memory/claims/CLM-0855.md`.
