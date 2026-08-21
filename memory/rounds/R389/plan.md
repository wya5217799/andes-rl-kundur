---
round: R389
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R389 plan — stock REGF2 object and clean-initialization gate

**Opened**: 2026-08-14
**Driver**: R388 validly stops the exact REGCV1/card/port formulation; the validated route census selects stock REGF2 as the only materially different installed VSM successor eligible for one upstream no-action gate.
**Parent**: CLM-1085; Q-0107; `paper/converter_vsg_pq_decoupling/working/route_contract.md#regf2-successor-decision`; `paper/converter_vsg_pq_decoupling/working/REGF2_successor_route_audit.md`

## TL;DR

On unchanged ANDES 2.0.0 Kundur static topology, construct exactly four stock REGF2 VSM devices and ask only whether the object is structurally clean, initializes natively, and completes a 0.2-s zero-input trajectory inside prospectively frozen diagnostics and electrical guards. No action, controller, disturbance, or training is permitted; valid failure stops stock REGF2 before authority testing.

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0106 closed-negative @ R388, by CLM-1085 — Do one-device-at-a-time signed Pref and Qref steps on the structurally clean four-REGCV1 Kundur object produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure?
- Q-0105 closed-positive @ R386, by CLM-1075 — Can the same four-device REGCV1 card pass native initialization and a zero-input short TDS when the unchanged packaged Kundur static tables are reconstructed with no legacy synchronous-machine, governor, or exciter records?
- Q-0104 closed-negative @ R384, by CLM-1065 — Can four ANDES REGCV1 converter-level VSG devices replace the four dynamic generator chains on the unchanged Kundur network, preserve exact one-to-one static-generator ownership and mutable Pref/Qref interfaces, and complete zero-input initialization and short TDS without numerical drift or non-finite electrical variables?

## Methodology

### Confirmed public seams and TDD order

1. **Builder seam**: a public REGF2 Kundur builder accepts the packaged XLSX/JSON sources and an output path, then returns a source/derived identity manifest. Tests first require deterministic static-table identity, exact four-device mapping/card, required PLL inventory, and structural absence.
2. **Classifier seam**: a pure contract builder and record classifier accept canonical mappings and return exactly PASS, scientific STOP, or ANALYSIS-INVALID. Vertical red-green slices cover provenance/schema invalidity before scientific branches.
3. **Lifecycle seam**: one self-documenting CLI exposes only `rehearse`, `prepare`, and `execute --expected-seal-sha256`. Tests observe setup-only rehearsal, source-bound seal, create-only routing, and immutable artifact identities through this interface.

These are the same three public boundaries used successfully by R384--R388; the user's instruction to continue under the existing plan confirms reuse of these seams. Tests do not mock internal repository modules; ANDES itself is isolated only at the external-runtime boundary for Windows unit tests.

### Frozen scientific object

- ANDES 2.0.0 WSL runtime and packaged Kundur XLSX/JSON static source.
- Deterministic static-only projection with exact `Bus/PQ/PV/Slack/Line/Area` tables and unchanged 10-bus/15-line connectivity.
- Four active REGF2 devices mapped `(REGF2_1, bus 1, gen 1)` through `(REGF2_4, bus 4, gen 4)` with `Sn=900.0` MVA.
- Every other explicit parameter equals the installed ANDES 2.0.0 REGF2 default and is serialized in the contract: `rf=0`, `xf=0.2`, `Vdip=0.8`, `Tfrz=0`, `PQFLAG=1`, `fn=60`, `dwmax=75`, `dwmin=-75`, `wdrp=0.033`, `Qdrp=0.045`, `Tr=0.005`, `Te=0.005`, `KPi=0.5`, `KIi=20`, `KPv=3`, `KIv=10`, `Pmax=1`, `Pmin=-1`, `KPplim=5`, `KIplim=30`, `Qmax=1`, `Qmin=-1`, `KPqlim=0.1`, `KIqlim=1.5`, `Tpm=0.025`, `gammap=1`, `gammaq=1`, `mf=0.15`, `dd=0.11`, and auto-found PLL linkage. The record separately seals this input card and the deterministic setup-time system-base representation (`xf=0.2*100/900`, `Pmax/Qmax=9`, `Pmin/Qmin=-9`; all other fields unchanged), so unit conversion is not mistaken for parameter drift.
- Installed source hashes are frozen for `regf1.py` and `regf2.py`; forbidden device/DAE tokens include REGCV1, REGCV2, REGF1, REGF3, GENROU, TGOV1, EXDC2, and event models.

### Single formal trajectory

1. Build and set up a fresh system; run power flow.
2. Capture the linked static-generator P/Q source immediately after power flow and before TDS initialization.
3. Run native TDS initialization; capture solver/test flags, every nonzero or non-finite residual row, bad residual indices, clamped-limit rows, and complete finite-value status.
4. Apply no post-init Pref/Qref/Paux/Qaux write and no disturbance. Capture a complete time-zero snapshot, run native TDS to 0.2 s at tolerance `1e-4`, and archive the complete native trace.
5. Require exact mapping and source/reference preservation at `1e-12`; zero bad initialization residuals at absolute threshold `1e-6`; finite DAE and REGF2 values; bus voltage `[0.9,1.1]` pu; current magnitude at most `10.0` pu; apparent power at most `9.0` system pu; virtual frequency `[0.95,1.05]` pu; and maximum Pe/Qe/bus-voltage zero-input drift at most `2e-4` pu.

No early scientific counterexample shortcut is needed because there is one job. The unique formal attempt is preserved even on failure; no in-round retry or parameter adjustment is authorized.

## Gate

- `REGF2-OBJECT-INIT-PASS`: complete provenance/schema; exact source, topology, mapping, card, PLL inventory, structural absence, and references; native power flow/init/0.2-s completion; zero registered bad residuals; every finite/electrical/drift guard passes.
- `STOP-REGF2-OBJECT-INITIALIZATION`: complete valid evidence but any native initialization/convergence, residual, finite-value, electrical, or drift gate fails. Close Q-0107 negative and stop stock REGF2 before action authority.
- `ANALYSIS-INVALID`: any source/provenance/schema/diagnostic/trace/attempt-accounting defect, unexpected execution exception, or seal mismatch. Preserve artifacts; do not interpret physical values or retry inside R389.
- PASS opens only a new question about the actual post-init REGF2 dynamic signal seam. It does not establish authority, P/Q decoupling, stability, safety, controller value, MARL value, topology generalization, EMT/HIL, or deployment validity.

## Formal launch contract

- `formal_entry`: `scripts/run_r389_regf2_object_init_gate.py`.
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r389_regf2_object_init_gate.py rehearse`.
- `rehearsal_scope`: setup-only construction and schema/provenance inspection; no PFlow, TDS initialization, or physical trajectory.
- `rehearsal_checks`: installed package/version/source hashes; packaged XLSX/JSON equality; deterministic derived-case hash; exact REGF2/card/mapping and required PLL inventory after setup; forbidden model/DAE absence; question/plan authority; output absence; no competing research process; native-thread environment; create-only routing.
- `capacity_evidence`: `memory/rounds/R389/capacity_evidence.json` records host/WSL resources, competing processes, setup-only elapsed time, and the intentional quick-run serial cap.
- `host_process_budget`: 1 WSL Python process, an intentional cap for one dependent trajectory under the user's small-run policy rather than a throughput estimate.
- `wsl_python_processes`: 1 total including launcher/worker accounting.
- `native_threads_per_process`: 1 for OMP, OpenBLAS, MKL, and NumExpr, set before NumPy/ANDES import.
- `other_reserved_processes`: must be measured as zero immediately before seal; otherwise HOLD and do not seal.
- `seal_command`: `/home/wya/andes_venv/bin/python scripts/run_r389_regf2_object_init_gate.py prepare`.
- `seal_path`: `memory/rounds/R389/formal_seal.json`, binding the plan, question, line/route/programme, installed sources, builder/classifier/runner/tests, launcher, dependencies, rehearsal, capacity record, and R388 parent evidence.
- `formal_execute_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r389_regf2_object_init_gate.py execute --expected-seal-sha256 <sha256>`.
- `formal_output`: create-only `results/research_loop/r389_regf2_object_init_gate/` with immutable attempt, execution, analysis, manifest, and whole-file SHA-256 sidecars. Exactly one formal attempt and at most one physical trajectory are permitted.
- Formal execution is expected to be a quick run; seal-time readiness must be `RUN-READY`, with ETA recalibrated from the measured setup-only rehearsal and prior one-trajectory ANDES evidence. Monitor only process state, resource safety, and terminal artifact presence until completion.

## 资产保护契约

- Read/hash only: R384--R388 plans, seals, attempts, results, feeds, claims, questions, REGCV1 sources/tests, packaged ANDES cases, installed ANDES package, and every other manuscript line.
- Add only the REGF2 builder/classifier/runner/tests, R389 lifecycle artifacts, Q-0107 outcome assets, and current-line navigation/feed updates required by the normal close gate.
- Never overwrite the packaged Kundur case; all derived work uses create-only scratch/output paths.
- Do not change network connectivity, static operating data, step magnitude (there is no step), REGF2 parameters after result visibility, thresholds, or resource budget after seal.

## Cross-references

- CLM-1085 and R388: exact REGCV1/card/port signed-authority stop.
- `paper/converter_vsg_pq_decoupling/working/REGF2_successor_route_audit.md`: durable installed-source and 26-episode direction audit; T24 is the sole eligible route.
- Q-0107: sole falsifiable objective.

## Preformal rehearsal correction

The first setup-only rehearsal stopped with no artifacts and no PFlow/TDS. A
minimal probe isolated deterministic 900-MVA device-base to 100-MVA
system-base conversion (`xf 0.2 -> 0.2*100/900`, P/Q limits `+/-1 -> +/-9`)
plus input-binding loss because ANDES mutates `System.add` payloads. The
contract now seals input and runtime cards separately, and the builder copies
bindings before the external call. Regression tests and a second setup-only
probe pass; no scientific parameter, topology, threshold, or budget changed.
