# Assembly report — decoupling-marl-model-first submission package (2026-08-14)

Mechanical LaTeX assembly of the manuscript from the six section drafts.
Prepared for later registration by the supervisor; nothing was registered
by this pass.

## Files produced (paper/decoupling_marl_model_first/)

| File | Status |
|---|---|
| `main.tex` | assembled IEEEtran journal skeleton, 8 sections in order I–VIII |
| `references.bib` | 43 BibTeX entries from the differentiation memo [1]–[43], none skipped |
| `main.pdf` | compiled, 10 pages, 0 overfull boxes, 0 undefined refs/citations |
| `assembly_report.md` | this file |

Supporting build outputs also present: `main.aux`, `main.log`, `main.bbl`,
`main.blg`.

## Compile status

`pdflatex` (MiKTeX) exists. Full cycle run and green:
`pdflatex` (1st) → `bibtex` (clean, after one mechanical fix described
below) → `pdflatex` (2nd) → `pdflatex` (3rd). Final PDF: `main.pdf`,
10 pages, no overfull `\hbox`, no undefined references or citations.
8 cosmetic underfull-box warnings remain in justified captions/columns
(badness-10000 spacing artifacts endemic to IEEEtran two-column layout;
no content impact).

## What went in / what was kept out

- Title: provisional candidate 1, on one clearly marked `\title` line
  (PI swap point commented in the tex). Author block and IEEEkeywords are
  placeholders pending PI sign-off (no author/keyword content exists in
  the drafts; nothing was invented).
- Abstract verbatim from `abstract_title_candidates.md` (no citations).
- Sections I–VIII converted in order; every "Status:", "Delivery notes",
  draft header, markdown rule, and the intro draft's cited-subset list
  are author metadata and were excluded.
- All numbers kept verbatim (see W4 gate below).
- Tables: Table I (four storage nodes) and Table II (information-family
  gate outcomes) as booktabs tables with the drafts' captions verbatim,
  including their "Source:" pointers.
- Figures: fig1 (plant), fig2 (gate sequence), fig3 (R312 probes),
  fig4 (R344 endpoints), fig5 (R350 oracle), fig7 (R363 feasibility) with
  finding-first captions written from the draft prose (no
  `figures_source_manifest.md` exists); **fig6 is NOT included** (family
  results live as Table II). Each data figure caption carries a source
  pointer to its results JSON (per assembly-plan step 3); fig2 is the
  protocol flowchart and has no results-JSON source.

## Citation-sequence mapping (memo number -> paper number)

Renumbered by first appearance in the assembled paper. 41 of 43 memo
references are cited in the draft prose; memo [39] (Xu et al.) and [43]
(Witsenhausen) are not cited by any draft and are retained in
`references.bib` only (bibtex drops them from the printed list, so the
rendered bibliography is [1]–[41]).

| memo | paper | memo | paper | memo | paper |
|---|---|---|---|---|---|
| 1 | 4 | 16 | 18 | 31 | 7 |
| 2 | 5 | 17 | 12 | 32 | 1 |
| 3 | 11 | 18 | 13 | 33 | 2 |
| 4 | 8 | 19 | 22 | 34 | 3 |
| 5 | 29 | 20 | 25 | 35 | 24 |
| 6 | 30 | 21 | 27 | 36 | 19 |
| 7 | 16 | 22 | 26 | 37 | 20 |
| 8 | 14 | 23 | 28 | 38 | 21 |
| 9 | 35 | 24 | 9 | 39 | uncited (bib only) |
| 10 | 34 | 25 | 10 | 40 | 40 |
| 11 | 15 | 26 | 32 | 41 | 39 |
| 12 | 36 | 27 | 31 | 42 | 41 |
| 13 | 17 | 28 | 33 | 43 | uncited (bib only) |
| 14 | 37 | 29 | 6 | | |
| 15 | 38 | 30 | 23 | | |

## W4 gate (assembly-plan step 4) — PASS, no drift

Headline numbers verified identical across the assembled tex at the
required locations (values verbatim from drafts):

| Number | Locations |
|---|---|
| 95.5% / 99.3% | Abstract, Section I, Section V-A, Section VIII (+ fig4 caption) |
| 1.7e-9 ($1.7\times10^{-9}$) | Abstract, Section I, Section V-B, Section VII-A, Section VIII (+ fig5 caption) |
| 16/16 vs 10/16 | Abstract, Section I, Section VI, Section VIII (+ fig7 caption) |
| 0.130 / 0.087 | Section IV-C (methods; single home as drafted) |
| 1.11%–3.90% | Section IV-B (+ fig3 caption) |

No drift introduced.

## Content-fidelity notes / decisions taken

1. **Numbered-equation set (assembly-plan review finding 4.1)**: all
   seven equations are numbered and prose-referenced, but physical order
   of appearance fixes the numbers: (1) DAE plant, (2) GENCLS swing,
   (3) ESD1 lag/achieved power, (4) tree-edge residual + zero-common
   condition (Section III-D, appears before IV-C), (5) common/differential
   coordinate transform, (6) separate-input plant model, (7) joint-endpoint
   QP. The plan's enumeration "(4) transform, (5) separate-input,
   (6) tree-edge" does not match the draft's section order; automatic
   numbering by appearance was used so numbers stay monotonic and all
   `\ref`s resolve.
2. Equation (7) (joint-endpoint QP) is rendered from the feed language
   (R356/R358/R363: minimize normalized differential squared-error subject
   to the ≥2% common endpoint target and exact physical limits), with
   notation (`\bar e_c`, `\bar e_d`, `C_phys`) defined in prose; no new
   numbers introduced.
3. Equation (3) uses the model-contract executable form
   `T_ip·d(I_p,out)/dt = I_p,cmd − I_p,out`, `P_grid = v·I_p,out`
   (same content as the draft's `T_ip I_p' = I_p,cmd − I_p` plus the
   achieved-power part required by the plan's "(3) ESD1 active-current lag
   and achieved power").
4. Citations added at assembly per the methods draft's delivery note:
   Kundur textbook [41] at "modified Kundur two-area" (III-A), ANDES
   framework paper [40] at "ANDES 2.0.0" (III-A), OSQP [42] at the
   "direct quadratic program (QP) solve" (IV-D). No other citations were
   added, moved, or dropped; the intro draft's own subset numbering was
   ignored as instructed.
5. "Table III.1" prose references in the methods draft became
   `Table~\ref{tab:nodes}` (the table is Table I in the assembled paper).
6. Figure source paths are typeset via `\urldef` aliases because `\url`
   cannot be used inside `\caption` (moving argument); control-sequence
   names are letter-only. Paths are unchanged strings.
7. Full-width figures (fig1, fig4, fig7) use `figure*` and equation (7)
   is split across two `aligned` lines — pure layout fixes for the
   two-column class; no content change.
8. bibtex warning "empty author in unifi2024specifications" fixed by
   authoring the entry to `{UNIFI Consortium}` (the memo's own
   attribution); no other bib change beyond formatting.
9. `IEEEkeywords` left empty (commented) — no keyword content exists in
   the drafts; pending PI/venue pass.
10. Open human items from the memo (full-text verification of specific
    works, author-list confirmation for [25], [40], edition for [41])
    are unchanged and remain outside this mechanical pass.

## Remaining for the supervisor

- Register the package artifacts (main.tex, references.bib, main.pdf,
  this report) per the line's ARTIFACTS.json.
- PI title/author/keywords sign-off before venue Pass 2/3.
