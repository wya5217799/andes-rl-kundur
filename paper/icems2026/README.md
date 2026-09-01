# ICEMS 2026 full paper

The title is intentionally unchanged from the submitted digest. ADR-0022
reactivates this line for a bounded positive-core manuscript repair and, only
after a no-execution gap audit, at most one prospectively gated small
supplement. The paper reports the completed R274--R280 evidence chain. The formal result uses three
predefined seeds, a prospectively generated fresh disturbance bank, and a
size-matched centralized TD3 baseline. It supports learned differential
allocation and shows that the tested scalar parameter-sharing factorization is
meaningfully effective but inferior to the centralized actor. It does not
support an architecture-wide conclusion about MARL. No additional experiment
is required to defend this manuscript core.

Supplementary work is deliberately small-step: one falsifiable development
question at a time, followed only when warranted by one separately authorized
and prospectively frozen evidence round. Development results cannot be relabelled
as confirmatory evidence. This restart does not authorize training, ANDES,
algorithm sweeps, or a 200-cell-scale batch. The model-first line is a read-only
source of mechanism definitions, implementation ideas, deterministic-baseline
design, and stop gates; its numerical results do not transfer into this paper.

Regenerate the evidence macros and vector result figures from the fixed
summaries and retained trajectories:

```powershell
python build_figures.py
```

The dynamic-response scenario is selected without inspecting controller
outcomes: it is the first moderate-severity case in the formal-bank manifest
order. The rule and source hashes are written to
`working/dynamic_response_selection.json`.

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
- do not add MARL superiority, dynamic-decoupling, unified-GFM-BESS, EMT,
  stability, topology-generalization, or deployment claims without new
  evidence.

The full-paper instructions and deadline should be rechecked immediately before
uploading at <https://www.icems2026.org/full-paper-submission/>. The page was
last checked on 2026-07-26 and listed 2026-08-24 as the final-paper deadline.
