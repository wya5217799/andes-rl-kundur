---
round: R474
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-23'
closed: '2026-08-23'
supersedes_rounds: []
superseded_by_round: null
abort_reason: owner-ordered shutdown after external deep review proved the pi(i)=(i+2)
  diagonal-copy P fails guardrail per-slot pool equality; batch mixing 2/3; materiality
  test mismatch; successor R475 implements row-permuted P + all-fresh 2x2 + direct
  materiality Holm
superseded_note: null
---
# R474 plan — U2 successor with same-time-permutation placebo (guardrails §A)

**Opened**: 2026-08-23
**Driver**: Owner decision after R473 close: run the corrected message-source
experiment (option 2 — retrain only the P-source cells) with the placebo
redesigned as a same-time permutation of the authentic source pool per the
2026-08-22 three-package intake (guardrails §A), and subject the experiment
code to strict review before any formal execution.
**Parent**: CLM-1475/R473 (U2 supported under the old exogenous-donor P);
R472 owner-ordered shutdown; guardrails
`skills/kundur-round/references/experiment-design-guardrails.md` §A/E;
R470 sealed aggregate protocol.

## TL;DR

R474 retrains exactly the 60 P-source cells (actor=P or critic=P) with the
placebo redefined as a same-time device permutation of the authentic
observation pool (π(i)=(i+2) mod 4, the unique non-neighbour permutation on the
4-device ring), reuses the 48 N/0 cells and all 6 base states from R473 via
NTFS hardlinks, passes a falsification-first routing check before any training,
then runs the byte-identical R470 aggregate. A mandated two-reviewer code gate
(runner diff vs R473 + guardrail §A.2 implementation audit) must pass before
rehearsal/seal. Wording keeps the total-algorithm-effect boundary (no pure
semantic information claim, no universal intrinsic claim).

## Snapshot at plan-time (oracle as of 2026-08-23)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Methodology

### Frozen evidence identity

- Work class: **evidence**; create-only root
  `results/research_loop/r474_u2_source_factorial`.
- Design is R470/R473 byte-for-byte except the P-source semantics: 18 cells by
  seeds 401..406, 43,200 physical training steps, development/evaluation
  scenario bank, half/final checkpoints, full curves, endpoints, 10% log
  materiality, exact sign-flip randomization inversion, paired bootstrap CI95,
  Holm alpha .05 — all inherited unchanged.
- **The single scientific change**: P rows are built from the SAME-TIME joint
  observation by the device permutation π(i)=(i+2) mod 4 (the unique
  permutation with no fixed point and no true-neighbour source on the 4-device
  ring), channel-respecting per the env layout (cols 3,4 = d_omega block;
  cols 5,6 = omega_dot block):
  `rows[i,3]=rows[i,4]=joint[(i+2)%4,1]` and `rows[i,5]=rows[i,6]=joint[(i+2)%4,2]`.
  N reads the same contemporaneous state pool unpermuted; 0 zeroes slots 3:7.
  No pre-recorded donor trajectories are generated or consumed anywhere.
- U3 executed-action semantics, network, optimizer, replay/update count,
  reward, action limits, environment, and seeds unchanged.

### Falsification-first routing check (guardrails §A.2, BLOCKING)

- Before any training shard: on real ANDES joint observations
  (rehearsal three-step + a pre-train standalone check), verify per feature
  channel (d_omega block = cols 3,4; omega_dot block = cols 5,6) per
  scenario/time: `sort(N source pool) == sort(P source pool)` (both realize
  each device exactly twice); every source tuple changed; no P source is a
  true neighbour of its recipient (pi(i)=i+2 not in COMM_ADJ[i]); P and N
  read the same contemporaneous state pool; realized slot content equals the
  intended source feature (env COMM_ADJ wiring for N, permutation wiring for
  P). Any failure = `FACTORIAL-INVALID`, no training starts.
- **Operationalization record (guardrails preamble, 2026-08-23)**: the env's
  neighbour order is asymmetric (`COMM_ADJ = {0:[1,3], 1:[0,2], 2:[1,3],
  3:[2,0]`), so per-column/per-slot pool equality is not well-defined (the N
  col-3 source multiset {1,0,1,2} contains a duplicate that no device
  permutation can reproduce). The A.2 pool equality is therefore checked per
  feature channel (combined neighbour block), where N and P each realize every
  device exactly twice and the sorted pools are equal. The realized-slot
  identity check still verifies per-column wiring against the real COMM_ADJ.
- The check is implemented as a probe in the runner (`routing_check`) and
  recorded in rehearsal and in the formal pre-train gate output.

### Reuse gate (hardlinks, no regeneration)

- Reuse from R473 iff the R473 formal manifest lists the file, its sidecar
  hash matches, and the cell is NOT in the P-source retrain set.
- Retrain set (actor=P or critic=P) = 10 cells:
  `a0_cp, an_cp, ap_c0, ap_cn, ap_cp` x 2 rewards = 60 shards.
- Reused cells = 18 - 10 = 8:
  `a0_c0, a0_cn, an_c0, an_cn` x 2 rewards = 48 training shards, plus their 16
  evaluation shards from R473 (deterministic eval on identical checkpoints).
- Reuse all six R473 base states (`donors/seedN/base_state.pt`) as hardlinks;
  identity = R473 manifest base_state_sha256 per seed.
- After seal, import valid files as NTFS hardlinks and record source path,
  source hash, file identity, byte count in an import provenance manifest.
  Hardlinks add no second data bytes.

### Retrain and inference

- Freshly trained in R474: exactly the 10 P cells x 6 seeds = 60 shards,
  with the new same-time P semantics. The 48 reused cells are not re-run.
- Power n=6 inherited from sealed R431 (sd=0.0823901083, materiality
  log(1.10)); `OPTIMIZATION-UNRESOLVED` on failed/missing seed, half/final
  direction flip, or absent late stabilization (R470 rule).

### Evaluation, aggregate, hardware, durable launch

- After the 60 new shards: verify all 108 training manifests (60 fresh + 48
  reused), evaluate the 60 new shards' half/final checkpoints (20 eval
  shards), reuse the 48 cells' R473 eval JSONs (16 shards), then run the
  byte-identical R470 aggregate protocol and final manifest.
- Capacity: inherit the R473 post-reboot ladder evidence
  (`memory/rounds/R473/capacity_evidence.json`, same host, same 17-budget
  run just completed) — no fresh ladder; freeze 16 workers + 1 launcher, one
  native thread each, host budget 17, `other_reserved_processes` 0.
- Formal launch via hidden `Start-Process wsl.exe` with stdout/stderr
  redirected under `tmp/andes/r474_detached_*`. A nonzero phase stops the
  pipeline. No retry in R474; any post-seal scientific or orchestration
  failure requires a successor. Do not inspect R473/R474 endpoint outcomes
  before aggregation (structure-only checks allowed).

### Code review gate (owner-mandated, BLOCKING before rehearsal/seal)

- After implementation and before rehearsal: two independent reviewers audit
  the same runner diff:
  - **Reviewer A (diff/data-flow)**: every change of
    `scripts/run_r474_u2_source_factorial.py` vs `scripts/run_r473_u2_source_factorial.py`
    must be either the P-semantics change, its routing check, or the
    reuse/retrain split — nothing else (reward, network, optimizer, replay,
    schedule, RNG stream, environment, endpoints, thresholds unchanged).
  - **Reviewer B (guardrail §A.2 implementation)**: the routing check must
    actually verify each required property on real observations; the
    permutation must be structurally non-neighbour and fixed-point-free;
    no donor bank code path may remain reachable in training/eval.
- Every finding is fixed and pinned by a directed test before rehearsal.
- Review reports (PASS/FAIL + findings) are recorded in
  `memory/rounds/R474/code_review_a.md` and `code_review_b.md` and their
  hashes enter the seal. No seal without both PASS.

## Formal launch contract

- `formal_entry`: `scripts/run_r474_u2_source_factorial.py <phase>`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r474_u2_source_factorial.py rehearse`
- `rehearsal_scope`: routing-check on real three-step ANDES observations,
  objective/reward identities, reuse audit against R473 manifest, hardlink
  identity probe, retrain-set exactness (10 cells), initialization parity
  (same base as R473 per seed), terminal truth table, no-donor reachability
  (grep/import check), real three-step ANDES update; no formal root.
- `capacity_evidence`: `memory/rounds/R473/capacity_evidence.json` (inherited)
- `wsl_python_processes`: 17
- `native_threads_per_process`: 1
- `host_process_budget`: 17
- `other_reserved_processes`: 0

## Gate

- `U2-SOURCE-EFFECT-SUPPORTED`: all integrity/optimization/routing/reuse gates
  pass and at least one Holm-controlled primary `N-P` effect has CI lower
  bound above `log(1.10)` in the beneficial direction.
- `U2-SOURCE-EFFECT-NOT-SUPPORTED`: all gates pass but neither effect clears
  materiality and multiplicity.
- `OPTIMIZATION-UNRESOLVED`: failed/missing seed, budget-direction flip, or
  absent stabilization.
- `FACTORIAL-INVALID`: any import identity, routing-check, initialization,
  reward, executed-action, budget, evaluation, or hash gate fails.
- Wording (guardrails §A.3): under any outcome, a positive `N-P` effect is the
  total algorithm effect of the authentic neighbour source versus the
  same-time-permuted placebo at fixed other factors — never a pure semantic
  neighbour-information value, and no universal intrinsic communication claim.

## Theory intake

- Retained prediction (three-package intake 2026-08-22, guardrails §F P0):
  with the clean same-time placebo, `N` improves held-out primary loss over
  `P` by more than 10% for at least one role without a half/final direction
  flip.
  - observables: per-seed paired log-loss contrasts `N-P` at fixed
    critic/reward factors (R470 aggregate definition); half/final direction
    consistency; late-curve stabilization; Holm result; CI lower bound vs
    `log(1.10)`; routing-check flags.
  - verdicts: `supported` / `refuted` / `undecidable` written back in the feed.
- Guardrails §A.2 routing observables: the four properties (sorted-pool
  equality per slot/feature/scenario/time, every-tuple-changed, non-neighbour
  source, same contemporaneous pool) are machine-checked pre-train; any false
  flag is `FACTORIAL-INVALID` and is itself a refutation signal for the
  implementation, not a training outcome.
- Boundary: even a positive result remains a confounded total source effect
  (optimization gap uncontrolled); no semantic-value isolation claim.

## 资产保护契约

Preserve R431/R438/R451/R460/R470/R471/R472/R473 and imported GPT material
byte-for-byte. Add only the R474 runner + tests, the code-review reports,
reuse audit against the R473 manifest, hardlink-based result root, the 60 new
training shards, evaluation/aggregate results, analysis/report/claim/verdict,
and final package. Do not inspect R473 endpoint outcomes beyond structure
(validity, steps, identities, hashes) before R474 aggregation.

## Cross-references

- R473 manifest/analysis: `results/research_loop/r473_u2_source_factorial/`
  (`formal_manifest.json`, `import_provenance.json`).
- CLM-1475: U2 completed under the old exogenous-donor P (total-effect wording).
- CLM-1315: endpoint and paired-seed definitions; CLM-1360: same-learner
  16-worker capacity; CLM-1440: executed-action Bellman semantics.
- Guardrails: `skills/kundur-round/references/experiment-design-guardrails.md`
  §A (intervention purity + falsification-first + wording), §E (executed
  action), §F (next-round priorities).
