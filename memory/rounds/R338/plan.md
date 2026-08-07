---
round: R338
state: completed
opened: '2026-08-04'
closed: '2026-08-05'
supersedes_rounds:
- R337
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R338 plan - parallel execution successor for the ICEMS comparison

**Opened**: 2026-08-04
**Driver**: Preserve the frozen genuine distributed-versus-single-actor study
while replacing R337's accidentally serial formal scheduler with three real
concurrent WSL workers and a small physical canary gate.
**Question**: Q-0088
**Parent**: R337 aborted execution; no R337 formal outcome is a parent result.

## TL;DR

The paper title and scientific comparison do not change. R338 may reuse only
the ten R337 checkpoints and the controller-blind R337 fresh bank that were
sealed before any formal controller outcome was available, after exact hash
verification. The 65 partial R337 formal traces, failure record, progress,
logs, and formal output directory are forbidden inputs. A new R338 seal and a
new empty formal directory are mandatory.

Execution proceeds in small gates. First prove three-way concurrency with
offline workers. Then run one short physical canary per worker, covering the
classical controller, matched joint-observation actor, and neighbour-only
distributed actor. The canary is scheduling evidence only: no performance
endpoint may be summarized or used to select anything. Only a canary that
passes concurrency, isolation, completion, and provenance checks may release
the complete 264-new-trajectory formal matrix.

## Snapshot at plan-time (oracle as of 2026-08-04)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Kept as the immutable plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify
  1e-9 bit-identical from WSL before landing.
- Q-0026 [opened R260] Will the Archive Index actually be queried?
- Q-0087 [opened R336] Which location-dependent input dynamics explain the
  upstream-load mismatch before any bridge repair?
- Q-0088 [opened R337] On the fixed four-VSG path, does a neighbour-only
  distributed edge residual add guarded value beyond the selected causal edge
  controller and remain non-inferior to a matched joint-observation actor?

## Recently Closed (last 3)

- Q-0086 closed-negative at R336 by CLM-0885.
- Q-0085 closed-positive at R334 by CLM-0880.
- Q-0084 closed-negative at R332 by CLM-0870.

## Authority and comparison identity

- Selected line: `paper/icems2026`. The protected title remains byte-for-byte
  `Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent
  Reinforcement Learning`.
- Lane: `evidence`. R338 creates new physical canary and formal trajectories.
  No manuscript text changes before the publication gate.
- Distributed arm: one shared actor is invoked separately on each path edge
  using only the two endpoint observations; its three scalar outputs are the
  three executed edge actions. A joint critic is training-only.
- Single-actor arm: one joint-observation actor emits the identical three edge
  actions. Actor capacity, classical prior, projection, limits, reward,
  training budget, seeds, bank, bootstrap, and thresholds remain R337's frozen
  objects.
- Claim ceiling remains local to one modified-Kundur plant, one fixed
  four-node path, and the executed information/action formulation. No generic
  multi-agent, topology, stability, deployment, or transfer claim is allowed.

## Immutable upstream acceptance

- Allowed R337 upstreams: `results/r337_prior_residual_training` and
  `results/r337_fresh_bank`, including their seals, summaries, hashes,
  checkpoints, controller contracts, formal bank, and frozen q0 screen traces.
- Acceptance reason: these objects were prospectively specified and sealed
  before R337 formal execution; stopping R337 changed only the scheduler and
  did not change or select training seeds, checkpoints, cases, arms, rewards,
  margins, or thresholds.
- Every allowed upstream file consumed by R338 must match its recorded hash.
  Checkpoint metadata remains truthfully R337; R338 records it as an immutable
  upstream rather than relabelling it as newly trained.
- Forbidden R337 inputs: `results/r337_formal_evaluation`, its 65 partial
  traces, `formal_seal.json`, `formal_attempt.json`, `formal_failure.json`, all
  formal logs, and any formal performance endpoint. No copying or resuming is
  permitted.

## Methodology

Implement a thin execution-only adapter over the frozen formal evaluator. The
adapter changes round identity, output paths, truthful upstream provenance,
and scheduling only; it does not change the plant, controllers, observation or
action spaces, training objects, scenario bank, metrics, or decision rule.
Test the public host-launch and worker seams before creating the R338 seal.
After sealing, execute and classify only the declared short canary in this
turn. The complete formal evaluation remains a separately released second
step under the same immutable contract.

## Small-step execution gates

### Gate 0 - offline scheduler

- Host-side launcher starts all workers before waiting.
- Exactly three worker commands, three unique shard indices, three unique
  scratch directories, three unique log files, and a global denominator of
  264 are required.
- Each WSL worker uses one Python process; native numerical threads are fixed
  to one. The repository-wide WSL Python cap is three.
- A shared-barrier integration test must prove overlap, and three dummy workers
  must produce three unique outputs with global progress `3/3`.

### Gate 1 - short physical canary

- Create the R338 formal seal first, with zero R338 formal traces at freeze.
- Launch exactly three workers concurrently. Each executes one fixed 15-step
  physical trajectory on the first frozen scenario: respectively the selected
  classical arm, centralized seed 421, and distributed seed 421.
- Canary paths are confined to `results/r338_parallel_canary`; they never enter
  the formal matrix. Read only start/completion/provenance fields and hashes;
  do not aggregate or compare physical endpoints.
- Pass requires all three workers to cross the shared readiness barrier,
  produce exactly one unique completed record, report no simulator failure,
  match the new seal and old immutable upstream hashes, preserve three logs,
  and overlap in wall-clock execution. Any collision, timeout, extra process,
  incomplete record, or provenance drift is a retained canary failure.

### Gate 2 - complete formal matrix

- Only Gate 1 PASS may release the host launcher for three concurrent formal
  shards. Formal execution uses 300 steps, the unchanged 24-case bank, 11 new
  controller arms, and a global total of 264 new trajectories. The 24 frozen
  q0 records are reused exactly as declared, yielding the unchanged 288-cell
  analysis matrix.
- Output is create-only under `results/r338_formal_evaluation`; logs are
  create-only under `results/r338_parallel_logs`. Existing outputs cause a
  hard stop. No retry, seed replacement, case redraw, arm change, threshold
  change, or outcome-driven tuning is allowed.
- The three workers may run in parallel, but analysis runs only once after
  exactly 264 new trace records exist and all workers exit zero.

## Formal decision and stopping rule

Use the unchanged R337/R293 decision tree: first require integrity and
controller-completion guards; then test distributed improvement over the
selected classical controller and distributed superiority or local
non-inferiority against the matched centralized actor on both co-primary
endpoints. A negative result is retained without repair.

Stop this small-step turn after Gate 1 is classified. Do not automatically
start the multi-hour Gate 2 run merely because the canary passed. A later
explicit continuation may launch Gate 2 without changing its seal or contract.

## Asset and close-out contract

- New assets are confined to `memory/rounds/R338`, `results/r338_*`, an R338
  adapter, the reusable host launcher/scratch fix, and focused tests. R337
  artifacts remain byte-for-byte retained.
- After a complete formal result, publish and audit the paper-facing feed
  before claim registration or manuscript edits, then close the verdict,
  update Q-0088, reconcile only the selected ICEMS navigation files, and run
  repository health, validation, rendering, focused/full tests, and the exact
  three-part plain-Chinese PI delivery.

## Cross-references

- Direct question: `memory/questions/Q-0088.md`.
- Selected manuscript: `paper/icems2026/LINE.md`.
- Genuine comparison contract: `memory/rounds/R337/plan.md`.
- Aborted serial execution record: `memory/rounds/R337/formal_failure.json`.
