---
line_id: paralleled-vsg-marl
status: active
priority: 1
stage: experiment-side-stopped-no-joint-headroom
artifact_manifest: paper/paralleled_vsg_marl/ARTIFACTS.json
scope:
  write_roots:
    - paper/paralleled_vsg_marl
  shared_read_roots:
    - paper/icems2026
    - paper/decoupling_marl_model_first
    - paper/sci_upgrade_survey
    - memory
    - results
    - docs/research
    - src/andes_rl_kundur
venue:
  kind: conference
  status: shortlisted
  primary: "IEEE PES General Meeting 2027 (provisional; lock owned by author/PI)"
  decision_record: paper/paralleled_vsg_marl/working/venue_decision_2026-08-13.md
  official_source_status: current
  last_checked: 2026-08-13
  review_triggers:
    - after the author/PI states Pass 0 constraints (tier, deadline, fees, article type)
    - after any material change to title, contribution, evidence, or deadlines
    - before venue-specific drafting or submission (Pass 3 refresh)
working_title: "Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning"
title_policy: "Title wording is fixed; every term stays prospective until its gate passes on the same object."
objective: >-
  Build one ANDES experiment with four runtime VSG energy agents, each owning a
  bounded, energy-constrained active-power-reference port; establish a matched
  strong deterministic dynamic-decoupling baseline, then test whether direct
  per-VSG MARL adds coordination value without physical, energy, or
  control-stress harm.
decision_refs:
  - "docs/adr/0015-reset-fixed-title-to-object-matched-line.md#decision"
  - "paper/paralleled_vsg_marl/ROUTE.md#current-gate"
  - "paper/paralleled_vsg_marl/ROUTE.md#reuse-matrix"
  - "paper/paralleled_vsg_marl/working/feasibility_native_four_vsg_contract.md#decision"
evidence_refs:
  - "CLM-0970 -> paper/paralleled_vsg_marl/reports/R364.md"
  - "CLM-0975 -> paper/paralleled_vsg_marl/reports/R365.md"
  - "CLM-0980 -> paper/paralleled_vsg_marl/reports/R366.md"
  - "CLM-0985 -> paper/paralleled_vsg_marl/reports/R368.md"
  - "CLM-0990 -> paper/paralleled_vsg_marl/reports/R369.md"
  - "CLM-0995 -> paper/paralleled_vsg_marl/reports/R370.md"
  - "CLM-1000 -> paper/paralleled_vsg_marl/reports/R371.md"
  - "CLM-1005 -> paper/paralleled_vsg_marl/reports/R372.md"
  - "CLM-1010 -> paper/paralleled_vsg_marl/reports/R373.md"
  - "CLM-1015 -> paper/paralleled_vsg_marl/reports/R374.md"
  - "CLM-1020 -> paper/paralleled_vsg_marl/reports/R375.md"
  - "CLM-1025 -> paper/paralleled_vsg_marl/reports/R376.md"
  - "CLM-1030 -> paper/paralleled_vsg_marl/reports/R377.md"
  - "CLM-1035 -> paper/paralleled_vsg_marl/reports/R378.md"
  - "CLM-1040 -> paper/paralleled_vsg_marl/reports/R379.md"
  - "CLM-1045 -> paper/paralleled_vsg_marl/reports/R380.md"
  - "CLM-1050 -> paper/paralleled_vsg_marl/reports/R381.md"
  - "CLM-1055 -> paper/paralleled_vsg_marl/reports/R382.md"
required_reading:
  - paper/paralleled_vsg_marl/LINE.md
verification:
  - One physical VSG per runtime actor with one independently intervenable action vector; a GFL storage action is not VSG control.
  - The power-reference port belongs to its VSG power balance and energy state with valid units, sign, timing, and achieved-power accounting.
  - Deterministic, random-direct, independent-RL, no-message, and message-enabled MARL comparisons have matched permissions.
  - Old-line results and checkpoints are design inputs only, never evidence for this line.
stop_when:
  - No training or sweeps on the stopped direct per-VSG M/D formulation.
  - Stop the energy-port direction if the physical gate cannot confirm a one-to-one VSG-owned power-reference port.
  - The energy-port formulation must pass object, actuator, deterministic-efficacy, and non-learning headroom gates before any training.
  - Freeze learner capacity, training/tuning, seed/checkpoint, and sealed-evaluation budgets before the MARL comparison becomes identifiable.
  - A failed gate stops that formulation without algorithm sweeps.
  - R375 stops the frozen deterministic power-reference formulation on its held-out physical guard; no retry, gain change, headroom test, or training.
  - R380 stops the registered full-order source-model formulation on sealed trajectory fidelity; no controller design, model retuning, retry, or training.
  - R381 stops the registered two-stage washout formulation at the development gate; no evaluation-bank access, gain/order/corner change, retry, headroom test, or training.
  - R382 separately stops the current power-port MARL experiment route because its bounded outcome-seeing family finds disturbance-only benefit but no joint probe-cross headroom; no information gate, larger oracle family, controller retry, or training.
  - Keep the title fixed as an unsupported target during manuscript closure; do not write MARL, coordination, or positive decoupling claims from this line's evidence.
---

# Fixed-title manuscript line

This file is navigation only.  The route document defines the next gate and
reuse boundary; numerical facts may enter only through claims and bound feeds.
