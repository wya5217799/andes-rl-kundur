---
round: R289
state: completed
opened: '2026-07-30'
closed: '2026-07-30'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R289 plan — sealed multigraph single-circuit topology-information gate

**Status**: ACTIVE
**Opened**: 2026-07-30
**Driver**: Correct R288's simple-graph dead end prospectively, without
reinterpreting R288 or reading an R289 EIG endpoint.
**Parent**: CLM-0655, CLM-0615, CLM-0630; Q-0047

## TL;DR

No training and no time domain. Freeze one canonical single-circuit outage in
each retained parallel corridor (5-6, 6-7, 9-10), verify connectivity and q0
PFlow, then seal. On nominal plus the three variants, compare q0 with the six
R277 Hadamard zero-sum inertia allocations in a 4x7 EIG matrix. Measure the
per-configuration oracle against the best topology-blind robust fixed action.
This is a same-node multigraph/status/admittance experiment, not changed
simple adjacency and not structural topology generalisation.

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

### A. Frozen plant and action library

- Plant: `AndesMultiVSGEnvV4._build_system()` unchanged.
- VSG order: buses `[12,16,14,15]`; G4, PFlow/EIG, and the R281 mode rule stay
  in `probes/eig_alloc_common.py`.
- Actions, fixed order:
  - q0 `[350,350,350,350]`;
  - h1+ `[500,500,200,200]`, h1- `[200,200,500,500]`;
  - h2+ `[500,200,500,200]`, h2- `[200,500,200,500]`;
  - h3+ `[500,200,200,500]`, h3- `[200,500,500,200]`.
- Every action has total M=1400. No controller, reward, checkpoint, scenario,
  environment default, training, or time-domain execution is introduced.

### B. Stage A — prospective multigraph configurations, before EIG

R288's immutable inventory is structural input only. It established that all
nonparallel non-VSG lines are bridges and that the simple-graph screen has no
candidate. R289 does not edit or reinterpret that result.

The configuration set is frozen now:

1. `topology_1`: open `Line_0` from the 5-6 pair (`Line_0`,`Line_1`);
2. `topology_2`: open `Line_2` from the 6-7 pair (`Line_2`,`Line_3`);
3. `topology_3`: open `Line_9` from the 9-10 pair (`Line_9`,`Line_10`).

The canonical circuit is the lowest numeric line suffix in each group. All
circuits within a selected pair must be active with finite positive x. Their
r/x/b fields are recorded but never used for selection; the fixed plant
contains a 1e-5 r/x offset between paired circuit records. Opening the
canonical circuit must change exactly one `Line.u`, preserve active-bus
connectivity, bus/VSG counts, G4, and total-M, and converge q0 PFlow.

The 7-8 `Line_4/5/6` group is excluded because it is the prior declared
corridor axis. The 8-9 group is excluded because it contains `Line_8`, whose
Toggler semantics are protected. VSG stubs and single-circuit bridges remain
excluded. If any exact selected pair/line or guard is absent, Stage A is
INVALID and no seal or EIG is allowed.

After the three q0 PFlow checks pass, write
`results/r289_topology_information/topology_inventory.json` and
`memory/rounds/R289/topology_information_seal.json` with create-only sidecars.
The seal contains the exact line table, exclusions, actions, thresholds,
R281 anchors, and plan/input/code hashes. No reselection follows the seal.

### C. Stage B — sealed 4x7 EIG matrix

For nominal plus the three sealed outages, build a fresh plant for each of the
seven actions, open only the declared circuit, rerun PFlow, and run EIG.
Use the unchanged R281/R283 identification:

- merge conjugate entries;
- keep 0.2-1.5 Hz modes;
- select max `abs(P_area1-P_area2)`;
- within each topology, compare each action with its q0 anchor using
  participation cosine >=0.90 and `abs(df)<0.05 Hz`;
- compare each variant q0 with nominal q0 using cosine >=0.80 and
  `abs(df)<0.10 Hz`.

Each cell records PFlow, G4, total-M, exact-opened-line, bus/VSG counts,
finite eigenvalues, and no real part above 1e-7. Nominal q0/h1+/h1- must
reproduce R281 q=0/+0.25/-0.25 damping ratios within absolute 1e-6.

### D. Registered estimands

For topology t and action a:

`zeta_ratio(t,a)=zeta(t,a)/zeta(t,q0)`.

- Per-topology oracle: maximum damping ratio; ties prefer q0 then frozen order.
- Topology-blind robust fixed: one common action maximizing the minimum
  zeta-ratio over all four configurations; same tie rule.
- Headroom:
  `100*(zeta_oracle(t)-zeta_fixed(t))/abs(zeta_fixed(t))`.
- Report per-topology oracle/fixed damping, action count, headrooms, mean/max
  headroom, robust worst-case ratio, all branch checks, and all guards.

## Gate

1. **INVALID**: missing/drifting seal, source, sidecar, exact configuration,
   4x7 cell, anchor, PFlow, G4, total-M, bus/VSG, finite/stability, or
   opened-line guard.
2. **PARTIAL-IDENTIFICATION**: integrity passes, but a cross-topology q0 or any
   within-topology action branch check fails. Headroom is descriptive only.
3. **STATIC-TOPOLOGY-VALUE**: all checks pass, at least two distinct oracle
   actions occur, max headroom >=5%, and four-topology mean headroom >=2%.
4. **NO-MATERIAL-TOPOLOGY-VALUE**: valid complete matrix that does not meet 3.

Only 3 permits proposing a later classical topology-conditioned time-domain
question. It does not authorize training or GNN, and no follow-up starts
automatically. Result visibility cannot change lines, actions, thresholds,
branch rules, anchors, estimands, or classifications.

## Outcomes

- Complete exactly one sealed 4x7 matrix or stop with retained INVALID
  evidence.
- Reserve the claim before feed numeric statements; publish a pointer-first
  `results/r289_topology_information/FEED.md`.
- Run evidence and power-system domain gates on the feed, then feed check,
  claim/verdict/question/programme close-out, validation, rendering, governance
  checks, and relevant tests.
- Do not bind R289 to the active SCI line unless its publication gate later
  explicitly authorizes it.

## 资产保护契约

- Preserve all R288 files and hashes; the R288 probe is a read-only execution
  parent if reused.
- Preserve all R277/R281-R287 data, controller/checkpoint code, manuscript
  prose, LaTeX, figures, journal files, and existing tracked/untracked edits.
- Real ANDES runs only under WSL `/home/wya/andes_venv/bin/python`, via
  `scripts/andes_scratch.py`; scratch directories are retained.
- Formal R289 artifacts are create-only. A retained integrity or execution
  failure stops the round and is never deleted or retried.

## Cross-references

- CLM-0655 / R288 — simple-graph intervention design is infeasible, not a
  topology-value result.
- CLM-0615 / R281 — nominal EIG anchors and spatial-allocation response.
- CLM-0630 / R283 — branch checks and bounded small-signal scope.
- `docs/research/2026-07-30_topology_information_value_gate.md#decision`.
