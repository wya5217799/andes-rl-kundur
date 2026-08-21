---
line_id: converter-vsg-pq-decoupling
status: active
priority: 2
stage: ppvsm1-signed-authority-stop
artifact_manifest: paper/converter_vsg_pq_decoupling/ARTIFACTS.json
scope:
  write_roots:
    - paper/converter_vsg_pq_decoupling
  shared_read_roots:
    - paper/paralleled_vsg_marl
    - paper/decoupling_marl_model_first
    - paper/icems2026
    - memory
    - results
    - docs/research
    - src/andes_rl_kundur
venue:
  kind: journal
  status: unassessed
  primary: To be selected after the deterministic and headroom gates
  decision_record: paper/converter_vsg_pq_decoupling/working/route_contract.md
  official_source_status: unverified
  last_checked: null
  review_triggers:
    - after a valid deterministic P/Q-decoupling result
    - after the learning-necessity gate
    - before venue-specific drafting or submission
working_title: "Physics-First P/Q Decoupling and Coordinated Control of Converter-Level VSGs"
title_policy: "The title is provisional and contains no MARL claim; every physical and coordination term remains prospective until its same-object gate passes."
objective: >-
  Preserve the R384--R397 valid stops and analysis-invalid records as
  registered. R397 validly stops the two-unit PPVSM1 formulation at the
  signed P/Q authority gate on target attribution; no controller,
  decoupling, learning, droop-slope, or successor work is authorized.
decision_refs:
  - "docs/adr/0016-separate-converter-vsg-pq-decoupling-line.md#decision"
  - "docs/adr/0017-structural-absence-regcv1-successor.md#decision"
  - "paper/converter_vsg_pq_decoupling/working/route_contract.md#decision"
  - "paper/converter_vsg_pq_decoupling/working/route_contract.md#regf2-successor-decision"
  - "paper/converter_vsg_pq_decoupling/working/route_contract.md#r390-mechanism-only-decision"
  - "paper/converter_vsg_pq_decoupling/working/route_contract.md#r391-disposition"
  - "paper/converter_vsg_pq_decoupling/working/route_contract.md#survey-conformance"
evidence_refs:
  - "CLM-1060 -> paper/converter_vsg_pq_decoupling/reports/R383.md"
  - "CLM-1065 -> paper/converter_vsg_pq_decoupling/reports/R384.md"
  - "CLM-1070 -> paper/converter_vsg_pq_decoupling/reports/R385.md"
  - "CLM-1075 -> paper/converter_vsg_pq_decoupling/reports/R386.md"
  - "CLM-1080 -> paper/converter_vsg_pq_decoupling/reports/R387.md"
  - "CLM-1085 -> paper/converter_vsg_pq_decoupling/reports/R388.md"
  - "CLM-1090 -> paper/converter_vsg_pq_decoupling/reports/R389.md"
  - "CLM-1095 -> paper/converter_vsg_pq_decoupling/reports/R390.md"
  - "CLM-1100 -> paper/converter_vsg_pq_decoupling/reports/R391.md"
  - "CLM-1105 -> paper/converter_vsg_pq_decoupling/reports/R392.md"
  - "CLM-1125 -> paper/converter_vsg_pq_decoupling/reports/R396.md"
  - "CLM-1130 -> paper/converter_vsg_pq_decoupling/reports/R397.md"
required_reading:
  - paper/converter_vsg_pq_decoupling/LINE.md
  - paper/converter_vsg_pq_decoupling/working/route_contract.md
verification:
  - Preserve Kundur connectivity and the ANDES 2.0.0 platform; change only the prospectively registered object and its parameters.
  - One converter-level VSG equals one physical device; later P/Q pairs must come from the actual dynamic seam.
  - Establish initialization and signed per-channel authority; match permissions across all comparison families.
  - Prior-line implementations need prospective validation; prior results and thresholds are not evidence here.
stop_when:
  - No MARL training until object, deterministic decoupling, non-learning headroom, and information-value gates all pass.
  - R390 is analysis-invalid by CLM-1095; R391 closes Q-0108 positive.
  - R391 stops this formulation before authority; R392 validly stops the stock-REGF2 diagnosis at MECHANISM-MIXED; no successor or deployment work is authorized.
  - R393+ runs PPVSM1 on a two-unit diagnostic cell first; four-unit scaling is a later gate.
  - R397 validly stops the two-unit PPVSM1 formulation at the signed authority gate (target attribution on PPVSM1_1 Pref); no successor, controller, decoupling, learning, droop-slope, or scaling work is authorized.
  - Do not change Kundur connectivity here; topology generalization needs a later gate.
  - ANDES phasor-domain evidence cannot support switching, harmonic, protection, EMT, HIL, or deployment claims.
---

# Converter-level VSG P/Q-decoupling manuscript line

This file is navigation only.  Experimental facts enter through claims and
bound feeds created prospectively on this line.
