---
line_id: decoupling-marl-model-first
status: active
priority: 3
stage: common-channel-headroom-confirmed-methodology-route
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
  Rebuild the titled MARL coordination from an implementation-faithful sampled-data
  DAE, exact common/differential decomposition retaining measured cross-coupling,
  independently executed local vector actions, and a matched deterministic-plus-neural
  comparison. Neural training is forbidden until model, authority, deterministic-control,
  and residual-headroom gates pass.
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
  - "The affine, flexible non-neural, one-hop message, and shared-prediction learnability gates are complete and negative; the common-channel headroom gate is positive. Any continuation must register a mechanistically different falsifiable question; no new execution starts from the current evidence alone. The working title wording remains fixed; its Coordination and Multi-Agent Reinforcement Learning terms remain prospective until valid distributed-action and learning evidence exists."
---
