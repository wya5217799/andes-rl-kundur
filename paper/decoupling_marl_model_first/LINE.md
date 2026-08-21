---
line_id: decoupling-marl-model-first
status: active
priority: 3
stage: manuscript-closure
artifact_manifest: paper/decoupling_marl_model_first/ARTIFACTS.json
scope:
  write_roots: [paper/decoupling_marl_model_first]
  shared_read_roots: [memory, results, docs/research, src/andes_rl_kundur]
venue:
  kind: journal
  status: shortlisted
  primary: "IEEE Transactions on Power Systems (Pass 1 shortlist; lock owned by author/PI)"
  backup: "IEEE Transactions on Sustainable Energy / Electric Power Systems Research / IEEE Open Access Journal of Power and Energy (Pass 1 shortlist)"
  decision_record: paper/decoupling_marl_model_first/working/venue_decision_2026-08-14.md
  official_source_status: partial
  last_checked: 2026-08-14
  review_triggers: [before venue-specific framing, before manuscript drafting, before submission (Pass 3 refresh)]
working_title: "An Implementation-Faithful Model-First Methodology for Storage-Coordinated Paralleled VSGs: Bounded Deterministic-Control Gain and Residual-Headroom Limits"
title_policy: "Object-matched wording, methodology plus bounded deterministic-control framing; the MARL term is unsupported by this evidence and is excluded. Exact wording is fixed by the PI at the argument-contract stage; no title term may exceed the registered claim ceiling."
objective: >-
  Manuscript-only closure: turn the line's terminal evidence (R306-R363,
  CLM-0740-CLM-0965) into one object-matched paper via the venue gate and the
  paper-writing protocol. The experiment side stays frozen: no new rounds,
  claims, questions, simulator execution, or training on this line.
decision_refs:
  - "docs/adr/0015-reset-fixed-title-to-object-matched-line.md#decision"
  - "docs/adr/0018-reactivate-decoupling-model-first-manuscript-only.md#decision"
  - "paper/decoupling_marl_model_first/working/model_contract.md#research-objective"
  - "paper/decoupling_marl_model_first/working/model_contract.md#equation-to-implementation-reconciliation"
  - "paper/decoupling_marl_model_first/working/venue_decision_2026-08-14.md#pass-1-shortlist"
  - "paper/decoupling_marl_model_first/working/manuscript_argument_contract_2026-08-14.md#thinking-template"
evidence_refs: ["CLM-0740 -> paper/decoupling_marl_model_first/reports/R306.md", "CLM-0745 -> paper/decoupling_marl_model_first/reports/R307.md", "CLM-0750 -> paper/decoupling_marl_model_first/reports/R308.md", "CLM-0755 -> paper/decoupling_marl_model_first/reports/R309.md", "CLM-0760 -> paper/decoupling_marl_model_first/reports/R310.md", "CLM-0765 -> paper/decoupling_marl_model_first/reports/R311.md", "CLM-0770 -> paper/decoupling_marl_model_first/reports/R312.md", "CLM-0775 -> paper/decoupling_marl_model_first/reports/R313.md", "CLM-0780 -> paper/decoupling_marl_model_first/reports/R314.md", "CLM-0785 -> paper/decoupling_marl_model_first/reports/R315.md", "CLM-0790 -> paper/decoupling_marl_model_first/reports/R316.md", "CLM-0795 -> paper/decoupling_marl_model_first/reports/R317.md", "CLM-0800 -> paper/decoupling_marl_model_first/reports/R318.md", "CLM-0805 -> paper/decoupling_marl_model_first/reports/R319.md", "CLM-0810 -> paper/decoupling_marl_model_first/reports/R320.md", "CLM-0815 -> paper/decoupling_marl_model_first/reports/R321.md", "CLM-0820 -> paper/decoupling_marl_model_first/reports/R322.md", "CLM-0825 -> paper/decoupling_marl_model_first/reports/R323.md", "CLM-0830 -> paper/decoupling_marl_model_first/reports/R324.md", "CLM-0835 -> paper/decoupling_marl_model_first/reports/R325.md", "CLM-0840 -> paper/decoupling_marl_model_first/reports/R326.md", "CLM-0845 -> paper/decoupling_marl_model_first/reports/R327.md", "CLM-0850 -> paper/decoupling_marl_model_first/reports/R328.md", "CLM-0855 -> paper/decoupling_marl_model_first/reports/R329.md", "CLM-0860 -> paper/decoupling_marl_model_first/reports/R330.md", "CLM-0865 -> paper/decoupling_marl_model_first/reports/R331.md", "CLM-0870 -> paper/decoupling_marl_model_first/reports/R332.md", "CLM-0875 -> paper/decoupling_marl_model_first/reports/R333.md", "CLM-0880 -> paper/decoupling_marl_model_first/reports/R334.md", "CLM-0885 -> paper/decoupling_marl_model_first/reports/R336.md", "CLM-0890 -> paper/decoupling_marl_model_first/reports/R339.md", "CLM-0895 -> paper/decoupling_marl_model_first/reports/R340.md", "CLM-0900 -> paper/decoupling_marl_model_first/reports/R341.md", "CLM-0910 -> paper/decoupling_marl_model_first/reports/R344.md", "CLM-0915 -> paper/decoupling_marl_model_first/reports/R350.md", "CLM-0920 -> paper/decoupling_marl_model_first/reports/R351.md", "CLM-0925 -> paper/decoupling_marl_model_first/reports/R352.md", "CLM-0930 -> paper/decoupling_marl_model_first/reports/R356.md", "CLM-0935 -> paper/decoupling_marl_model_first/reports/R357.md", "CLM-0940 -> paper/decoupling_marl_model_first/reports/R358.md", "CLM-0945 -> paper/decoupling_marl_model_first/reports/R359.md", "CLM-0950 -> paper/decoupling_marl_model_first/reports/R360.md", "CLM-0955 -> paper/decoupling_marl_model_first/reports/R361.md", "CLM-0960 -> paper/decoupling_marl_model_first/reports/R362.md", "CLM-0965 -> paper/decoupling_marl_model_first/reports/R363.md"]
required_reading:
  - paper/decoupling_marl_model_first/LINE.md
verification:
  - "This navigation card holds no feed facts: per-round verdicts, numbers, and gate outcomes live only in the feeds bound by evidence_refs above. Run the registered rounds and read their feeds before claiming any gate status."
  - "Manuscript lane only: drafting, figures, and venue artifacts stay inside this line's write scope; the shared ledger, results, and other manuscript lines remain read-only."
stop_when:
  - "Experiment side frozen: no new evidence round, claim, question, simulator execution, or training on this line; the terminal evidence is R306-R363 and CLM-0740-CLM-0965."
  - "No MARL, learned-controller-value, or unqualified residual-learning wording; every headline statement stays at its bound feed's allowed claim."
  - "No venue-specific framing before the venue gate shortlists; no submission before Pass 3 refresh and the submission audit."
  - "Reviewer requests that need new data or execution are future work, not this line's repair."
  - "Cross-line evidence transfer stays forbidden by ADR-0015."
---

# Model-First manuscript-closure line

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
common-channel result (`CLM-0965`) is a physical mechanism finding, not a
controller or learning result.  Consequently, this line cannot support the
fixed title's Multi-Agent Reinforcement Learning term.  Per ADR-0018 it is
active for manuscript-only closure of its bounded deterministic-control and
methodology evidence; its experiment side stays frozen.

This file is navigation only. Open evidence through current claims and the
registered artifact map; do not copy result values or source-paper conclusions
into this file.
