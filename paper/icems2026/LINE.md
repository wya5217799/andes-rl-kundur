---
line_id: icems2026
status: frozen
stage: frozen-evidence-line
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
  Preserve the bounded ICEMS manuscript, claims, feeds, and implementation
  assets as a read-only evidence line. No result or checkpoint transfers to
  the successor fixed-title line.
decision_refs:
  - "docs/adr/0015-reset-fixed-title-to-object-matched-line.md#decision"
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
  - This line remains read-only and non-selectable; reopening requires a new explicit decision.
  - R280, R291, and R338 remain bounded to their executed objects and do not support the successor title.
---

# ICEMS 2026 frozen evidence line

## Failure disposition

This manuscript line is a failed title-goal attempt, not a merely incomplete
positive MARL result.  Its headline shared scalar factorization does not
compare one independently acting agent per VSG.  The later sealed distributed
comparison uses three edge actors rather than four VSG agents and establishes
`NO-NEURAL-INCREMENT` against the selected classical edge controller
(`CLM-0905`), including failure of the registered relative no-harm guard.  The
learned distributed arm therefore did not merely lack a positive increment; it
failed the registered comparison against the retained classical controller.
Consequently, this line cannot support the fixed title as a successful
multi-agent coordination contribution.  It remains frozen only as bounded
negative evidence and as a source of reusable implementation and evaluation
assets.

This file is navigation only. Open evidence through current claims and the
registered artifact map; do not copy result values or source-paper conclusions
into this file.
