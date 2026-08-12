---
round: R381
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R381 plan — Gate B-4 cascaded-washout deterministic physical gate

**Opened**: 2026-08-12
**Driver**: Test the single second-order washout mechanism that passed the
scratch offline separation gate, without reopening the stopped first-order
family or changing gains after outcome visibility.
**Parent**: CLM-1040 (R379 first-order stop), CLM-1045 (R380 model-fidelity
stop), `tmp/paralleled-vsg-marl/second-order-washout/offline_gate.json`

## TL;DR

R381 freezes one genuinely higher-order feasibility-native neighbour
controller and compares it with zero and local control on the same four VSG
power-reference ports. Development failure stops the mechanism before the
untouched evaluation bank. A pass authorises only a separately registered
non-learning headroom gate; training, parameter search, and first-order retry
remain forbidden.

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?

## Methodology

### Scientific object and estimand

- Modified-Kundur V4 with four VSG energy units at buses `[12, 16, 14, 15]`;
  legacy M/D path zero; one independently executed feasibility-native scalar
  action per VSG; unchanged energy, ramp, SOC, power, timing, and identity
  guards.
- Estimand: whether this one fixed second-order neighbour controller clears
  deterministic differential-benefit and no-harm gates versus the zero and
  local arms. Because information patterns differ, no filter-order-only,
  architecture-class, or MARL attribution is identified (`QUALIFY`).

### Frozen arms and mechanism

- `zero_feedback`: zero node action.
- `local_feasibility_native`: `kp_n=4.0 /Hz`, `ki_n=0.8 /(Hz*s)`, clip 0.70.
- `distributed_cascaded_hp_damping_ks1_kc0p5_fc0p05_order2`: same local PI
  and dynamic-average common channel; `ks_n=1.0 /Hz`, `kc_n=0.5 /s`; two
  identical discrete washouts in series on the Laplacian frequency message,
  each with `alpha=exp(-2*pi*0.05*0.2)=0.9391013674242926`.
- Exactly one candidate. No gain, corner, order, clip, probe, or arm sweep.
  Controller update 0.2 s, 50 steps, seed 42, nominal endpoint frequency
  60 Hz. The internal historical controller semantics remain separate from
  physical endpoint units.

### Frozen banks

- Development, 30 records: paired action probes in four arithmetic modes at
  magnitude 0.25 under `PQ_Bus15 -0.45`; disturbances `PQ_1 +0.65` and
  `PQ_Bus14 -0.55`; three arms x ten records.
- Evaluation, at most 30 records and only after development eligibility:
  paired probes under `PQ_0 -0.40`; disturbances `PQ_0 +0.60` and
  `PQ_Bus15 +0.55`; same three arms. This bank was not executed by R379.
- Common, inter-area, and two local-area arithmetic coordinates remain endpoint
  views, not asserted eigenmodes.

### Frozen guards, endpoints, and decision tree

- Guards: 50 finite completed steps, no TDS failure, outer projection identity
  at `1e-12`, empty saturation reasons, SOC in `[0.20,0.80]`, zero legacy M/D,
  channel reconstruction, zero-sum differential action, uniform timing, and
  common-plus-three-differential action rank four.
- Primary: mean differential-frequency energy and settling within 0.01 Hz.
  Secondary/no-harm: common IAE, peak, RoCoF, probe off-diagonal energy and
  normalized cross ratio, action variation, headroom, bound contact, and
  projection leakage.
- Development eligibility versus local: differential-energy ratio `<=0.98`;
  settling at least one 0.2 s step faster; common IAE `<=1.05`; both probe
  cross ratios `<=1.10`.
- Evaluation: mean differential-energy ratio `<=0.95` versus zero and local;
  every condition `<=1.10`; settling no worse than either baseline and at
  least 0.2 s faster than local; common IAE `<=1.05` of best; peak/RoCoF and
  both probe cross ratios `<=1.10`.
- Guard failure -> `STOP-UNSAFE-CONTROL`; development failure ->
  `STOP-DEVELOPMENT-NO-CANDIDATE`; held-out primary/common/probe failure ->
  the matching `STOP-*`; all pass -> `DETERMINISTIC-DECOUPLING-PASS`.
- No retry. Any pre-seal engineering failure may be repaired before the seal;
  any post-seal pre-attempt failure aborts the round and requires a successor.

## Formal launch contract

- `formal_entry`: `scripts/run_r381_gate_b4_deterministic.py` through
  `scripts/andes_scratch.py` under WSL ANDES 2.0.0.
- `rehearsal_command`: `/home/wya/andes_venv/bin/python
  scripts/andes_scratch.py scripts/run_r381_gate_b4_deterministic.py
  rehearse` from the WSL-mounted repository root with every native numerical
  thread variable fixed to one.
- `rehearsal_scope`: source/parent hashes, active plan, installed package and
  case hash, capacity, result-root absence, closed contract, and zero physical
  trajectories through the formal entry's pre-attempt path.
- `rehearsal_checks`: all listed checks true and
  `physical_trajectory_executed=false`; rehearsal and source enter the seal.
- `wsl_python_processes`: 1 total (launcher and runner are one replaced process;
  no child or process-pool worker).
- `native_threads_per_process`: 1.
- `capacity_evidence`: R379
  `results/research_loop/r377_gate_b3_deterministic/formal_analysis.json`
  completed the same 60-record, 50-step serial physical workload in
  454.5728820480872 s; R381 has at most 60 records and uses the same simulator,
  plant, port, and output schema. Recheck runtime, free memory/disk, artifact
  projection, and competing processes pre-seal.
- `host_process_budget`: 1, an intentional attempt-level hard cap because this
  bounded run uses the already validated create-only serial runner; parallel
  sharding would add unneeded new isolation/provenance plumbing.
- `other_reserved_processes`: 0; rehearsal and execute fail closed if another
  research Python process is observed.
- ETA: about 455 s from the representative anchor; at most 682 s with the
  preregistered 1.5x safety factor. Monitor only process health, completed
  artifact presence, and resource safety; no intermediate scientific reads.

## Gate

One question: does the single second-order washout neighbour controller turn
the offline frequency-separation result into disturbance-driven differential
benefit without physical, common-mode, probe-cross, energy, or control-stress
harm? Valid STOP outcomes close this formulation. PASS opens only the
non-learning conditional-headroom gate.

## 资产保护契约

- Immutable: R364-R380 plans, seals, source snapshots, results, claims, feeds,
  and verdicts; V4/base environment, action map, energy port, banks, endpoint
  definitions, first-order controller, and old results.
- Allowed additions: R381 controller integration, contract/classifier wrapper,
  runner, focused tests, round artifacts, create-only result root, one feed,
  one claim, verdict, manifest entry, and current-line navigation refresh.
- Formal seal freezes source, parent hashes, contract, thresholds, budgets,
  rehearsal, installed case, and output absence before any trajectory.
- No overwrite, post-seal patch, formal retry, training, random arm, gain
  change, bank resize, threshold change, or manuscript prose.

## Cross-references

- CLM-1040 / R379: first-order family stopped on the development probe-cross
  boundary; development physical records are design inputs only.
- CLM-1045 / R380: full-order source-model formulation stopped before control;
  no model result transfers.
- Offline scratch gate: implementation qualification only; no scientific
  evidence transfer.
