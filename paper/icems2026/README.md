# ICEMS 2026 full paper

The title is intentionally unchanged from the submitted digest. The paper
reports the completed R274--R278 evidence chain and treats the R278 seed-49
pilot as a prospective no-go for overall adaptive MARL value. No additional
experiment is required for this manuscript version.

Regenerate the evidence macros and vector result figure from the frozen
summaries:

```powershell
python build_figures.py
```

Build from this directory with MiKTeX:

```powershell
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The checked submission artifact is copied to:

```text
output/pdf/icems2026_full_paper.pdf
```

Before uploading:

- keep the paper between 4 and 6 A4 pages and omit page numbers;
- add the conference copyright notice only when the organizers provide it;
- run the final file through IEEE PDF eXpress (conference ID `69927x`);
- do not add multi-seed, unseen-disturbance, unified-GFM-BESS, EMT, stability,
  topology-generalization, or deployment claims without new evidence.

The full-paper instructions and deadline should be rechecked immediately before
uploading at <https://www.icems2026.org/full-paper-submission/>. The page was
last checked on 2026-07-26 and listed 2026-08-24 as the final-paper deadline.
