---
line_id: decoupling-marl-model-first
status: active
priority: 3
stage: physical-input-location-diagnosis
artifact_manifest: paper/decoupling_marl_model_first/ARTIFACTS.json
scope:
  write_roots:
    - paper/decoupling_marl_model_first
  shared_read_roots:
    - memory
    - results
    - docs/research
    - src/andes_rl_kundur
venue:
  kind: conference
  status: unassessed
  primary: To be selected
  decision_record: paper/decoupling_marl_model_first/working/model_contract.md
  official_source_status: unverified
  last_checked: null
  review_triggers:
    - before venue-specific framing
    - before manuscript drafting
working_title: "Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning"
title_policy: >-
  Wording fixed by PI on 2026-08-03; unchanged wording does not validate title terms before their registered gates pass.
objective: >-
  Rebuild Decoupling-Oriented Coordination of Paralleled VSGs With
  Multi-Agent Reinforcement Learning from an implementation-faithful sampled-
  data DAE, an exact common/differential decomposition that retains measured
  cross-coupling, independently executed local vector actions, and a matched
  deterministic-plus-neural comparison. Neural training is forbidden until
  model, authority, deterministic-control, and residual-headroom gates pass.
decision_refs:
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
required_reading:
  - paper/decoupling_marl_model_first/LINE.md
verification:
  - Runtime execution uses local observations, declared neighbour messages, and independent vector actions without a central scalar projection.
  - Single-network and multi-agent arms share the same physical action, limits, bank, interaction budget, and registered estimand.
  - EVAL remains diagnostic-only and training starts only after a prospective residual-headroom gate.
  - R316 validates the frozen order-10 retained-cross dynamic reduction and its finite-bank empirical mismatch envelope on two untouched operating conditions and three input shapes; only a separate deterministic-controller design question is now eligible, while physical control, distributed-agent, and learning claims remain blocked.
  - R322 validly finds arm-dependent mixed gain-authority and estimation effects on the registered development bank, so neither prospective dominance signature passes and no common scalar repair or fresh holdout is authorized; any future deterministic route must include actuator constraints prospectively in synthesis.
  - R324 binds every material proxy/execution value to a source or explicit assumption and passes both frozen adjacent open-loop TDS-subdivision convergence pairs; Q-0079 closes positive and Q-0078 is eligible on the unchanged plant.
  - "R330 validly passes the exact frozen R329 package on all 80 registered untouched retained-model rows under five fixed linear delivered-output transforms; this is model-only package evidence and authorizes only the separately registered ANDES bridge question, not physical, distributed-agent, learning, stability, safety, topology-generalization, or title-result claims."
  - "R332 validly blocks the direct physical bridge because the frozen R329 disturbance shares the control-input channel while the declared experiment requires a separate physical disturbance; only open-loop disturbance identification is eligible, with no controller, distributed-agent, learning, or title-result claim."
  - "R334 validly qualifies one independently executed Bus14 active-load column for one signed pair and two operating points under the corrected complete source-bound contract; Q-0085 closes positive, but a separately sealed successor disturbance package remains mandatory before any physical closed loop."
  - "R336 validly blocks the complete four-load physical disturbance package: all records and physical event guards pass, but the immutable model misses both Bus7/Bus8 channel waveforms at development and untouched points while Bus14/Bus15 pass; numerical full rank cannot override failed response gates, and only a location-dependent input-dynamics diagnosis is eligible."
stop_when:
  - Q-0087 may only diagnose which location-dependent input dynamics explain the upstream-load mismatch, beginning with R336 development data and stopping before any repair is selected on holdout outcomes.
  - No deterministic physical closed loop, distributed runtime, reward design or optimization, agent, neural training, or EVAL starts before a publication-valid physical disturbance result, the deterministic ANDES bridge, and a separately registered residual-headroom gate pass. A reduced-model holdout or failed-gate diagnostic cannot authorize them.
  - The working conference title wording remains fixed; its Coordination and Multi-Agent Reinforcement Learning terms remain prospective until valid distributed-action and learning evidence exists.
---
# Model-first decoupling and multi-agent manuscript line - a full mathematical and experimental rebuild that inherits no other paper's claims without re-audit.
