# R485 manuscript audit — 2026-09-01

## Status

**PASS — revised, re-reviewed candidate; not canonical.**

The reviewed manuscript is `manuscript/main_r485.tex`. The pre-existing
`manuscript/main.tex` was used only as a donor for structure, presentation,
method-explanation patterns, and literature leads. It was not used as an edit
base or as scientific evidence, and it was not modified or promoted over.

## Fixed route and claim boundary

- Title: *Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning*.
- Headline evidence: CLM-1525 / R485 only.
- Post-hoc support: CLM-1530 / R486 only, explicitly subordinate to R485.
- The accepted digest constrains the title only; it does not constrain the
  manuscript's problem statement, method, contributions, results, or conclusion.
- The 6 s primary screen and 30 s direct checks are reported separately and are
  not pooled.
- Command RMS and command total variation are comparator-relative command-activity
  measures, not physical-safety, hardware-stress, thermal, wear, or damage claims.
- Actor-path and observation diagnostics are exploratory associations and are not
  presented as identified causal mechanisms.
- No new experiment, training run, simulation, or sweep was introduced for this
  manuscript.

## Evidence checks

- R485 headline reproduced consistently: 121/208 endpoint-qualified evaluations,
  0/208 complete-contract passes; command-RMS and command-TV fail in 832/832
  evaluated blocks; 397 RoCoF failures and 37 worst-frequency-peak failures.
- The four source contrasts are described as not establishing a Holm-controlled
  material effect, never as equivalence to zero.
- R486 is limited to post-hoc support: 5/208 cases pass endpoints and all
  non-command guards while failing command-activity guards; break-even ratios and
  median command-activity ratios are kept in that qualified context.
- Direct 30 s M/D cases remain a separate four-case check. Earlier R483/R484
  checkpoints, replay rows, and result counts do not enter the R485 result set.

## Writing gates

- `intro-drafter` hard-flaw gate: **PASS**. The Introduction follows the required
  six-paragraph chain, states exactly three contributions, and keeps limitations
  independent of contributions.
- `paper-writer` evidence map and chapter blueprint: **PASS**. Evidence authority,
  chapter-level claim scope, and result provenance were fixed before drafting.
- Fresh-context citation and evidence review: **PASS**. All 16 unique citation
  keys resolve in `references.bib` and support their adjacent claims; numerical
  and semantic checks against R485/R486 passed.
- High-risk wording review: **PASS**. No command-activity-to-safety conversion,
  diagnostic-to-causal conversion, non-rejection-to-equivalence conversion, or
  R483/R484 result carry-over was found.
- `academic-research-suite` Stage 2.5: **PASS WITH NOTES**. All 16 rendered
  references, 16 citation contexts, 26 high-impact claim groups, 41 exact
  Evidence Rows, 25 data/method checks, and seven AI research failure modes were
  reviewed. The two notes are the legacy non-ARS provenance passport and the
  bounded originality sample; neither blocks Stage 3 after owner confirmation.
  Full record: `working/ars_stage25_r485_20260901/stage25_integrity_report.md`.

## Build and visual QA

- Output: `manuscript/main_r485.pdf`, 6 A4 IEEE two-column pages.
- Build sequence: `pdflatex`, `bibtex`, `pdflatex`, `pdflatex`.
- `latexmk` was unavailable because the local MiKTeX installation lacks Perl;
  the explicit equivalent build sequence completed successfully.
- Log: no undefined references or citations, no LaTeX errors, and no overfull
  boxes. Two underfull hboxes (badness 1931 and 2134) and one underfull vbox are
  ordinary line/column whitespace and do not hide content.
- All six rendered pages were inspected. No clipping, overlap, unreadable figure,
  malformed glyph, or reference-layout defect was observed.

## Repository checks

- `python memory/tools/inventory_manuscript.py ...`: evidence-sensitive inventory
  generated and reviewed.
- `python memory/tools/validate.py`: **OK** (469 claims, 112 questions, 36 notes;
  90 historical or unrelated soft warnings).
- `feed_check.py reports/R485.md`: **OK**.
- `feed_check.py reports/R486.md`: **OK**.
- `session_context.py --json --line yang-md-decoupling-marl`: manuscript mode;
  no artifact alerts after candidate registration.

## Disposition

This is a reviewed R485 candidate and a source-package input. It remains
noncanonical by design because the requested deliverable is `main_r485.tex` and
the donor `main.tex` must stay intact until an explicit promotion decision.

## Full five-seat review and revision closeout

The frozen pre-revision candidate received five role-separated reviews:
Journal-Fit/EIC, methodology, VSG-domain, deployment/reproducibility perspective,
and Devil's Advocate. The panel used one model family, so role separation is not
reported as independent error processes. Its mechanical first-round outcome was
**Major Revision**: no critical finding or evidence contradiction was found, but
method reporting, construct boundaries, originality positioning, and artifact
access required repair.

The revision resolved the load-bearing findings without new simulation or
training:

- narrowed qualification to the finite empirical contract and defined
  `decoupling-oriented` as a finite-window response-energy target, not modal
  decoupling, safety, stability, or a universal MARL claim;
- made objective--evaluation mismatch the principal alternative explanation for
  0/208 and stated that a matched command-aware objective is needed for causal
  attribution;
- disclosed the complete normalized observation, device/system-base action
  semantics, decoded-increment reward terms, signed-rank assumptions, separate
  Holm families, all eight post-hoc familywise upper bounds, and exact inventory
  denominators;
- added the exact 14-card table, adjacent-control positioning, an assurance
  ladder, and a machine-readable reproduction manifest;
- corrected the execution provenance: R485 sources are bound to reviewed commit
  `bf2d445d8a9ac1faa862dbd15aa1bf6c83024aa0`; the later post-hoc intake is
  separately bound to `8610a9e43cf153c993e889c1da22cad295406927`.

Stage 3-prime re-review used revision-blind criteria commitments followed by
persuasion-blind evidence checks. One re-review cycle correctly found a
conflicting execution-commit statement and five omitted numerical upper bounds;
both were repaired and rechecked. The final scoped re-verifications returned
**FULLY ADDRESSED** for every inherited must-fix and should-fix item, with no new
regression.

## Stage 4.5 final integrity

- Final source SHA-256:
  `15338efbb483d81befaed899334f5ec1ff971c89d69ba69e08b88b96dc9ab7ae`.
- Final PDF SHA-256:
  `8560b41427f9273dd763381d55ca3d57b7f177806245c79779789e9c9d9a57ee`.
- PDF structural preflight: PASS, 6/6 enumerated and readable A4 pages;
  unencrypted PDF 1.5; 22/22 fonts embedded.
- Citation closure: 19 unique cited keys, 0 missing from the 24-entry BibTeX
  database; no unresolved `??`, TODO, DRAFT, or placeholder markers.
- R485 authority replay: `VALID-MIXED`; 121 endpoint-qualified policies, 0
  complete-contract policies, 832 blocks, 832 command-RMS failures, 832
  command-TV failures, 397 RoCoF failures, 37 worst-peak failures, 0
  common-frequency failures, 1,082/1,082 terminal artifacts, and 5,088/5,088
  trajectories; no horizon pooling or available-case analysis.
- Reproduction companion:
  `working/r485_reproducibility_companion_20260901.zip`, SHA-256
  `03c895d8420528cee38dddfde787f01d2515a2ef7df3c97f035fb381995ef0f4`;
  ZIP CRC, external sidecar, internal sidecars, 14/14 profile cards, 26-seed
  roster, result hashes, and fixed settings all verified.
- Final visual inspection: all six pages are readable; figures, tables,
  equations, reference columns, and page breaks show no clipping, overlap, or
  malformed glyphs.

No manuscript-level scientific blocker remains within the frozen R485/R486
evidence ceiling. IEEE PDF eXpress validation, author metadata, funding/conflict
declarations, copyright, and final submission-system actions remain external
human submission steps.
