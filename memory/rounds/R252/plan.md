---
round: R252
state: active
opened: '2026-05-20'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R252 plan — Classical baseline (droop) dual-metric audit (CLM-0186 cross-check)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, classical-baseline dual-metric audit)
**Driver**: This session's CLM-0430 dual-metric audit revealed paper
Eq.14 reward terms contribute 3-6% on cum_rf even when vestigial
on 11-axis. The R85 classical-vs-RL comparison (CLM-0186 "RL beats
droop 2.1×") was authored pre-CLM-0430, citing only `geo`. R85's
own summary.json already contains cum_rf data for every droop k,
which spot-check shows **reverses the conclusion on paper-metric**:
droop k=2.0 cum_rf = -0.0641, RL SOTA (R201) cum_rf = -0.0692
(droop 8% better on cum_rf). R252 formalises this dual-metric
audit, writes the corrected CLM-0186 supersede, and updates the
gauge-invariance memo with the "RL vs droop" dual-metric panel.
**Parent**: CLM-0186 (R85), CLM-0430 (dual-metric audit).

## TL;DR

No new training. R252 is a re-analysis round:
1. Re-load R85's full droop scan from
   `results/r85_classical_baseline/r85_classical_baseline_summary.json`
2. Cross-tab against R201/R72_w4/R239 SOTA controllers (already
   measured cum_rf via earlier CLM-0440 anchor) on BOTH metrics.
3. Write CLM-0445 superseding CLM-0186 with the dual-metric table.
4. Update `docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md`
   to add the "classical vs RL dual-metric" panel.

## Methodology

```bash
# Load R85 droop scan + RL SOTA cum_rf via baselines.py
python memory/tools/baselines.py --filter "r201_w1_hreg|r72_w4|r239" --sort cum_rf
# Read R85 nested droop scan directly
python -c "
import json
d = json.load(open('results/r85_classical_baseline/r85_classical_baseline_summary.json'))
for run in d['droop_all']:
    print(f'k={run[\"k_droop\"]:5.1f}  geo={run[\"geo\"]:.4f}  cum_rf={run[\"cum_rf\"]:+.4f}')
"
```

No env / train / score code touched. Pure analysis.

## Pre-registered outcomes (dual-metric)

Pre-registered framing for the cross-tab:

| Comparison | geo (11-axis) outcome | cum_rf outcome |
|------------|------------------------|------------------|
| Droop best vs R201 SOTA | geo ratio (R201/droop): expect ~2.1× per CLM-0186 | cum_rf ratio: expect droop slightly better (~6-8%) per spot-check |
| Droop best vs R239 (scalar+only-phi_abs) | expect ~2× | expect droop slightly better |
| Droop k-sweep monotonicity | expect non-monotone (sweet spot at k≈2-5) | expect bowl shape; minimum (best) at moderate k |

**Decision rules**:
- If cum_rf differences > 3% (above noise): **document as a second
  dual-metric divergence finding, write CLM-0445 superseding CLM-0186**.
- If cum_rf differences < 3% (within noise): keep CLM-0186, add a
  dual-metric annotation as supplementary not supersede.
- If unexpected (droop dominates on BOTH metrics, or RL on both):
  **investigate before committing** — could be ranker drift since R85.

## Connection to paper claim structure

R85's "RL beats droop 2.1×" finding is paper Sec.IV-D primary
contribution 1. If R252 confirms cum_rf inversion, the paper claim
becomes **"RL beats droop on transient/utility (11-axis) but
droop beats RL on synchronization tightness (cum_rf)"** — a more
nuanced and honest framing, matching the paper-Eq.14 dual-metric
contribution 5 structure.

## Cross-references

- R85 classical baseline (CLM-0186 — what this audits)
- CLM-0430 (methodological dual-metric audit — same pattern)
- CLM-0435 (R251 scalar s50 anchor — measured > estimated lesson)
- CLM-0440 (R72_w4 anchor — gives SOTA cum_rf for comparison)
- `docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md`
