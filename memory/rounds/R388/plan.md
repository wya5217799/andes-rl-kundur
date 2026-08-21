---
round: R388
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R388 plan — integrity-corrected REGCV1 signed-authority gate

**Opened**: 2026-08-14
**Driver**: R387's sole sealed attempt is analysis-invalid because its evidence schema confuses JSON mapping order with bus identity, omits a separate initial snapshot, and has no typed branch for an advanced partial native trajectory; repair only those three integrity defects without changing the scientific experiment.
**Parent**: Q-0106; CLM-1080; R387; CLM-1075; R386; ADR-0017

## TL;DR

工作量：`evidence`。R388 是 R387 唯一获准的完整性修复轮，不重试或重解释
R387。保持 ANDES 2.0.0、Kundur 拓扑、四台 REGCV1、参数卡、17 臂顺序、
`0.09 pu` 步长、2 秒时域、全部科学阈值、电气边界、串行资源和禁用训练完全
不变。只把母线身份改为集合等价，单独封存零时刻完整信号快照，并把已推进但
提前结束且原生不收敛的完整部分轨迹表示为科学停止候选。模式或证据仍有缺陷
则分析无效且不重跑；有效负结果停止当前 REGCV1 方案。

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

Determine whether the unchanged R387 17-arm signed Pref/Qref experiment can
produce an admissible scientific classification once, and only once, the three
registered measurement/classification defects are corrected prospectively.

### Immutable scientific contract

- Reuse R387's exact ANDES 2.0.0 installation, packaged Kundur XLSX/JSON static
  tables, static-only derived object, network connectivity, four-device
  `(REGCV1_i,bus=i,gen=i)` mapping, 900-MVA ratings, REGCV1 parameter card,
  PFlow/reference/init/action ordering, and structural-absence guards.
- Reuse the exact ordered 17 fresh-system arms: zero, then devices `1..4`,
  channels `pref,qref`, signs `negative,positive`. Apply the same post-init
  absolute setpoint step `delta=+/-0.09` system pu, with requested/applied
  tolerance `1e-12`, `tf=2.0 s`, and native TDS tolerance `1e-4`.
- Reuse without change the signed floor `2e-4`, target-attribution floor
  `2e-4`, paired-separation floor `4e-4`, bus-voltage `[0.9,1.1]`, current
  magnitude `<=10`, apparent power `<=9` system pu, and omega `[0.95,1.05]`.
  No controller, feedback, reward, training, retry, topology/card/threshold
  change, or model substitution is permitted.
- A contract-equivalence test must compare every scientific field above with
  R387. R388 may differ only in lifecycle identity, parent/provenance fields,
  and the following evidence-schema fields.

### Three integrity-only corrections

1. Validate voltage-trace bus identity as the exact frozen key set
   `{1,...,10}`, independent of JSON mapping order. Duplicated, missing, or
   substituted identities remain invalid.
2. After successful native TDS initialization and before the setpoint write,
   serialize `trajectory_start_time_seconds=0.0` plus a complete initial
   snapshot for every bus voltage and every REGCV1 `Pe,Qe,Id,Iq,omega` value.
   Store native time-series rows separately as strictly increasing post-start
   samples. The first native sample must be positive and no later than
   `1/30 + 1e-4 s`; a complete arm's final sample must equal `2.0 s` within
   `1e-4`.
3. If native TDS advances beyond zero, returns with `tds_converged=false`, and
   terminates strictly before `2.0-1e-4 s`, serialize the complete available
   trace and the exact typed error `TDS terminated before horizon`. The last
   stored sample must equal the recorded terminal time; this is a valid
   scientific STOP candidate. An exception, non-increasing/misaligned trace,
   converged-but-short trajectory, missing initial snapshot, or polluted
   sentinel is analysis-invalid.

### Classification and stopping

- `REGCV1-SIGNED-AUTHORITY-PASS` requires the same complete scientific checks
  as R387 across all 17 arms. It opens only a separately registered
  deterministic P/Q-decoupling question.
- `STOP-REGCV1-SIGNED-AUTHORITY` requires record integrity but at least one
  native solver, electrical, action identity, signed response, attribution, or
  paired-separation failure. Close Q-0106 negative and stop this REGCV1
  formulation without tuning or training.
- `ANALYSIS-INVALID` has precedence for any source, contract, provenance,
  schema, capture, diagnostic, arm-count/order, unexpected-exception, or
  create-only defect. Preserve the attempt; do not retry R388.

### TDD, review, and execution discipline

- First demonstrate failing regression tests for canonical JSON round-trip,
  separate initial capture/native first-sample timing, and advanced partial
  native termination. Add adversarial missing/substituted identity and
  malformed-partial tests. Then implement only the R388 classifier/runner
  seams, leaving the sealed R387 sources and artifacts unchanged.
- Before any rehearsal or seal, run focused/inherited tests, repository health,
  round preflight, and independent parallel Standards and Spec reviews; clear
  every launch blocker. Rehearsal is setup-only and may not call PFlow or TDS.
- The formal bank is small, so use one WSL Python process and one native thread;
  multiprocess startup overhead is not justified. Seal once and execute exactly
  one create-only formal attempt.

## Formal launch contract

- `formal_entry`: `scripts/run_r388_regcv1_signed_authority_correction_gate.py`.
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r388_regcv1_signed_authority_correction_gate.py rehearse`.
- `rehearsal_scope`: `same-pre-attempt-path`; one representative clean object,
  setup-only, no PFlow/TDS call, and `physical_trajectory_executed=false`.
- `rehearsal_checks`: `source_hash`, `parent_hash`, `installed_package`,
  `installed_cases`, `static_table_identity`, `derived_case_determinism`,
  `structural_absence`, `setup_only_canary`, `output_absence`,
  `question_in_flight`, `active_plan`, `no_competing_research_process`, and
  `physical_trajectory_executed=false`.
- `capacity_evidence`: `memory/rounds/R388/capacity_evidence.json`.
- `host_process_budget`: 1; `wsl_python_processes`: 1;
  `native_threads_per_process`: 1; `other_reserved_processes`: 0.
- `seal_command`: `/home/wya/andes_venv/bin/python scripts/run_r388_regcv1_signed_authority_correction_gate.py prepare`.
- `seal_path`: `memory/rounds/R388/formal_seal.json`; it binds rehearsal,
  capacity, contract, sources, parents, runtime, cases, and derived case before
  any formal output exists.
- `formal_execute_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r388_regcv1_signed_authority_correction_gate.py execute --expected-seal-sha256 <sha256>`.
- `formal_output`: create-only
  `results/research_loop/r388_regcv1_signed_authority_correction_gate/`; exactly
  one 17-arm attempt, no overwrite, retry, or partial-bank substitution.

## Gate

- PASS, STOP, and INVALID are exactly the three classifications defined above;
  integrity precedes science. Formal output is never reclassified by editing
  the sealed classifier, contract, or record.

## 资产保护契约

- Immutable: every R383-R387 seal, record, feed, claim, verdict, sidecar, source
  file, and measured value; packaged cases/installation; Kundur connectivity;
  REGCV1 card; prior manuscript lines, checkpoints, and results.
- New/modified before seal: this R388 plan, R388-only classifier, runner, tests,
  setup-only rehearsal/capacity records, and navigation hashes. R387 code and
  artifacts remain byte-identical.
- New after seal: exactly one create-only R388 formal root, then the normal
  feed/claim/verdict/report/manifest/navigation close-out.
- Forbidden: importing R387 measurements as R388 evidence, R387 retry or
  reinterpretation, threshold/card/step/horizon changes, controller, training,
  topology/model substitution, or scientific claims from an invalid record.

## Cross-references

- CLM-1080 / R387: analysis-invalid result and exact three-defect diagnosis;
  supplies only the correction rationale, not scientific evidence.
- CLM-1075 / R386: valid clean-object construction and initialization parent.
- Q-0106 / ADR-0017: same-object signed per-device authority question and
  structural-absence route boundary.
