---
round: R387
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R387 plan — signed per-device REGCV1 Pref/Qref authority

**Opened**: 2026-08-14
**Driver**: R386 establishes a valid clean four-REGCV1 zero-input object but not dynamic actuator authority; execute the smallest prospective bank that separates requested, applied, and achieved P/Q for every device and input sign.
**Parent**: Q-0106; CLM-1075; R386; ADR-0017

## TL;DR

工作量：`evidence`。保持 ANDES 2.0.0、Kundur 静态网络、四台 REGCV1、
参数卡和初始化顺序不变；串行执行 17 条独立轨迹：一条零输入参考，以及
四台设备的有功、无功参考各自正负一步。每步为系统基准 `0.09 pu`，在初始化
成功后施加，运行 2 秒。严格区分请求、写入回读和实际 P/Q 响应，并检查
动作身份、响应符号、目标归属、求解器、电压、电流、容量和转速。通过只开放
另轮确定性解耦设计；有效负结果停止当前 REGCV1 方案；无效记录不准本轮重跑。

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0106 [opened R387] Do one-device-at-a-time signed Pref and Qref steps on the structurally clean four-REGCV1 Kundur object produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure?

## Recently Closed (last 3)

- Q-0105 closed-positive @ R386, by CLM-1075 — Can the same four-device REGCV1 card pass native initialization and a zero-input short TDS when the unchanged packaged Kundur static tables are reconstructed with no legacy synchronous-machine, governor, or exciter records?
- Q-0104 closed-negative @ R384, by CLM-1065 — Can four ANDES REGCV1 converter-level VSG devices replace the four dynamic generator chains on the unchanged Kundur network, preserve exact one-to-one static-generator ownership and mutable Pref/Qref interfaces, and complete zero-input initialization and short TDS without numerical drift or non-finite electrical variables?
- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?

## Methodology

### Single falsifiable objective

Determine whether every one of the four structurally clean REGCV1 devices has
independently signed and correctly attributed dynamic authority through its
own `Pref` and `Qref` interface, before any controller or learning mechanism is
introduced.

### Frozen object and intervention bank

- Reuse the R386 construction implementation, not its measured values. Keep
  ANDES 2.0.0, the exact packaged Kundur XLSX/JSON static tables, static-only
  projection, network connectivity, `(REGCV1_i,bus=i,gen=i)` mapping, 900-MVA
  ratings, parameter card, post-PFlow/pre-TDS-init reference capture, structural
  absence checks, and initialization diagnostics unchanged.
- Create one fresh system per arm. The exact deterministic order is one
  zero-step reference followed by device index `1..4`, channel order
  `pref,qref`, and sign order `negative,positive`: 17 independent trajectories.
- Apply a single absolute setpoint step immediately after successful native
  TDS initialization and before `TDS.run()`. The signed increment is
  `delta=0.09` system-base per unit for both channels, exactly 1% of each
  900-MVA device rating on the 100-MVA system base. No event, controller,
  feedback, reward, or training enters any arm.
- Freeze `tf=2.0 s` and native TDS tolerance `1e-4`. This horizon spans 200
  converter lag constants (`Tc=0.01 s`) and 0.2 virtual-inertia constants
  (`M=10 s`); it tests distinguishable initial dynamic authority, not settling,
  steady-state tracking, or P/Q decoupling.

### Requested, applied, and achieved estimands

- Before the intervention, snapshot all eight `(device, pref/qref)` setpoints.
  Record the target baseline, signed requested increment, requested absolute
  setpoint, applied target readback, and all eight post-write readbacks.
- Require target requested/applied equality within `1e-12` absolute and every
  non-commanded device-channel setpoint unchanged within `1e-12`. A write that
  changes another setpoint is action-identity leakage regardless of achieved
  electrical response.
- Map `pref -> Pe` and `qref -> Qe`. For every action arm, define achieved
  terminal responses as its four-device terminal powers minus the zero-step
  arm's corresponding terminal powers. The target response is the entry for
  the commanded device; non-target responses are the other three entries.
- Freeze `authority_abs_floor=2e-4` system pu, twice the native solver
  tolerance. Require `sign * target_response >= authority_abs_floor` and
  `abs(target_response) - max(abs(non_target_responses)) >=
  authority_abs_floor`. For each device/channel pair, require positive-minus-
  negative target separation at least `4e-4`.
- Record the target device's cross-channel terminal response (`Qe` under a
  `Pref` step; `Pe` under a `Qref` step), all cross-device same- and
  cross-channel responses, and trajectory extrema. These values are descriptive
  only in R387 and cannot support a decoupling claim or threshold selection.

### Solver and electrical guards

- Every arm must pass setup, PFlow, native TDS initialization/test, zero
  non-tolerance initialization residuals, zero clamped-limit rows, structural
  absence, complete time advancement to `2.0 s`, native convergence, and exact
  reference-source preservation. All 17 ordered arms must be attempted and
  recorded. An executed count below 17 is admissible only when every
  unexecuted arm contains an exact, schema-valid expected native PFlow,
  TDS-initialization, or no-time-advance failure sentinel; it then forces
  scientific STOP. Any missing/duplicated arm, unexplained absent trajectory,
  or malformed sentinel is analysis-invalid.
- Serialize the stored time grid plus trajectory extrema. Require all stored
  DAE states/algebraics and final REGCV1 values finite; every bus voltage in
  `[0.9,1.1] pu`; every REGCV1 current magnitude
  `sqrt(Id^2+Iq^2) <= 10.0 pu`; apparent power
  `sqrt(Pe^2+Qe^2) <= Sn/system_mva_base`; and virtual speed
  `omega in [0.95,1.05] pu` throughout every executed trajectory.
- The current limit equals the 900-MVA rating divided by the 100-MVA system
  base and the registered 0.9-pu minimum voltage. These guards prevent a
  numerical response from being accepted when it leaves the registered
  electrical envelope; they do not certify protection or hardware safety.

### Integrity, stopping, and vulnerability ledger

- Seal the exact contract, runner, classifier, reused construction/runtime
  dependencies, focused tests, plan, question, parent evidence hashes,
  installed ANDES/REGCV1 source, packaged cases, setup-only rehearsal, and
  capacity record before the formal attempt. Formal output is create-only.
- Schema, provenance, contract-digest, source, arm-order/count, diagnostic,
  time-series capture, or unexpected execution defects take precedence as
  `ANALYSIS-INVALID`. Expected complete scientific guard failures become
  `STOP-REGCV1-SIGNED-AUTHORITY`.
- The zero arm protects against natural drift; both signs protect against
  direction-specific or monotone bias; fresh systems protect against state
  carry-over; all-eight-setpoint snapshots protect against software identity
  leakage; target-minus-nontarget response protects against mistaking network
  propagation for local authority; fixed pre-outcome thresholds protect
  against post-hoc pass construction.
- Residual vulnerability: a 2-s terminal endpoint does not prove settling,
  linearity, global operating-range authority, decoupling, robustness,
  stability, EMT fidelity, or deployment. These claims remain forbidden.
- One formal attempt only. A valid negative stops this REGCV1 formulation. An
  invalid or anomalous outcome triggers the registered strict diagnostic loop
  but no R387 rerun; any repaired execution requires a separately authorized
  successor.

### TDD and review gate

- Public seams are fixed before tests:
  `build_signed_authority_contract()`,
  `apply_regcv1_setpoint_step(system, arm)`, and
  `classify_regcv1_signed_authority_record(record, contract=...)`, plus a
  runner exposing only `rehearse`, `prepare`, and `execute`.
- First write failing tests for exact 17-arm construction, one-target-only
  readback, signed/attributed pass, paired separation, electrical failure,
  malformed/missing/duplicated arms, provenance drift, and create-only routing.
  Then implement the smallest vertical slices and run focused tests.
- Before rehearsal, run independent Standards and Spec reviews in parallel and
  clear every launch blocker. Rehearsal may construct and call `setup()` on one
  representative system but must not call PFlow or any TDS method.

### Resource contract

- The bank is small and sequential dependencies are negligible inside one
  process. Use one WSL Python process and one native numerical thread; process
  startup and repeated case import make a capacity ladder or multi-process
  bank more costly than useful for 17 short trajectories.
- Rehearsal records host/WSL memory, disk, competing research processes,
  source/parent/runtime hashes, static-table identity, derived-case
  determinism, structural absence, setup-only construction, and absence of a
  formal output root. It records the process budget without physical execution.
- Formal output is create-only under
  `results/research_loop/r387_regcv1_signed_authority_gate/`.

## Formal launch contract

- `formal_entry`: `scripts/run_r387_regcv1_signed_authority_gate.py`.
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r387_regcv1_signed_authority_gate.py rehearse`.
- `rehearsal_scope`: `same-pre-attempt-path`; one representative clean object,
  setup-only, no PFlow or TDS call, and
  `physical_trajectory_executed=false`.
- `rehearsal_checks`: `source_hash`, `parent_hash`, `installed_package`,
  `installed_cases`, `static_table_identity`, `derived_case_determinism`,
  `structural_absence`, `setup_only_canary`, `output_absence`,
  `question_in_flight`, `active_plan`, `no_competing_research_process`, and
  `physical_trajectory_executed=false`.
- `capacity_evidence`: `memory/rounds/R387/capacity_evidence.json`.
- `host_process_budget`: 1; `wsl_python_processes`: 1;
  `native_threads_per_process`: 1; `other_reserved_processes`: 0.
- `seal_command`: `/home/wya/andes_venv/bin/python scripts/run_r387_regcv1_signed_authority_gate.py prepare`.
- `seal_path`: `memory/rounds/R387/formal_seal.json`; it binds rehearsal,
  capacity evidence, contract, sources, parents, runtime, cases, and derived
  case before any formal attempt exists.
- `formal_execute_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r387_regcv1_signed_authority_gate.py execute --expected-seal-sha256 <sha256>`.
- `formal_output`: create-only
  `results/research_loop/r387_regcv1_signed_authority_gate/`; exactly one
  17-trajectory attempt, no overwrite, retry, post-seal threshold/card change,
  or partial-bank substitution.

## Gate

- `REGCV1-SIGNED-AUTHORITY-PASS`: the complete sealed bank passes provenance,
  source/object/reference/diagnostic, 17-arm solver/electrical, setpoint
  identity, signed target response, target attribution, and paired-separation
  checks. Open only the right to register a separate deterministic P/Q
  decoupling question.
- `STOP-REGCV1-SIGNED-AUTHORITY`: the record is complete and valid but at least
  one scientific solver, electrical, action-identity, signed-response,
  attribution, or paired-separation check fails. Close Q-0106 negative and stop
  this REGCV1 formulation without tuning, model substitution, or training.
- `ANALYSIS-INVALID`: provenance, schema, contract, source, diagnostics, arm
  count/order, unexpected execution, capture, or output integrity fails.
  Preserve the invalid record, run strict diagnosis, and permit no R387 retry
  or scientific conclusion.

## 资产保护契约

- Immutable: all R384-R386 seals, records, feeds, claims, verdicts, sidecars,
  and parent source files; packaged ANDES cases/installation; Kundur topology
  and static data; REGCV1 card; every earlier manuscript line, checkpoint,
  result, and evidence artifact.
- New/modified before seal: Q-0106, R387 plan, programme/line/route navigation,
  R387 classifier, runner, focused tests, setup-only rehearsal, capacity
  evidence, and formal seal.
- New after seal: exactly one create-only formal result root, followed by the
  normal feed/claim/verdict/report/manifest/navigation close-out.
- Forbidden: editing prior-round artifacts, importing prior measured values as
  R387 evidence, post-outcome threshold/card changes, retry, controller,
  feedback law, reward, training, topology/model substitution, or treating
  action readback alone as achieved physical authority.

## Cross-references

- CLM-1075 / R386: clean structural construction, corrected source capture,
  initialization, and zero-input short-run validity; opens only R387.
- CLM-1070 / R385: endpoint-order defect remains analysis-invalid and supplies
  no physical values to R387.
- CLM-1065 / R384: status-disabled legacy-chain formulation remains stopped.
- ADR-0017 / CLM-1060: structural absence stays on this manuscript line with
  unchanged ANDES/Kundur scope and physics-first gate ordering.
