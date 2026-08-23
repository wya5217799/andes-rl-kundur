---
round: R475
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-23'
closed: '2026-08-23'
supersedes_rounds:
- R474
superseded_by_round: null
abort_reason: formal phases called the inherited R470 seal verifier; two reviewers
  did not cover one identical final hash set; sealed test source drifted during execution;
  no fresh training shard completed
superseded_note: null
---
# R475 plan — U2 confirmatory successor: row-permuted same-time placebo, all-fresh 2x2 factorial, direct materiality Holm

**Opened**: 2026-08-23
**Driver**: Owner decision A after R474 abort: adopt the external deep-review
redesign (`working/gpt_pro_r474_placebo_review_deep_20260823/02_MANDATORY_REDESIGN.md`)
— P becomes a row permutation of the authentic N neighbour 4-tuples
(`rho(i)=(i+1) mod 4`), the confirmatory factorial becomes all-fresh
`2x2 (actor, critic) x reward x seeds 401..406 = 48` training runs, and the
materiality gate directly tests `H0: effect <= log(1.10)` with Holm on the two
factor p-values. R474 was sealed+launched then aborted same-day at zero fresh
shards after the review proved the `pi(i)=(i+2)` diagonal-copy P fails the
guardrail's per-slot pool equality, batches mix at a 2/3 offset coefficient,
and the declared Holm materiality was not what the aggregate implemented.
**Parent**: CLM-1475/R473 (U2 supported under the old exogenous-donor P);
R474 abort record; guardrails
`skills/kundur-round/references/experiment-design-guardrails.md` §A; external
redesign `working/gpt_pro_r474_placebo_review_deep_20260823/02_MANDATORY_REDESIGN.md`.

## TL;DR

R475 retrains exactly 8 arm cells (48 shards: `an_cn, an_cp, ap_cn, ap_cp` x
`r0/r1` x seeds 401..406) all in one round with the P placebo redefined as the
pre-registered row permutation `P[i,3:7] = N[(i+1)%4,3:7]` of the authentic
same-time N neighbour block (own slots unchanged), verifies per-slot value
pools, full tuple multiset, non-neighbour sources and no-within-tuple-duplicate
by source-ID structure proof + actual-output checks + negative mutation tests
(the aborted `i+2` diagonal copy must FAIL), then evaluates all 48 checkpoints
in the same round's evaluator and runs a rewritten aggregate: profile-paired
`log(P/N)` main effects, direct sign-flip materiality at `log(1.10)` with Holm
over actor/critic, bootstrap demoted to descriptive sensitivity, and
design/execution/integrity/dynamics/effect fields separated. The 0-source
cells stay out of the confirmatory analysis. Wording keeps the total-algorithm
effect boundary (no pure semantic claim, no universal intrinsic claim).

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
  `results/research_loop/r475_u2_confirmatory`.
- Design: R470/R473 learner, optimizer, replay, schedule, environment,
  endpoints, thresholds and evaluation bank are inherited byte-identical;
  the only scientific changes vs R474 are (1) P routing = row permutation of
  the authentic N neighbour block, (2) confirmatory set = all-fresh 8 cells x
  6 seeds = 48 training shards with zero reuse of R473/R474 training or eval
  artifacts, (3) aggregate = profile-paired main effects + direct materiality
  Holm, (4) routing gate = per-slot + tuple-multiset + mutation-tested.
- `rho(i) = (i+1) mod 4`, `P[i, 0:3] = joint[i, 0:3]`, `P[i, 3:7] =
  joint[(i+1)%4, 3:7]` (row permutation of the authentic N 4-tuples; own
  features preserved). Pre-registered main direction; `rho(i)=(i-1) mod 4`
  is recorded as the pre-registered sensitivity direction and is NOT run
  unless explicitly ordered.
- N reads the same contemporaneous joint unpermuted; 0 zeroes slots 3:7.
  No pre-recorded donor trajectories anywhere; donor code paths unreachable.

### Falsification-first routing gate (guardrails A.2, BLOCKING)

- Source-ID structure proof (integer IDs, not float equality):
  1. `rho` is a permutation of 0..3; 2. `rho(i) != i`;
  3. for every i, neither P source is in `COMM_ADJ[i]` (sources of
     `N[(i+1)%4]` are neighbours of i+1 = {i, i+2}; true neighbours of i are
     {i-1, i+1}; disjoint);
  4. per-slot source-ID multisets of N and P are equal (row permutation);
  5. full ordered 2-source tuple multiset of N and P are equal;
  6. P tuple differs from N tuple for every i; 7. the two P sources differ.
- Actual-output value gate on real and synthetic joints: per column c in
  3..6, `sort(n_rows[:,c]) == sort(p_rows[:,c])`; row-tuple multiset equal;
  own columns 0:2 unchanged. No pool rebuilt from the expected formula.
- Mutation/negative tests (in unit tests, must FAIL on the aborted design):
  the `i+2` double-copy must fail; any single swapped P slot must fail; any
  true-neighbour source must fail; any fixed-point row permutation must fail;
  a donor-bank or other-time-step source must fail; `same_contemporaneous_pool`
  must be derived from the single-joint data flow (not hardcoded).
- real-ANDES integration smoke after the structure proof and synthetic
  actual-output tests (three-step ANDES update during rehearsal).

### Confirmatory factorial (all-fresh, no reuse)

- Cells: `an_cn, an_cp, ap_cn, ap_cp` x rewards {0,1} = 8 arms; seeds 401..406;
  48 training shards, 43,200 physical steps each, half/final checkpoints,
  full curves, endpoints. The 0-source cells (a0_*, *_c0) are OUT of the
  confirmatory analysis; R473 records remain descriptive history only.
- Base states: six R473 `donors/seedN/base_state.pt` reused by NTFS hardlink
  with R473-manifest hash identity (initialization parity, not training data);
  every fresh manifest records the hardlinked local path + sealed hash.
- Evaluation: all 48 checkpoints (16 arm-stage cells) evaluated by THIS
  round's evaluator in this round's eval phase; no R473/R474 eval JSON is
  read by the aggregate. Eval records, guards and thresholds identical to
  R470/R473.

### Inference protocol (external redesign section 6)

- Per-seed paired main effects (profile-paired first, then equal-weight):
  - actor: `D_actor,s = mean over critic in {N,P}, reward in {0,1},
    evaluation profile of log(L(ap_*)/L(an_*))` at the same profile;
  - critic: `D_critic,s = mean over actor in {N,P}, reward in {0,1},
    evaluation profile of log(L(*_cp)/L(*_cn))` at the same profile.
- Confirmatory p-values: `signflip_p_one_sided(values, log(1.10))` (full 2^6
  enumeration, one-sided at the materiality boundary), Holm over the two
  factor p-values at familywise alpha 0.05.
- Bootstrap CI95 (exact 6^6 resample enumeration, not Monte Carlo) is
  reported as `DESCRIPTIVE-SENSITIVITY` only; it never gates the verdict.
- Output: all six seed effects, mean, median, min, leave-one-out, direction
  count, plus half/final direction consistency and the inherited loss
  stability rows as dynamics qualifiers (never as a materiality substitute).
- Power: `memory/rounds/R475/power_analysis.json` re-done for the materiality
  target — null boundary log(1.10), alternative log(1.20), two-test Holm,
  discrete sign-flip procedure, seed-difference sd from sealed R431 with its
  uncertainty interval. n=6 is retained and the round is explicitly labelled
  LOW-RESOLUTION-CONFIRMATORY: at true 20% the normal-approximation power to
  establish >10% under the two-test Holm is about 73.5%, and the sign-flip p
  grid is k/64, so the first Holm threshold 0.025 requires 1/64. The plan
  does not claim 80% power to establish materiality.
- Classifier: orthogonal fields `design` (VALID|INVALID),
  `execution` (COMPLETE|INCOMPLETE), `integrity` (PASS|FAIL),
  `training_dynamics` (STABLE|UNSTABLE|NOT_ASSESSED),
  `material_effect` (ESTABLISHED|NOT_ESTABLISHED|NOT_TESTED), plus a
  human-readable verdict composed from them:
  - design/execution/integrity failure -> no confirmatory effect verdict;
  - dynamics unstable -> fixed-budget estimate retained, no
    "optimization-resolved" wording;
  - materiality not established -> `NOT_ESTABLISHED`, never "no effect".

### Code review gate (owner-mandated, BLOCKING before rehearsal/seal)

- Two independent reviewers audit the same runner diff vs
  `scripts/run_r474_u2_source_factorial.py`:
  - **Reviewer A (diff/data-flow)**: every change must be one of the four
    registered changes (P routing, retrain set, routing gate, aggregate
    protocol) — nothing else (learner, reward, optimizer, replay, schedule,
    RNG stream, environment, endpoints, thresholds unchanged).
  - **Reviewer B (guardrail §A.2 implementation + mutation suite)**: the
    routing gate actually verifies each required property on real outputs;
    the permutation is fixed-point-free, non-neighbour, per-slot-pool- and
    tuple-multiset-preserving; the aborted `i+2` copy fails the negative
    tests; no donor code path is reachable.
- Structured review artifacts (JSON): schema_version, reviewer id,
  reviewed commit + file hashes, decision=PASS|FAIL, open P0/P1 counts,
  findings list. Reports live at
  `memory/rounds/R475/code_review_a.json` / `code_review_b.json`.

### Rehearsal, seal, launch, capacity

- Rehearsal: all probes enter a single required list and `passed` is the AND
  of every probe — routing (structure + synthetic actual-output + real
  three-step ANDES), objective semantics, reward identity, terminal truth
  table, U3 executed-action paths, initialization parity, hardlink identity,
  retrain-set exactness (8 arms), no-donor reachability, short ANDES update.
- Seal: `load_seal` re-verifies the seal hashes of plan, power, routing gate,
  rehearsal, both structured reviews, capacity, sources, shard lists at every
  formal phase (not only contract+sources).
- Capacity: inherit R473 post-reboot ladder evidence (same host, 17-budget
  run just completed twice); freeze 16 workers + 1 launcher, one native
  thread each, host budget 17, `other_reserved_processes` 0.
- Formal launch via hidden `Start-Process wsl.exe` with stdout/stderr
  redirected under `tmp/andes/r475_detached_*`; nonzero phase stops the
  pipeline; no retry inside R475; post-seal failure requires a successor.
- Do not inspect R473/R474 endpoint outcomes beyond structure before
  aggregation (structure-only checks allowed).

## Formal launch contract

- `formal_entry`: `scripts/run_r475_u2_confirmatory.py <phase>`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r475_u2_confirmatory.py rehearse`
- `rehearsal_scope`: routing structure proof + synthetic actual-output +
  real three-step ANDES, objective/reward identities, retrain-set exactness
  (8 arms), initialization parity (R473 base hardlinks), terminal truth
  table, no-donor reachability, real three-step ANDES update; no formal root.
- `capacity_evidence`: `memory/rounds/R473/capacity_evidence.json` (inherited)
- `wsl_python_processes`: 17
- `native_threads_per_process`: 1
- `host_process_budget`: 17
- `other_reserved_processes`: 0

## Gate

- `MATERIAL-EFFECT-ESTABLISHED`: all design/execution/integrity/dynamics
  gates pass and at least one factor's direct materiality p-value
  (`H0: effect <= log(1.10)`) rejects under Holm (first threshold 0.025).
- `MATERIAL-EFFECT-NOT-ESTABLISHED`: all gates pass but neither factor
  rejects the materiality null under Holm.
- `EXECUTION-INCOMPLETE`: missing shard / failed seed / missing eval.
- `INTEGRITY-INVALID` / `DESIGN-INVALID`: hash, reward, initialization,
  budget, routing, or semantic gate failures (routing failure =
  `DESIGN-INVALID`; no training starts).
- `TRAINING-DYNAMICS-UNSTABLE` is a qualifier, not a verdict killer, unless
  the pre-registered objective requires stability.
- Wording under any outcome: a positive `N-P` effect is the total algorithm
  effect of the authentic neighbour source versus the pre-registered
  same-time row-permuted placebo at fixed other factors — never pure semantic
  neighbour-information value, no universal intrinsic communication claim.

## Theory intake

- External-review prediction (deep package 2026-08-23, guardrails §A):
  with the clean row-permuted placebo, `N` improves held-out primary loss
  over `P` beyond 10% for at least one role under the direct materiality
  Holm, OR the effect is not established at that bar.
  - observables: per-seed paired log effects; direct materiality p-values
    and Holm outcome; half/final direction consistency; late-curve
    stabilization; bootstrap only descriptive; routing/mutation flags.
  - verdicts: `supported` / `refuted` / `undecidable` written in the feed.
- Boundary: even a positive result remains a confounded total source effect
  (optimization gap uncontrolled, residual self/diagonal structure inherent
  to the 4-ring); no semantic-value isolation claim.

## 资产保护契约

Preserve R431/R438/R451/R460/R470/R471/R472/R473/R474 and imported GPT
material byte-for-byte. Add only the R475 runner + tests, structured code
reviews, power analysis, routing gate, rehearsal, seal, result root (48
fresh training shards + eval + aggregate), analysis/report/claim/verdict, and
final package. Do not inspect R473/R474 endpoint outcomes beyond structure
before R475 aggregation.

## Cross-references

- External redesign: `paper/yang_md_decoupling_marl/working/gpt_pro_r474_placebo_review_deep_20260823/02_MANDATORY_REDESIGN.md` (and `01_R474_DEEP_REVIEW.md` findings F-01..F-13, verification record `03_VERIFICATION_RECORD.md`).
- R474 abort: `memory/rounds/R474/plan.md`, `memory/rounds/R474/verdict.md`.
- CLM-1475: U2 completed under the old exogenous-donor P (total-effect wording, statistics superseded by this round's direct materiality protocol).
- CLM-1315: endpoint and paired-seed definitions; CLM-1360: same-learner 16-worker capacity; CLM-1440: executed-action Bellman semantics.
- Guardrails: `skills/kundur-round/references/experiment-design-guardrails.md` §A/E/F.
