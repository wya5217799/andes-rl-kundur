---
line_id: icems2026
status: active
priority: 1
stage: revision
artifact_manifest: paper/icems2026/ARTIFACTS.json
scope:
  write_roots:
    - paper/icems2026
  shared_read_roots:
    - memory
    - results
    - docs/research
venue:
  kind: conference
  status: locked
  primary: 29th International Conference on Electrical Machines and Systems
  decision_record: paper/icems2026/README.md
  official_source_status: current
  last_checked: 2026-07-26
  review_triggers:
    - before final upload
    - after organizer instructions change
objective: >-
  Revise the ICEMS paper using the current R280, R291, and R338 claim/feed
  authority: preserve the title, retain fixed 3 s only as a bounded benchmark,
  and align all architecture language with the executed scalar and three-edge
  comparisons without a positive class-level or generalization claim.
decision_refs:
  - "paper/icems2026/README.md#icems-2026-full-paper"
  - "paper/icems2026/working/chapter_blueprint.md#v-results-and-discussion"
evidence_refs:
  - "CLM-0580 -> paper/icems2026/reports/R280.md"
  - "CLM-0585 -> paper/icems2026/reports/R280.md"
  - "CLM-0590 -> paper/icems2026/reports/R280.md"
  - "CLM-0595 -> paper/icems2026/reports/R280.md"
  - "CLM-0610 -> paper/icems2026/reports/R280.md"
  - "CLM-0670 -> paper/icems2026/reports/R291.md"
  - "CLM-0905 -> paper/icems2026/reports/R338.md"
required_reading:
  - paper/icems2026/LINE.md
  - paper/icems2026/working/chapter_blueprint.md
verification:
  - Architecture claims name the scalar executed action and tested shared factorization.
  - Three-edge architecture claims distinguish endpoint-only shared-edge execution from joint-observation execution and retain the selected classical controller.
  - Quantitative claims remain within current claim and retained-artifact authority.
  - Unified GFM-BESS, motor-load, topology, EMT, and deployment transfer remain explicit non-claims unless separately authorized and evidenced.
  - No source manuscript or SCI line is modified outside its selected write scope.
stop_when:
  - Abstract, contributions, results, limitations, and conclusion use the same bounded architecture claim.
  - The R291 negative handoff gate is used only as bounded result and limitation evidence.
  - The R338 genuine distributed comparison is used only through CLM-0905 and its bounded negative publication disposition.
  - The professor-facing revision decision says no further control experiment is currently necessary.
  - The exact ICEMS package passes its evidence, domain, repository, and compile checks.
---

# ICEMS 2026 manuscript line

This file is navigation only. Open evidence through current claims and the
registered artifact map; do not copy result values or source-paper conclusions
into this file.
