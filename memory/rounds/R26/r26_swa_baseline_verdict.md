# r26 — B-6 SWA / model-soup baseline verdict

**Date**: 2026-05-07
**Probe**: `scripts/research_loop/eval_swa_baseline.py`
**Raw output**: `results/research_loop/r26_swa_manifest.json`
              + `results/research_loop/eval_v4_baseline/ddic_v4_swa_w*_load_step_{1,2}.json`
**Wall**: ~9 min (5 weight points × ~100 s eval each + ranking ~30 s; faster
          than estimated because ckpt merge is in-process)
**Status**: **COMPLETE**. Verdict = **partial novelty** (HAWE = SWA at the
sweet spot but HAWE is robust off-sweet-spot where SWA collapses).

---

## TL;DR (UPDATED 2026-05-07 after ranker B1+B2 fix in `paper_grade_axes.py`)

> All numbers below are **post-ranker-fix** (own-final settling band +
> full-trace window — see r28 §V4). The pre-fix numbers are quoted at the
> end of the table for reference; they are **NOT** the headline.
>
> **Sweet spot (w ≥ 0.95)**: SWA ≈ HAWE within 1 % (SWA w98 = 0.442 vs
> HAWE 98/2 = 0.439, diff +0.003). DA-CRIT-1 lineage-circularity claim
> **confirmed at the headline weight**.
>
> **Off-sweet-spot (w ≤ 0.80)**: SWA still trails HAWE, but the gap is
> much smaller after the ranker fix:
>
> | w_R21 | SWA   | HAWE  | rel diff (post-fix) | rel diff (pre-fix, retracted) |
> |------:|------:|------:|--------------------:|------------------------------:|
> | 0.50  | 0.290 | 0.331 | **-12.4 %**         | (-38.8 %)                      |
> | 0.80  | 0.398 | 0.405 | **-1.7 %**          | (-26.8 %)                      |
>
> So HAWE's "off-sweet-spot niche" *survives* the ranker fix but is much
> weaker: a 12 % advantage at w=0.50 instead of 39 %. **Decision**: HAWE
> still keeps a partial novelty claim, but the strength of the SWA-vs-HAWE
> argument in the paper has to be downgraded from "27-39 % collapse" to
> "1-12 % gap that narrows toward the sweet spot". The paper must still
> cite Izmailov 2018 / Wortsman 2022 (panel CONS-3) but the §VI-B'
> SWA-baseline narrative needs to acknowledge the gap is small.
>
> **Why the pre-fix numbers were misleading**: the old ranker used a
> paper-target settling band that R21's own-final (~0.057 Hz) sat
> comfortably inside, giving R21-aligned controllers a happy 0.65
> settling score and pushing all SWA-derivative scores higher than they
> deserved. The fix exposes that *neither* SWA nor HAWE survives the
> 7 s settling residual at the paper-anchor 3 s tolerance.

---

## SWA vs HAWE comparison table — POST-RANKER-FIX (authoritative)

| w_R21 | SWA 6-axis | HAWE 6-axis | abs diff | rel diff |  DA-CRIT-1 implication                                                |
|------:|-----------:|------------:|---------:|---------:|-----------------------------------------------------------------------|
| 0.50  | **0.290**  | 0.331       | -0.041   | -12.4%   | SWA still trails; gap much smaller post-fix (was -38.8%)               |
| 0.80  | **0.398**  | 0.405       | -0.007   | -1.7%    | Near-parity post-fix (was -26.8%)                                      |
| 0.90  | **0.428**  | 0.424       | +0.004   | +0.9%    | SWA marginally ahead — both inside R21 basin                           |
| 0.95  | **0.437**  | 0.433       | +0.004   | +0.9%    | Tied (noise-level)                                                     |
| 0.98  | **0.442**  | 0.439       | +0.003   | +0.7%    | **Decisive row**: tied → DA-CRIT-1 confirmed at the headline weight    |

Reference anchors (post-fix):
- R21 alone (w_R21 = 1.00): **0.444** (was 0.613 pre-fix)
- ws8 alone (w_R21 = 0.00): **TBD** (need re-rank; pre-fix was 0.419)
- no-control floor: 0.110 (no ddic axes; unchanged)

### Pre-fix numbers (RETRACTED — kept for reference)

| w_R21 | SWA pre | HAWE pre | abs diff | rel diff |
|------:|--------:|---------:|---------:|---------:|
| 0.50  | 0.290   | 0.474    | -0.184   | -38.8%   |
| 0.80  | 0.398   | 0.544    | -0.146   | -26.8%   |
| 0.90  | 0.588   | 0.552    | +0.036   | +6.5%    |
| 0.95  | 0.605   | 0.602    | +0.003   | +0.5%    |
| 0.98  | 0.610   | 0.607    | +0.003   | +0.5%    |

The pre-fix numbers came from `paper_grade_axes.py` before the B1
(window) + B2 (band-target) fixes documented in r28. The pre-fix ranker
inflated all R21-adjacent controllers via a happy band-centring artifact
(R21 own-final 0.057 Hz fits inside the paper-target ±0.02 Hz band that
spans 0.06-0.10 Hz). Once the band is centred on each controller's own
residual the inflation goes away and SWA-vs-HAWE separation collapses.

---

## Plot in prose: "robustness band"

```
   6-axis
   0.7 |
   0.6 |  R21=0.613    ┌─────────●━━━━●  SWA  (w=0.95,0.98)
       |               │            ●━━━━━━━━━━━━━━━━━ R21 (w=1.00)
   0.5 |  HAWE band ━━━│━━━━━━━━━━━━●━━━━●━━●  HAWE (w=0.50..1.00)
       |               │
   0.4 | ws8=0.419 ●   │
       |             ● │  SWA (w=0.80)
   0.3 |               │
       |          ● SWA (w=0.50)
   0.2 |
       └─────────────────────────────────────────
        0.0   0.5     0.8     0.9    0.95  1.0   w_R21
```

HAWE's curve crosses 0.474 at w=0.50 and stays above 0.484 across the
full simplex; SWA drops to 0.290 at w=0.50.

---

## Per-axis decomposition (decisive row, sweet spot)

Rank table top excerpt from `paper_grade_axes.py`:

```
Rank  Label                                  6-axis
   1  ddic_v4_h50_s49                        0.613   <-- R21
   2  ddic_v4_swa_w98                        0.610   <-- SWA decisive row
   3  ddic_v4_ens2_R21ws8_w9802              0.607   <-- HAWE decisive row
   4  ddic_v4_swa_w95                        0.605
   5  ddic_v4_ens2_R21ws8_w9505              0.602
   ...
   7  ddic_v4_swa_w90                        0.588
  10  ddic_v4_ens2_R21ws8_w9010              0.552   <-- HAWE @ 0.90
   ...
  35  ddic_v4_swa_w80                        0.398
  12  ddic_v4_ens2_R21ws8_w8020              0.544   <-- HAWE @ 0.80
   ...
  43  ddic_v4_swa_w50                        0.290
  22  ddic_v4_ens2_R21ws8_mean (=w50)        0.474   <-- HAWE @ 0.50
  120  no_control                            0.110
```

The full rank ordering is in the pipeline log; per-axis JSON is in
`results/research_loop/eval_v4_baseline/ddic_v4_swa_w98_load_step_{1,2}.json`.
A per-axis table can be regenerated with
`paper_grade_axes.py --json` (if needed for paper revision; not extracted
here to stay within scope).

Action-range axis (DA-CRIT-3): structurally 1.0 for SWA and HAWE alike
because env action space `ΔH ∈ [-5, +15]` never saturates the paper Eq.12
box `[-100, +300]`. Confirmed identical, do not over-interpret.

---

## Verdict

### V1 — Lineage circularity (DA-CRIT-1)

**Confirmed at the headline weight** (98/2). SWA w98 = 0.610 vs HAWE 98/2
= 0.607. Both are within 1% of R21 = 0.613 and within 0.5% of each other.
This is mathematically expected: ws8 = R21_final + 100-ep SAC update with
the same seed 49 (cookbook Path B, lines 78-94), so the perturbation δ
between R21 and ws8 is small in θ-space. With 2% mass on δ, both θ-mixing
and action-mixing land on essentially R21. The paper's "99.0% recovery"
is not a method claim at this row — it is a lineage tautology.

### V2 — HAWE has a real action-space niche off-sweet-spot

**Confirmed**. At w_R21 ≤ 0.80, SWA collapses (0.398 at w=0.80, 0.290
at w=0.50) while HAWE degrades smoothly (0.544 at w=0.80, 0.474 at
w=0.50). The 27-39% gap exceeds any plausible eval noise (deterministic
inference, single seed, no MC variance). Because the actor is
`tanh(MLP(o))`, action-space mixing is **not** equivalent to θ-mixing
once the two θ are not linearly close: SWA produces an MLP whose output
distribution is no longer in the convex hull of the two endpoint actor
outputs, while HAWE's action mixing always is by construction.

### V3 — Manuscript implications

The current paper draft (`毕业论文/plan/2026-05-07_andes_ieee_paper.md`,
§II-C "Ensemble Methods in Deep Reinforcement Learning") cites Wiering &
van Hasselt 2008 but **does not cite SWA / Model Soups**. This is a
factual gap that the panel correctly flagged (Perspective MAJOR-1, EIC
concern 2, panel CONS-3). The §VI-B HAWE sweet-spot table needs a
column for SWA at the same weights, and §VII-A "What does HAWE buy us?"
needs a fifth bullet on **off-sweet-spot robustness vs SWA**.

### V4 — Decision-tree branch (per `2026-05-07_path_B_execution.md` §2)

| Branch                                                          | Outcome | Action                                                                                                       |
|-----------------------------------------------------------------|---------|--------------------------------------------------------------------------------------------------------------|
| SWA ≈ HAWE everywhere (< 1% diff at all 5 w)                    | NO      | not the actual outcome                                                                                       |
| SWA tails diverge from HAWE (sweet spot tied, off-spot collapse) | **YES** | *Partial novelty*: HAWE keeps method claim only as "robust action-space ensemble"; cite SWA baselines.       |
| SWA all > HAWE                                                  | NO      | not the actual outcome                                                                                       |
| SWA all < HAWE by > 5%                                          | NO      | partially: only off-sweet-spot                                                                               |

→ **Branch 2 (Partial novelty)** activated.

---

## Next-step recommendations (priority-ordered)

| #   | Action                                                                                                                                                                                                     | Effort | Decides                                                                                                |
|-----|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|--------------------------------------------------------------------------------------------------------|
| N1  | Update paper §II-C: add SWA + Model Soups citations + 1-paragraph contextualisation of action-space-vs-weight-space mixing. Add §VI-B' subsection with the 5-row SWA-vs-HAWE table from this verdict.       | 2-4 h  | Direct response to panel CONS-3 + Perspective MAJOR-1; goes into next paper revision.                  |
| N2  | Re-frame paper §VII-A bullet 4 ("Negative-space anchor") + add a fifth bullet **"Off-sweet-spot robustness vs weight-space averaging"** quoting the 27-39% SWA collapse vs HAWE's smooth degrade.            | 1 h    | Same revision round.                                                                                   |
| N3  | If panel further pushes on lineage: run **B-2 fresh-seed actor** (independent seed 50/51/52 × 200 ep) + repeat HAWE + SWA both at the headline weight to test whether the 0.5% tie persists for non-lineage actors. | 1-2 d  | Whether DA-CRIT-1 also fires for fresh-seed pairs — would settle the lineage critique definitively.    |
| N4  | Sweep SWA at intermediate weights (0.92, 0.96) to localise where SWA ≈ HAWE transitions to SWA collapse. May reveal a sharper threshold than HAWE's smooth band, useful for the §VI-B narrative.            | 1 h    | Whether SWA's collapse boundary is sharper than HAWE's (additional defense argument).                  |
| N5  | (Out of scope for A2) Paper-side §IV-C "Why HAWE Helps" needs to be re-written as "Why HAWE is more robust than SWA" with the action-space non-linearity argument, citing the off-sweet-spot evidence.       | 4-6 h  | Restructured §IV-C in next revision. Defer to writing group.                                           |

---

## Files written

```
quality_reports/research_loop/r26_swa_baseline_verdict.md            ← this
results/research_loop/r26_swa_manifest.json                          ← 5 w × eval manifest
results/research_loop/eval_v4_baseline/ddic_v4_swa_w{50,80,90,95,98}_load_step_{1,2}.json  ← 10 trace JSONs
results/v4_swa_w{50,80,90,95,98}/agent_{0..3}_best.pt                ← 20 merged ckpts
scripts/research_loop/eval_swa_baseline.py                           ← driver
```

---

## Reproducibility

```bash
wsl -e bash -c "cd '/mnt/c/Users/27443/Desktop/Multi-Agent  VSGs' && \
    /home/wya/andes_venv/bin/python scripts/research_loop/eval_swa_baseline.py"
```

Add custom weights:

```bash
... eval_swa_baseline.py --weights 0.92 0.96 0.99 --force
```

The `--force` flag re-merges existing checkpoints (otherwise skips).

---

*Generated 2026-05-07 by code-probe dispatch group A2 (B-6). Verdict derived
from 5 SWA evaluation traces + paper-grade ranking. The "partial novelty"
finding is the strongest defensive position for HAWE-as-method available
without further training, and is independent of B-2 (fresh-seed) outcomes.*

---

## §X. Claim + Falsification (per O1 protocol)

### Claim

> Weight-space averaging (SWA / model-soups, Izmailov 2018, Wortsman 2022) of R21 + ws8 produces a controller within **+0.7%** of action-space HAWE at the headline w_R21 = 0.98 sweet spot (SWA 0.442 vs HAWE 0.439, post-ranker-fix), confirming that **HAWE-at-sweet-spot is structurally equivalent to a SWA variant** (panel DA-CRIT-1 lineage-circularity confirmed at the headline weight). Off-sweet-spot at w_R21 = 0.50, HAWE retains a **−12.4%** advantage that survives the ranker fix, so HAWE preserves a **partial novelty claim** as an off-sweet-spot ensembling strategy — much weaker than the pre-ranker-fix gap (39%) suggested.

### Falsification

| 维度 | 条件 | status |
|---|---|---|
| **F-Independence** | K independent training trajectories underlying the SWA-vs-HAWE comparison? | **K=1 trajectory** (R21 single seed) + **K=1 finetune** (ws8 = R21 same seed + 100ep). The "ensemble" is two checkpoints from the same trajectory — DA-CRIT-1 lineage circularity. The SWA-vs-HAWE comparison does NOT independently sample the actor space; it tests whether two averaging operators behave similarly on the same R21+ws8 pair. **B-2 (fresh-seed) is the only experiment that resolves true independence.** |
| **F-Coverage** | Did the weight sweep cover the regime where SWA might fail? | 5 points (w∈{0.5, 0.8, 0.9, 0.95, 0.98}). No w<0.5 (ws8-dominant regime) and no fine-grained sweep around the SWA-vs-HAWE crossover at w=0.85-0.90. **Adequate coverage** in the w_R21 ≥ 0.5 regime; the w<0.5 regime is irrelevant because both SWA and HAWE collapse there toward ws8-alone (0.419 pre-fix). |
| **F-Counterfactual** | Compared to "average a random untrained actor with R21" baseline? | **Not run.** Without this null, the SWA-vs-HAWE comparison cannot rule out "any averaging operator preserves R21 within 1%" as a generic property. The pre-fix 39% gap was strong enough to override this concern; the post-fix 1% gap is not. **Should run a random-actor baseline before paper claims SWA = HAWE.** |
| **F-Generalization** | Holds for a different actor pair (R21 + R30-ensemble member, R21 + r33K, ...)? | Not tested. K=1 actor pair (R21 + ws8). Until B-2 produces fresh-seed actors, generalization is undetermined. |
| **F-Robustness** | Eval noise envelope < 0.7% effect at w=0.98? | ANDES TDS deterministic; 6-axis ranker arithmetic deterministic. Estimated noise std ≤ 0.5%. **Robust at the sweet-spot crossover** (0.7% diff), **questionable** at intermediate w where the diff may shrink to noise. |

### Killshot

> If "SWA ≈ HAWE at w=0.98" is true precisely BECAUSE the underlying R21 and ws8 are non-independent (DA-CRIT-1 confirmed), then both averaging operators are testing the trivial property "0.98 of X plus 0.02 of (X + small δ) ≈ X under any monotone aggregator". The 1% near-tie at the sweet spot is then NOT evidence that "HAWE is a SWA variant" — it is evidence that "the actor pair is degenerate, so all averaging methods produce R21". **The fresh-seed B-2 experiment is the ONLY way to disambiguate**: if SWA and HAWE diverge under fresh-seed pairs, both methods are real; if they converge again, both are tautological. Until B-2 lands, the partial-novelty claim is **provisional**.

### Independent verification path

- [ ] **B-2 fresh-seed actor** (seed 50/51/52 × 200 ep) — repeat the SWA-vs-HAWE 5-point sweep with R21 + fresh-seed pair. Resolves DA-CRIT-1 + this tautology concern.
- [ ] Random-actor counterfactual: `theta_rand = 0.98 * theta_R21 + 0.02 * theta_random_init`. Should collapse to R21-class score if R21+ws8 result is degenerate; should drop sharply if R21+ws8 has real diversity.
- [ ] Ranker re-validation: spawn fresh-context claim-verifier on `paper_grade_axes.py` post-fix vs pre-fix to confirm the band-target inflation mechanism.


## Questions opened (this round)
- none (retrofit — this verdict pre-dates the Q entity introduced in R39)

## Questions closed (this round)
- none (retrofit)

## Questions advanced (this round, status unchanged)
- none (retrofit)
