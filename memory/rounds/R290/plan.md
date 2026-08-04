---
round: R290
state: completed
opened: '2026-07-30'
closed: '2026-07-30'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R290 plan — minimal topology-application and EIG-initialization diagnosis

**Status**: ACTIVE
**Opened**: 2026-07-30
**Driver**: R289 is invalid and cannot distinguish a topology-application/
initialization defect from a genuine positive-real mode.
**Parent**: CLM-0660, CLM-0655; Q-0047

## TL;DR

Do not repeat R289. Build a deterministic q0-only WSL feedback loop on the
sealed Line_2 outage, reproduce the initialization/positive-real symptom, and
minimize it. Inspect the local ANDES source only after the loop is red, rank
falsifiable hypotheses, then compare one topology-application variable at a
time. Separately replace implicit JSON dictionary order with an explicit
allocation-order list and lock it with a pure regression test. This round
produces diagnostic evidence only.

## Snapshot at plan-time (oracle as of 2026-07-30)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0047 [opened R287] Does genuine network-configuration variation create material small-signal value for topology-conditioned differential-inertia allocation?

## Recently Closed (last 3)

- Q-0046 closed-positive @ R287, by CLM-0650 — Does the frozen differential-allocation gain retain material value when the declared inter-area corridor weakening is extended from k=2.0 to k=2.5 and k=3.0?
- Q-0045 closed-positive @ R286, by CLM-0645 — Does the differential-allocation gain survive a weakened inter-area tie corridor in time domain, and does it depend on disturbance location?
- Q-0044 closed-positive @ R285, by CLM-0640 — What is the structure of the inter-area / VSG-local mode hybridization zone at low aggregate inertia (M0 in [100,200), q = +/-0.25)?

## Methodology

### A. Frozen diagnostic object

- Plant: `AndesMultiVSGEnvV4._build_system()` and q0
  `[350,350,350,350]`; total M=1400.
- Primary diagnostic target: the already sealed R289 `Line_2` outage only.
- Nominal q0 is the matched control.
- No alternate line, Hadamard action, controller, training, time integration,
  value matrix, damping comparison, or manuscript artifact is allowed.
- R288/R289 artifacts are read-only inputs and are never retried or
  reclassified.

### B. Phase-1 red-capable feedback loop

Create one WSL scratch command that:

1. builds the frozen plant and sets q0;
2. applies the R289 post-setup `Line.u=0` path to Line_2;
3. runs PFlow, the exact initialization path reached by EIG, and EIG;
4. records exact changed-line status, initialization return/success state,
   maximum algebraic residual available from ANDES, positive-real count and
   maximum real part;
5. exits nonzero when initialization fails or any real part exceeds 1e-7.

Run it at least twice before source-level hypotheses. Minimize to nominal q0
plus Line_2 q0. Console text alone is not the formal result; the final
diagnostic writes create-only JSON plus sidecar.

### C. Hypothesis and one-variable probes

After the loop is reproducibly red, inspect the local installed ANDES source
and the V4 builder. Record 3-5 ranked, falsifiable hypotheses in the diagnostic
artifact before testing. Each probe changes one of:

- when line status is applied relative to setup/PFlow;
- which documented ANDES refresh/setup API is invoked;
- whether EIG is called before or after a verified initialization.

Do not change the plant, line, q0, solver tolerances, eigenvalue threshold, or
mode band. A method is eligible only if exact line status, connectivity,
PFlow, initialization, finite residual/eigenvalues, and the 1e-7 positive-real
guard all pass. A passing method must reproduce nominal R281 q0 damping within
1e-6 before it can be considered a future execution path.

Hypotheses frozen after the two identical red reproductions:

1. post-setup `Line.u` mutation leaves setup-derived topology state stale;
2. the public `Line.set` API, optionally followed by connectivity refresh, is
   sufficient even after setup;
3. EIG continues after `TDS.test_ok=False`, so positive-real modes may be an
   artifact of an invalid initialized state;
4. if pre-setup application yields `TDS.test_ok=True` but preserves the same
   positive pair, the Line_2 q0 mode is genuinely unstable under this model.

Probe order is frozen: current direct mutation; public `Line.set`; public
`Line.set` plus connectivity refresh; a diagnostic setup hook that applies the
same line status immediately before the environment's existing `ss.setup()`.
The first passing method does not stop later registered probes.

### D. Order-preserving seal contract

Add a pure contract with both:

- explicit `allocation_order =
  [q0,h1_pos,h1_neg,h2_pos,h2_neg,h3_pos,h3_neg]`;
- allocation values keyed by name.

Canonical JSON may sort mapping keys, but every iterator and matrix validator
must use the explicit list. A red-then-green test round-trips through
`json.dumps(sort_keys=True)` and proves q0 remains first.

## Gate

- **ROOT-CAUSE-AND-PATH-VALIDATED**: the old path is reproducibly red; one
  source-supported one-variable method passes every initialization/eigenvalue
  guard and nominal anchor; regression tests lock the mechanism.
- **ROOT-CAUSE-BOUNDED-NO-VALID-PATH**: the old path is reproducibly red and
  hypotheses are tested, but no safe method passes. Q-0047 is blocked pending
  a different plant construction or external ANDES guidance.
- **INVALID-DIAGNOSTIC**: the symptom cannot be reproduced deterministically,
  source/probe hashes drift, the formal diagnostic is incomplete, or the
  probe changes more than the declared topology-application mechanism.

No outcome authorizes a new value matrix automatically. The round stops after
diagnosis, tests, feed, and ledgers.

## Outcomes

- `scripts/diagnose_r290_topology_initialization.py`
- focused pure/order and adapter tests
- create-only `results/r290_topology_initialization/diagnostic.json` plus
  sidecar and provenance
- pointer-first `results/r290_topology_initialization/FEED.md`
- claim, verdict, Q-0047 update, validation, rendering, and PI briefing

## 资产保护契约

- Do not edit any R288/R289 plan, seal, inventory, matrix, analysis,
  provenance, claim, feed, or verdict.
- Keep environment/controller/training/checkpoint/manuscript/LaTeX/figure/
  venue files unchanged.
- Real ANDES runs only in WSL `/home/wya/andes_venv/bin/python` through
  `scripts/andes_scratch.py`; preserve scratch.
- Diagnostic JSON is create-only. Retained failure is evidence, not a retry
  target.

## Cross-references

- CLM-0660 / R289 INVALID matrix and positive-real guards.
- CLM-0655 / R288 structural-feasibility boundary.
- CLM-0615 / R281 nominal q0 anchor.
- `results/r289_topology_information/FEED.md`.
