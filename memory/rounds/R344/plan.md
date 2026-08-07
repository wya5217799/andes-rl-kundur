---
round: R344
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-06'
closed: '2026-08-06'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R344 plan - separate-input deterministic physical bridge

**Opened**: 2026-08-06
**Driver**: Answer Q-0090 with one small, staged physical bridge before any distributed or learning work.
**Parent**: CLM-0900; R341 finite fresh-bank model qualification.

## TL;DR

Workload: `evidence`. Bind the two immutable R341 point-specific order-12
models to one full-output constrained horizon controller. First pass offline,
same-path, capacity, zero-action and signed-authority gates. Only then compare
that controller with zero control on one finite paired disturbance bank. Any
valid negative stops. No distributed runtime, reward, agent, training, EVAL,
topology change or title-result endpoint.

## Snapshot at plan-time (oracle as of 2026-08-06)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete - render STATE.md to refresh the oracle, but keep this block. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0090 [opened R341] Can the fresh-qualified predictor support a deterministic physical bridge before any distributed or learning experiment?

## Recently Closed (last 3)

- Q-0089 closed-positive @ R341, by CLM-0900 - finite fresh-bank separate-input model gate passed.
- Q-0087 closed-partial @ R339, by CLM-0890 - old static projected input bridge was inadequate.
- Q-0088 closed-negative @ R338, by CLM-0905 - separate ICEMS line; no transfer to this round.

## Frozen object

- Models: exact `FV0` and `FV1` order-12 objects in
  `results/r341_staged_fresh_model_validation/candidate_models.json`, whole-file
  SHA-256 `7a74cb78dca8c5e30f32a344ca43704079a1549c966ff21de492eba7a3f1e32e`.
  Keep four control and four physical-load inputs distinct. Never use `B(u+d)`
  or `d=M u`.
- Points: `FV0=(M=183.75,D=91.875,tie=1.16,SOC=0.435)` and
  `FV1=(M=211.25,D=105.625,tie=1.40,SOC=0.535)` on the R341 physical base.
- Controller: centralized full-output receding constrained horizon; one common
  plus three action-tree coordinates; horizon 25; action scale `0.36`;
  disturbance-augmented order 16 estimator with disturbance scale `0.05` and
  measurement fraction `0.01`. Output scales are point-specific maximum
  absolute zero-referenced coordinate responses over the already exposed R341
  lower-amplitude 25-step ramp-hold bank: FV0
  `[0.0005208588784582888,0.00020891280532014673,0.0002641363410614004,0.0004599914624251534]`;
  FV1
  `[0.0005014001877174584,0.0002058568956880255,0.00024780152784620513,0.00043006662398575727]`.
  This is a bridge object, not DMPC, distributed control or a stability proof.
- Solver: OSQP builtin direct, max 20000 iterations, absolute/relative
  tolerance `1e-9`, feasibility tolerance `1e-8`. Any solver failure invokes
  one power/ramp/SOC/energy-bounded move toward zero; any fallback in the
  claim-bearing bank is a valid bridge failure.
- Semantics: controller consumes previous delivered frequency coordinates and
  previous achieved `v*Ipout_y`; ramp state uses previous external command.
  Persist request, projected command, `Pext0`, `Psum`, `Ipcmd_y`, `Ipout_y`,
  `Ipmin`, `Ipmax`, recovery coefficients, voltage, SOC and achieved power.
- Limits: 0.2 s sample; node power `0.36` system p.u.; node ramp `0.072` per
  sample; 100 MVA system; 28 MWh per device; SOC `[0.2,0.8]`; charge/discharge
  efficiency `0.9848857802`; all internal ESD1 limits remain active.

## Methodology

0. **Offline return**: public-seam tests bind both candidate hashes, prove rank
   16 observability, stable estimator error poles, zero action at zero input,
   opposite signed common response and bounded request. This stage is complete
   only as engineering readiness; it creates no evidence.
1. **Implementation**: add one stable R344 adapter and public controller-step,
   trace-guard, staged-stop and analysis tests. The Windows and WSL scientific
   environments must pass the same focused suite before any live trajectory.
2. **Capacity ladder**: HOLD while R343 retains 16 processes. After R343 is
   terminal, run the same 32 exposed R341 lower-amplitude jobs (both points,
   four channels, both signs, two waveforms) at 16, 24 and 32
   single-thread workers. Preserve every rung. Select the valid rung with the
   highest completed-job throughput; reject any rung with failure, overlap or
   isolation loss, swap use, or less than 4 GiB WSL available memory. Freeze
   that whole-host budget before the R344 seal. No endpoint enters selection.

### Pre-seal execution amendment 1 (2026-08-06)

R343 was closed at the user's direction after its plumbing canary; no R343
formal result exists and no research process remains active. The first R344
capacity attempt is preserved at
`memory/rounds/R344/capacity_ladder.json` and
`results/r344_deterministic_bridge/capacity/rung_16/failure.json`. It stopped
before any representative job or physical trajectory because the isolated
launcher could not import the repository `scripts` package. No performance
endpoint was inspected. One repaired capacity attempt is authorized at
`memory/rounds/R344/capacity_ladder_attempt_2.json` and
`results/r344_deterministic_bridge/capacity_attempt_2/`. Only repository-path
bootstrap and create-only output routing changed; the 32 jobs, 16/24/32 rungs,
one native thread, guards, selection rule, scientific contract and stop tree
remain frozen. Preserve both attempts; no further capacity retry is authorized.
3. **Reconcile and same-path rehearsal**: write the selected capacity into this
   plan and `host_capacity.json`, with zero other reserved processes. Then run
   one create-only rehearsal through the exact WSL scratch launcher. It verifies
   source/parent hashes, installed ANDES/case, Python/numerical/OSQP identity,
   exact manifest round-trip, output absence, selected process budget and
   scratch isolation. It creates no attempt, seal or physical trace. Only a
   passing post-capacity rehearsal may enter the create-only R344 seal.
4. **Zero-action canary**: one five-interval record at each point, no load edit,
   controller bypassed, zero request. Any runtime, timing, equilibrium,
   line-status, readback, limiter, SOC or finite-value failure aborts R344.
   Require request, projected command and achieved power within `1e-8` system
   p.u. of zero, SOC drift at most `1e-8`, physical-frequency deviation at most
   `1e-8` Hz and algebraic residual at most `1e-8`.
5. **Signed-authority canary**: at both points, four control coordinates, both
   signs, magnitude `0.05` system p.u., five active plus twenty recovery
   intervals: 16 records. Controller bypassed. Require requested and projected
   signs, achieved sign, common/edge map, neutrality, no limiter/guard failure,
   and complete request-command-achieved provenance. Request and command must
   match within `1e-12`; final active achieved power must be within 5% of the
   request; edge request/command sums must be within `1e-12` of zero; final
   achieved fleet imbalance must be at most 5% of commanded L1 power. Any
   failure aborts.
6. **Paired bridge bank**: 16 scenarios = two points x four R341 physical load
   channels x two signs. Use only the lower registered ramp-hold amplitude:
   `0.03` system p.u. for `PQ_0`, `PQ_1`, and `PQ_Bus14`; `0.02` for
   `PQ_Bus15`; 25 intervals, exact R341 baseline rows and one-sample timing.
   Execute two arms per
   scenario: zero control and the frozen controller, for 32 new trajectories.
   Paired arms share initialization, solver, disturbance, sampling and guards.
   Stage 6 opens only after Stages 0-5 pass and explicit formal release.

## Decision and endpoints

Primary lower-is-better endpoints, computed only after all 32 formal traces
exist: (1) common-coordinate integral absolute error; (2) summed squared three
differential coordinates. Report physical mean-frequency and maximum pairwise
frequency deviation, action, SOC, achieved fleet imbalance and all guards as
secondary diagnostics.

- `DETERMINISTIC-BRIDGE-PASS`: every validity/physical guard passes; no solver
  fallback or saturation; controller engages on every nonzero case; both
  primary paired means improve by at least 2% versus zero control; each point
  improves directionally on both endpoints; no scenario worsens either
  endpoint by more than 5%.
- `VALID-NO-DETERMINISTIC-BENEFIT`: all traces and guards are valid but any
  efficacy condition fails. Close Q-0090 negative; no learning.
- `DETERMINISTIC-PHYSICAL-GUARD-FAIL`: execution is valid but any solver,
  fallback, limiter, SOC, energy, action, timing or physical guard fails.
  Close Q-0090 negative; no learning.
- `INVALID-DETERMINISTIC-BRIDGE`: seal, source, manifest, launcher, process,
  trace or analysis integrity fails. Preserve the attempt; no in-round retry.
- A pass authorizes only a separately registered residual-headroom question.
  It does not authorize neural training by itself.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r344_deterministic_bridge.py execute-canaries --expected-sha256 <seal>`
- formal_release_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r344_deterministic_bridge.py execute-formal --expected-sha256 <seal>`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r344_deterministic_bridge.py rehearse`
- capacity_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r344_deterministic_bridge.py capacity-ladder`
- rehearsal_scope: same-pre-attempt-path; no attempt, seal or physical output
- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,manifest_roundtrip,output_absence,process_budget,scratch_isolation
- wsl_python_processes: 32
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R344/host_capacity.json`
- host_process_budget: 32
- other_reserved_processes: 0

The repaired capacity ladder completed all three rungs. The 32-process rung
had the highest valid completed-job throughput, with all jobs overlapping,
isolated scratch directories, no swap use and more than 4 GiB WSL available
memory. These values are frozen before rehearsal and seal; do not resize them
from canary or formal outcomes.

## Asset protection

R341 models, seals, traces, thresholds and conclusions remain immutable. R343
and ICEMS assets are read-only. Add only the R344 adapter, focused tests,
R344 ledger/seals, and `results/r344_*`. Before the publication gate do not
edit manuscript prose, title, existing claims or another paper line. No bank,
threshold, point, controller, solver, estimator, concurrency or stop-tree
change after the R344 seal or after any claim-bearing outcome is visible.

## Cross-references

- `memory/claims/CLM-0900.md`
- `memory/questions/Q-0090.md`
- `paper/decoupling_marl_model_first/reports/R341.md`
