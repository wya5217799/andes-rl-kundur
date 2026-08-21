# LaTeX assembly plan (2026-08-14)

Working plan for assembling the submission package from the six Markdown
draft files. Not manuscript prose. Venue-specific formatting waits for the
Pass 2 venue lock; the IEEEtran class is used as the working skeleton
because the Pass 1 primary is an IEEE journal.

## Source mapping

| LaTeX file | From | Status |
|---|---|---|
| main.tex | — | to create |
| sec1_introduction.tex | draft/introduction_sec1.md | draft exists |
| sec2_related.tex | draft/related_work_sec2.md | draft exists |
| sec3_plant.tex | draft/methods_sec3_4.md (Section III) | draft exists |
| sec4_methodology.tex | draft/methods_sec3_4.md (Section IV) | draft exists |
| sec5_results.tex | draft/results_sec5_6.md (Section V) | draft exists |
| sec6_diagnosis.tex | draft/results_sec5_6.md (Section VI) | draft exists |
| sec7_discussion.tex | draft/discussion_conclusion_sec7_8.md (Section VII) | draft exists |
| sec8_conclusion.tex | draft/discussion_conclusion_sec7_8.md (Section VIII) | draft exists |
| abstract.tex | draft/abstract_title_candidates.md | draft exists; title pending PI |
| references.bib | working/differentiation_memo_2026-08-14.md references | 39 entries, verified pool |

## Assembly steps (order)

1. After PI fixes the title, convert each section to LaTeX (equations in
   align/equation, the family table as a booktabs table, Table III.1 as a
   proper table with source pointer).
2. Renumber citations citation-sequence across the full paper from the
   differentiation memo's [1]-[43] order; generate references.bib.
3. Insert the five planned figures (argument contract section 6); each
   figure gets a source pointer to its results JSON in the caption or
   source note per venue norms. Table II carries the family results; no
   family figure.
4. W4 consistency gate on the assembled file: identical headline numbers
   across Abstract/Introduction/Results/Discussion/Conclusion; wording
   ceiling re-checked.
5. W7: compile with IEEEtran, fix overfull/underfull warnings, produce PDF.
6. Venue Pass 3 refresh (official sources re-checked) after material
   content is final.
7. audit-journal-submission on the final package before sign-off.

## Numbered-equation set (review finding 4.1)

Fix these as numbered, prose-referenced equations at conversion:
(1) the sampled-data index-1 DAE plant; (2) the GENCLS swing equations;
(3) the ESD1 active-current lag and achieved power; (4) the
common/differential coordinate transform; (5) the separate-input plant
model; (6) the tree-edge residual and zero-common condition; (7) the
physically constrained joint-endpoint QP. All other display math stays
unnumbered notation.

## Open before assembly

- PI title choice (candidates in draft/abstract_title_candidates.md).
- Evidence-audit findings (running) and pre-submission-reviewer findings
  must be folded into the section drafts BEFORE conversion.
- Figures are generated only from results JSONs via the feeds (no
  recomputation of evidence); rendering happens after the review passes.
