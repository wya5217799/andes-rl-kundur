---
round: R397
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R397 plan — PPVSM1 two-unit signed P/Q authority gate

**Opened**: 2026-08-14
**Driver**: R396/CLM-1125 passes the two-unit PPVSM1 object gate (clean initialization, 0.2-s zero-input stationarity, guarded reduced spectrum) and opens only a signed P/Q authority gate. The PI explicitly authorized this new evidence round in-session on 2026-08-14: mirror the R388 signed-authority bank pattern on the two-unit diagnostic cell and freeze requested/applied/achieved P/Q per device, reusing the R396 runner chain and full-arm rehearsal.
**Parent**: Q-0110; CLM-1125; R396; CLM-1085; R388; CLM-1105; R392; route_contract#ppvsm1-successor-decision; route_contract#r393-r396-ppvsm1-disposition

## TL;DR

工作量：`evidence`。R397 冻结双机 PPVSM1 单元（母线 1-2，母线 3-4 静态锚）上的 9 臂有符号 Pref/Qref 银行：零臂 + 2 机 × pref/qref × 正负号，绝对步长 ±0.09 系统 pu，2 秒时域，全部 R388 科学阈值与电气包络。干预 = 原生 TDS 初始化后对冻结引用服务数组的直接绝对写（与 ANDES RenGen set_setpoint 同机制）。证据 schema 一次到位：显式初始快照、顺序无关母线身份、类型化提前终止分支、signal-major 初始行 + device-major 轨迹行、全局 DAE 地址读变量、record["round"]==contract["round"] 校验。rehearsal 全臂 canary 执行全部 9 臂每个记录步骤（R396 教训），canary 必须 record-integrity 有效（PASS 或 STOP 皆可封存，ANALYSIS-INVALID 阻塞），不绑定科学分支。PASS 关 Q-0111 正并只开 droop-slope 匹配验证新轮；有效负 = STOP，在控制器/解耦/学习工作前停 PPVSM1。附带一项仓库卫生维护（非实验）：根治测试套件运行时 ANDES 输出对仓库根的污染。

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0111 [opened R397] Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Recently Closed (last 3)

- Q-0110 closed-positive @ R396, by CLM-1125 — Does the projected-passive dual-droop VSM (PPVSM1) two-unit diagnostic cell pass clean native initialization, a 0.2-second zero-input stationarity gate, and a spectrum guard with no positive-real mode and no neutral degeneracy beyond the network common-angle reference, thereby opening only a separately registered signed P/Q authority gate?
- Q-0109 closed-positive @ R392, by CLM-1105 — Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?
- Q-0108 closed-positive @ R391, by CLM-1100 — Does the exact R389 four-REGF2 equilibrium contain a finite, numerically resolved positive-real mode in the ANDES reduced state matrix that reproduces across two independently initialized numerical arms without advancing simulation time?

## Methodology

### Single falsifiable objective

Determine whether the frozen two-unit PPVSM1 cell produces correctly applied, signed, target-attributed active and reactive power responses to per-device signed Pref/Qref steps across all nine registered arms without solver, electrical, or record-integrity failure.

### Immutable scientific contract

- Reuse R396's exact construction: ANDES 2.0.0, packaged/derived Kundur static case (10-bus, 15-line), two PPVSM1 devices (idx PPVSM1_1/PPVSM1_2, bus=gen=1/2), StaticGen 3-4 static anchors, 900-MVA device rating, 100-MVA system base, frozen PPVSM1 card (fn=60, mf=0.15, wdrp=0.033, Qdrp=0.045, krho=20, rho_rate_max=10, KPv=3, KIv=10, KPi=0.5, KIi=20, Te=0.005, rf=0, xf=0.2 device base, Rv=0.05 system base, P/Q limits ±1 device base, dw ±75), forbidden models absent, no PLL, static tables and connectivity unchanged.
- Execute exactly 9 ordered fresh-system arms: zero, then PPVSM1_1 pref/qref negative/positive, then PPVSM1_2 pref/qref negative/positive. Post-init absolute setpoint step delta=±0.09 system pu; requested/applied tolerance 1e-12; tf=2.0 s; native TDS tolerance 1e-4.
- Channels: pref→Pe (cross-output Qe), qref→Qe (cross-output Pe). Achieved response = terminal value minus zero-arm terminal value per device.
- Frozen guards (R388 bank envelope): signed floor 2e-4; target-attribution floor 2e-4; paired-separation floor 4e-4; bus voltage [0.9,1.1] pu; current magnitude ≤10 pu; apparent power ≤9 system pu (900/100); virtual frequency [0.95,1.05] pu.
- Intervention mechanism: after successful native TDS init, write the target channel's frozen reference service array element (system.PPVSM1.Pref.v[uid] / Qref.v[uid]) to pre_value + delta; record pre/post readbacks of all four device-channel values; StaticGen p/q tables are never written.
- Evidence schema (R388-corrected + R393-R396 lessons in one first attempt): complete initial snapshot at t=0 (signal-major devices {Pe,Qe,Id,Iq,virtual_frequency}); post-start native samples strictly increasing with first sample in (0, 1/30+tol]; converged-but-short trajectory = invalid; advanced nonconverged terminal < horizon−tol typed "TDS terminated before horizon"; no-advance typed "TDS did not advance"; bus identity exact key set {1..10} independent of JSON order; variables read from global DAE vectors by global addresses; classifier validates record["round"]==contract["round"]; trace rows device-major.
- One serial create-only formal attempt; no retry, tuning, controller, training, topology/card/threshold/horizon change, or model substitution.

### Classification and stopping

- PPVSM1-SIGNED-AUTHORITY-PASS: complete bank integrity and all ten checks true (record_integrity, reference_preservation, initialization_diagnostics_zero, native_solver, finite_values, electrical_envelope, action_identity, signed_self_response, target_attribution, paired_separation). Closes Q-0111 positive; opens only a separately registered droop-slope matching verification.
- STOP-PPVSM1-SIGNED-AUTHORITY: record integrity valid but at least one scientific check false. Closes Q-0111 negative; stops the PPVSM1 formulation before any controller, decoupling, or learning work.
- ANALYSIS-INVALID: any source, contract, provenance, schema, capture, diagnostic, arm-count/order, unexpected-exception, or create-only defect. Preserve the attempt; do not retry R397; only a separately authorized science-identical instrumentation correction may follow.

### Outcomes (pre-registered, identical meanings to R388)

- Zero arm completes 2.0 s with native convergence and stays inside every guard -> bank admissible; any zero-arm solver/electrical failure -> STOP.
- Each action arm: requested/applied equality within 1e-12 and no non-commanded channel change -> action identity passes.
- Achieved target response sign matches requested sign with |response| >= 2e-4 -> signed_self_response passes.
- |target| - max non-target >= 2e-4 -> target_attribution passes; positive minus negative separation >= 4e-4 -> paired_separation passes.
- All ten checks pass -> PPVSM1-SIGNED-AUTHORITY-PASS (opens only the droop-slope matching verification); any science check false with valid integrity -> STOP-PPVSM1-SIGNED-AUTHORITY (stops the formulation before controller/decoupling/learning work).

### TDD, review, and execution discipline

- Classifier first (pure module, no ANDES import): contract equivalence, arm/record schemas, failure sentinels (pflow, init, no-advance, partial), action receipts, response rows, paired separation, electrical/finite checks, all three classifications, adversarial malformed/duplicated/missing-identity records. Then the runner and its create-only rehearse/prepare/execute tests. Focused tests pass on Windows (classifier pure) and WSL (runner tests use fake builders where possible).
- Before any rehearsal or seal: focused/inherited tests, repository health, round preflight, and a two-axis (Standards + Spec) code review of the R397 diff; clear every launch blocker.
- Rehearsal runs the complete nine-arm bank as a canary through the formal runner's own arm path (build, setup, PFlow, init, diagnostics, reference capture, initial snapshot, setpoint write, TDS, trace capture, classifier pre-check) without creating any formal attempt or result; a canary classification of ANALYSIS-INVALID blocks the seal; the canary does not bind which scientific branch the formal attempt records.
- The formal bank is small; one WSL Python process, one native thread per process.

### 仓库卫生维护（本轮附带，非实验）

- 事实：WSL 全量套件从仓库根运行时，真实 ANDES 测试（已确认 tests/test_v4_env_regression.py 污染；r328/r330/r356/r357 与 launcher/qp/r334/r353-355/r358 两簇复现 clean）把 kundur_full_out.{lst,npz,txt} 写进仓库根，导致 test_real_checkout_passes_repository_health_cli 失败（交接文档误判为 ARTIFACTS 注册未生效）。其余 12 个失败为其他线所有的既有失败，不在本轮范围。
- 修复（只动测试面，不触碰 paper-cited 资产 base_env.py/andes_vsg_env_v4.py/train.py/paper_grade_axes.py）：已确认污染测试加 cwd 隔离（monkeypatch.chdir(tmp_path)）；conftest 增加 autouse teardown fixture，仅删除仓库根下恰好三个 kundur_full_out.* 文件名，把"仓库根永不留 kundur_full_out.*"codify 进套件 seam。
- 验证：修复后污染测试不再产生根污染；close 时全量套件运行后 test_real_checkout 必须绿、仓库根无 kundur_full_out.*。

## Formal launch contract

- formal_entry: scripts/run_r397_ppvsm1_signed_authority_gate.py
- rehearsal_command: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r397_ppvsm1_signed_authority_gate.py rehearse
- rehearsal_scope: same-pre-attempt-path; complete nine-arm scientific canary through the formal runner path (build, setup, PFlow, init, diagnostics, reference capture, initial snapshot, setpoint write, TDS, trace capture, classifier pre-check), no formal attempt or result artifact created, formal output absence enforced
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, installed_cases, static_table_identity, derived_case_determinism, structural_absence, setup_only_canary, full_bank_canary, output_absence, question_in_flight, active_plan, no_competing_research_process, physical_trajectory_executed=false
- capacity_evidence: memory/rounds/R397/capacity_evidence.json
- host_process_budget: 1
- wsl_python_processes: 1
- native_threads_per_process: 1
- other_reserved_processes: 0

One WSL Python formal process runs the serial nine-arm bank; native numerical library threads are pinned to 1; competing research processes are measured immediately before seal and required 0.

- seal_command: /home/wya/andes_venv/bin/python scripts/run_r397_ppvsm1_signed_authority_gate.py prepare
- seal_path: memory/rounds/R397/formal_seal.json
- formal_execute_command: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r397_ppvsm1_signed_authority_gate.py execute --expected-seal-sha256 <sha256>
- formal_output: create-only results/research_loop/r397_ppvsm1_signed_authority_gate/
- completion: one immutable execution, analysis, and manifest
- retry: none automatically; post-seal defects require a separately authorized successor

## Gate

Exactly the three classifications defined above; integrity precedes science. Formal output is never reclassified by editing the sealed classifier, contract, or record.

## 资产保护契约

- Immutable: every R383-R396 seal, record, feed, claim, verdict, sidecar, source file, and measured value; the PPVSM1 model (ppvsm1.py), builder (ppvsm1_static_kundur.py), object-gate classifier, and frozen card remain byte-identical; packaged cases/installation; Kundur connectivity; prior manuscript lines, checkpoints, and results.
- New/modified before seal: this R397 plan, Q-0111, R397-only classifier/runner/tests, rehearsal/capacity records, the conftest hygiene backstop, the test_v4_env_regression.py cwd isolation, and navigation hashes. R396 code and artifacts remain byte-identical.
- New after seal: exactly one create-only R397 formal root, then the normal feed/claim/verdict/report/manifest/navigation close-out.
- Forbidden: importing R396 measurements as R397 evidence; R393-R395/R396 retry or reinterpretation; threshold/card/step/horizon changes; controller, training, topology/model substitution; scientific claims from an invalid record.

## Cross-references

- CLM-1125 / R396: parent object pass; supplies the frozen object and the runner chain.
- CLM-1085 / R388: the bank pattern being mirrored; Q-0106 closed negative there for the four-REGCV1 formulation only.
- CLM-1105 / R392: stop rationale for stock REGF2; PPVSM1 is the PI-authorized redesign.
- Q-0110 / Q-0111; route_contract.md#ppvsm1-successor-decision, #r393-r396-ppvsm1-disposition, #survey-conformance.
