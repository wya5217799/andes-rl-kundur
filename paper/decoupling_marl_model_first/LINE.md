---
line_id: decoupling-marl-model-first
status: frozen
stage: frozen-methodology-evidence-line
artifact_manifest: paper/decoupling_marl_model_first/ARTIFACTS.json
scope:
  write_roots: [paper/decoupling_marl_model_first]
  shared_read_roots: [memory, results, docs/research, src/andes_rl_kundur]
venue:
  kind: conference
  status: unassessed
  primary: To be selected
  decision_record: paper/decoupling_marl_model_first/working/model_contract.md
  official_source_status: unverified
  last_checked: null
  review_triggers: [before venue-specific framing, before manuscript drafting]
working_title: "Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning"
title_policy: "Wording fixed by PI on 2026-08-03; unchanged wording does not validate title terms before their registered gates pass."
objective: >-
  Preserve the implementation-faithful model, actuator, information,
  deterministic-control, and residual-headroom gates as read-only methodology
  evidence. The line establishes a bounded centralized deterministic
  storage-power-control gain, but no incremental learned-controller or MARL
  gain.
decision_refs:
  - "docs/adr/0015-reset-fixed-title-to-object-matched-line.md#decision"
  - "paper/decoupling_marl_model_first/working/model_contract.md#research-objective"
  - "paper/decoupling_marl_model_first/working/model_contract.md#equation-to-implementation-reconciliation"
  - "paper/decoupling_marl_model_first/working/model_contract.md#stage-0-and-stage-1-non-learning-probe-contract"
  - "paper/decoupling_marl_model_first/working/model_contract.md#training-and-eval-gates"
evidence_refs:
  - "CLM-0740 -> paper/decoupling_marl_model_first/reports/R306.md"
  - "CLM-0745 -> paper/decoupling_marl_model_first/reports/R307.md"
  - "CLM-0750 -> paper/decoupling_marl_model_first/reports/R308.md"
  - "CLM-0755 -> paper/decoupling_marl_model_first/reports/R309.md"
  - "CLM-0760 -> paper/decoupling_marl_model_first/reports/R310.md"
  - "CLM-0765 -> paper/decoupling_marl_model_first/reports/R311.md"
  - "CLM-0770 -> paper/decoupling_marl_model_first/reports/R312.md"
  - "CLM-0775 -> paper/decoupling_marl_model_first/reports/R313.md"
  - "CLM-0780 -> paper/decoupling_marl_model_first/reports/R314.md"
  - "CLM-0785 -> paper/decoupling_marl_model_first/reports/R315.md"
  - "CLM-0790 -> paper/decoupling_marl_model_first/reports/R316.md"
  - "CLM-0795 -> paper/decoupling_marl_model_first/reports/R317.md"
  - "CLM-0800 -> paper/decoupling_marl_model_first/reports/R318.md"
  - "CLM-0805 -> paper/decoupling_marl_model_first/reports/R319.md"
  - "CLM-0810 -> paper/decoupling_marl_model_first/reports/R320.md"
  - "CLM-0815 -> paper/decoupling_marl_model_first/reports/R321.md"
  - "CLM-0820 -> paper/decoupling_marl_model_first/reports/R322.md"
  - "CLM-0825 -> paper/decoupling_marl_model_first/reports/R323.md"
  - "CLM-0830 -> paper/decoupling_marl_model_first/reports/R324.md"
  - "CLM-0835 -> paper/decoupling_marl_model_first/reports/R325.md"
  - "CLM-0840 -> paper/decoupling_marl_model_first/reports/R326.md"
  - "CLM-0845 -> paper/decoupling_marl_model_first/reports/R327.md"
  - "CLM-0850 -> paper/decoupling_marl_model_first/reports/R328.md"
  - "CLM-0855 -> paper/decoupling_marl_model_first/reports/R329.md"
  - "CLM-0860 -> paper/decoupling_marl_model_first/reports/R330.md"
  - "CLM-0865 -> paper/decoupling_marl_model_first/reports/R331.md"
  - "CLM-0870 -> paper/decoupling_marl_model_first/reports/R332.md"
  - "CLM-0875 -> paper/decoupling_marl_model_first/reports/R333.md"
  - "CLM-0880 -> paper/decoupling_marl_model_first/reports/R334.md"
  - "CLM-0885 -> paper/decoupling_marl_model_first/reports/R336.md"
  - "CLM-0890 -> paper/decoupling_marl_model_first/reports/R339.md"
  - "CLM-0895 -> paper/decoupling_marl_model_first/reports/R340.md"
  - "CLM-0900 -> paper/decoupling_marl_model_first/reports/R341.md"
  - "CLM-0910 -> paper/decoupling_marl_model_first/reports/R344.md"
  - "CLM-0915 -> paper/decoupling_marl_model_first/reports/R350.md"
  - "CLM-0920 -> paper/decoupling_marl_model_first/reports/R351.md"
  - "CLM-0925 -> paper/decoupling_marl_model_first/reports/R352.md"
  - "CLM-0930 -> paper/decoupling_marl_model_first/reports/R356.md"
  - "CLM-0935 -> paper/decoupling_marl_model_first/reports/R357.md"
  - "CLM-0940 -> paper/decoupling_marl_model_first/reports/R358.md"
  - "CLM-0945 -> paper/decoupling_marl_model_first/reports/R359.md"
  - "CLM-0950 -> paper/decoupling_marl_model_first/reports/R360.md"
  - "CLM-0955 -> paper/decoupling_marl_model_first/reports/R361.md"
  - "CLM-0960 -> paper/decoupling_marl_model_first/reports/R362.md"
  - "CLM-0965 -> paper/decoupling_marl_model_first/reports/R363.md"
required_reading:
  - paper/decoupling_marl_model_first/LINE.md
verification:
  - "This navigation card holds no feed facts: per-round verdicts, numbers, and gate outcomes live only in the feeds bound by evidence_refs above. Run the registered rounds and read their feeds before claiming any gate status."
  - "Runtime execution uses local observations, declared neighbour messages, and independent vector actions without a central scalar projection; EVAL remains diagnostic-only and training starts only after a prospective residual-headroom gate."
stop_when:
  - "This line remains read-only and non-selectable. Its gates may inform the successor design, but its claims, outcomes, and common-channel feasibility do not transfer as controller or MARL evidence."
---

# Model-First frozen methodology evidence line

## Outcome disposition

This manuscript line is a failed title-goal attempt but a successful bounded
deterministic-control and methodology investigation.  The implemented plant
adds four independently commanded storage devices at the four VSG buses and
optimizes their active-power requests; it does not implement one unified
VSG-with-storage device.  The retained centralized deterministic controller
establishes a finite-bank storage-power-control gain (`CLM-0910`).  Relative to
that controller, even the outcome-seeing offline upper bound exposes only
marginal nominal residual headroom, while the registered residual and
local/neighbour information families do not establish a qualifying causal
learnable increment (`CLM-0915`, `CLM-0945`--`CLM-0960`).  No neural or
multi-agent controller was therefore trained or evaluated.  The later
common-channel result (`CLM-0965`) preserves a physical mechanism clue, not a
controller or learning result.  Consequently, this line cannot support the
fixed title's Multi-Agent Reinforcement Learning term.  It remains frozen as
bounded deterministic-control and methodology evidence, together with its
reusable implementation assets.

This file is navigation only. Open evidence through current claims and the
registered artifact map; do not copy result values or source-paper conclusions
into this file.
