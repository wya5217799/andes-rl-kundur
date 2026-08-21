# Consolidated review — decoupling-marl-model-first (2026-08-14)

Consolidated, action-bearing record of the two manuscript review passes run
on 2026-08-14. Detailed reviewer reports stay ephemeral under
`tmp/decoupling_marl_model_first/`; this file records decisions and the fix
log only. This is a review record, not project evidence.

## Inputs reviewed

- Evidence audit: `tmp/decoupling_marl_model_first/evidence_audit_2026-08-14.md`
  (skill: audit-manuscript-evidence; inventory at
  `tmp/decoupling_marl_model_first/inventory_draft.json`).
- Pre-submission review: `tmp/decoupling_marl_model_first/presubmission_review_2026-08-14.md`
  (skill: pre-submission-reviewer).

## Decisions

1. Evidence audit: PASS (53 VERIFIED, 3 QUALIFIED, 0 UNSUPPORTED, 0
   CONFLICTED, 0 UNCHECKABLE). Wording ceiling fully held; no cross-section
   drift.
2. Pre-submission review: 0 CRITICAL, 8 MAJOR, 17 MINOR; score 5/10 at
   review time, "needs major revision" (assembly-stage only).
3. Domain audit (supervisor inline, per publication-gate route): CONDITIONAL
   PASS; presentation-only checks deferred to assembly.
4. Comparison-identifiability gate: ALLOW x4 (recorded in the argument
   contract).

## Fix log (applied 2026-08-14, all in the six draft files)

- R1.1 Introduction P5 section pointer corrected (canaries -> Section IV).
- R1.2 Information configurations counted as three (snapshot / one-hop
  messages / prediction messages) across Abstract, Results prose, Table II,
  Discussion, Conclusion; ground truth confirmed against R359-R362.
- R2.1 One-sentence lead-ins added to Sections III-VII.
- R4.2 IEEE-style captions added: Table I (nodes), Table II (family gate
  outcomes with legend).
- R4.3 Citation pool completed: ANDES [40], Kundur book [41], OSQP [42],
  Witsenhausen 1968 [43]; Yang et al. fixed as a single TPWRS 2023 entry.
- R5.1 Figure plan deduplicated: family results as Table II only (fig6
  unused); fig5 reworked to per-scenario rendering.
- Em-dash connectors and spaced-hyphen parentheticals removed from all
  manuscript prose; acronyms (DAE, TDS, NRMSE, SOC, QP, LPV) defined on
  first use; grammar fixes G3/G4/G7 applied; stale author notes refreshed.
- Audit M-1: Stage-1 nonlinearity ceiling labels corrected to OP0-point /
  all-point. Audit M-2: Discussion VII-A reworded to the feed's
  "outcome-seeing offline upper bound".

## Open items at consolidation time

1. PI title choice (candidates 1-3 in draft/abstract_title_candidates.md);
   assembly uses candidate 1 provisionally.
2. Venue Pass 2 lock (author constraints) and Pass 3 refresh before
   submission.
3. Figure rework (fig5 per-scenario) and figures_source_manifest.md
   finalization (in progress, figure agent).
4. LaTeX assembly + compile + W4 gate (in progress, assembly agent).
5. Submission-package audit (audit-journal-submission) after assembly.
6. Human full-text verification items from the differentiation memo
   (10 items, especially the search-bounded RQ1 absence claim).
