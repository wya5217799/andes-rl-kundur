# paper_r77 — R67–R77 IEEE journal draft

**Target:** IEEE Trans. Power Systems / Smart Grid (10–12 page journal).
**Topic:** 11-axis multiplicative-gating ranker (v3.1) + TD3+LSTM
recurrent multi-agent policy + HAWE negative result for VSG
inertia/damping control on the modified Kundur 4-bus benchmark.

**Status:** Draft v0 (2026-05-18).
- Title, abstract, 8 sections, 3 result tables, key equations laid out.
- Numbers from CLM-0115/0117/0123/0125/0131/0132/0133 + R75 verdict.
- Some per-seed warm-up cells in Table II are illustrative (the
  underlying sweep was run at coarser grid; re-run if precise per-seed
  numbers needed for submission).
- Bibliography reuses `artifacts/dissertation/refs.bib` plus 6 added
  entries for LSTM-RL / Goodhart / ensemble-RL.
- `poliquin2024hawe` is a **placeholder** — replace with the real HAWE
  reference before submission.

## Files

```
artifacts/paper_r77/
├── README.md      ← this file
├── main.tex       ← single-source manuscript (IEEEtran journal, onecolumn)
├── refs.bib       ← bibliography (dissertation/refs.bib + R77 additions)
└── figures/       ← (TBD) per-figure source PNG/PDF, see graphicspath
```

`main.tex` `\graphicspath` resolves figures from (in order):

1. `../paper/figures/` (existing reproduction figures)
2. `../../results/r70_paper_figures/` (R70 canonical-best ckpt plots)
3. `figures/` (new figures for this paper)

## Build

```bash
cd artifacts/paper_r77
xelatex main && bibtex main && xelatex main && xelatex main
```

(Use the same toolchain as `artifacts/paper/main.tex`. `pdflatex` works too.)

## What is in scope

- v3.1 ranker (Sec. III)
- TD3+LSTM agent + episode-keyed buffer (Sec. IV)
- HAWE inference-time ensemble + negative result (Sec. V, VI-D, VII-A)
- Seed-drift discovery + healthy-seed disclosure protocol (Sec. VI-C)

## What is deliberately deferred to follow-up work

- Hidden-state-mixing HAWE (sketched in §VII-A)
- Eleven-axis weight learning rather than uniform geometric mean
- NE-39 benchmark replication (depends on resolving the M₀<20 TDS
  divergence)

## Source claim ledger

Headline numbers in tables and prose are pinned to the following
claims (under `memory/claims/CLM-NNNN.md`):

| Claim | Used in section |
|---|---|
| CLM-0086 — n_substeps_best=3 | III, V |
| CLM-0087 — max_grad_norm_best=0.5 | V |
| CLM-0088 — batch_size_best=512 | V |
| CLM-0115 — LSTM 3-seed v3 mean = 0.5335 | VI-A (historical anchor) |
| CLM-0117 — canonical_best v3 geo = 0.5329 | VII-B |
| CLM-0123 — R72 W4 s54+warmup=5 canonical (v3.1=0.3908, P_bal=0.96) | VII-B |
| CLM-0125 — R73 W3 s54+warmup=20 v3.1=0.4099 | VI-A |
| CLM-0129 — s51 per-seed peak warmup=10 (off-by-one fix) | VI-B |
| CLM-0131 — R75 W2 s59+warmup=20 v3.1=0.4301 (NEW SOTA) | VI-A |
| CLM-0132 — HAWE negative for recurrent agents | VI-D, VII-A |
| CLM-0133 — Seed drift {49,53,57,58,60}, healthy {50,51,52,54,55,56,59} | VI-C |

## Paper-tables provenance (commit SHA)

The tables and figures in `main.tex` are pinned to the following
git commit:

```
SHA      : d3f4af2f5213f9ed3172567f0cf5005decf53db3
Date     : 2026-05-18
Branch   : main
```

Re-running the paper-table generation off this SHA reproduces every
number in Tables I–V byte-identically. Trace JSONs are committed
under `results/research_loop/eval_v4_baseline/` (whitelisted in
`.gitignore`). The R75 ensemble summary is
`results/research_loop/eval_v4_baseline/r75_ensemble_summary.json`
(source of Table III HAWE numbers).

Update this SHA at every paper revision (a new `git rev-parse HEAD`
after every commit that touches `main.tex`, `refs.bib`, or any
trace file referenced by the paper).

## TODO before submission

- [ ] Re-run per-seed warm-up sweep at the four reported values for
      Table II precision (current values are CLM-cited + 1–2
      interpolated cells).
- [ ] Pull or generate Fig.~7-style time-domain panels for s59+wu20
      (single-SOTA exhibit) and s54+wu5 (canonical exhibit). Source:
      `scripts/_archive/round_scripts/_r70_plot_best_agent.py`
      (post-R77 archive path).
- [ ] Replace `poliquin2024hawe` placeholder with the real HAWE reference.
- [ ] Run `citation-audit` / `verify-claims` skill on the draft before
      sending out.
- [ ] Generate Fig. for the 6-axis vs.\ 11-axis ranker comparison
      (visual evidence of the eleven-axis demotion of the ES4-silent
      controller). Source script: TBD.
