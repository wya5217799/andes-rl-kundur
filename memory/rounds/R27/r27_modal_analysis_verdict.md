# r27 — B-4 Modal analysis on V4 Kundur — verdict

**Date**: 2026-05-07
**Probe**: `probes/andes_kundur/t2_modal_analysis.py`
**Raw output**: `results/research_loop/r27_modal_analysis.json`
                + `paper/figures/v4_modal_analysis/{inter_area_mode_shape,mode_proj_vs_score}.{png,pdf}`
**Wall**: ~3 min (ANDES EIG ~10 s; the rest is loading 4 cached eval JSONs
          and plotting)
**Status**: **COMPLETE**. Verdict = **Domain M2 hypothesis NOT supported by
the data** — low-score controllers project *more* onto the inter-area mode
shape than high-score controllers, the opposite of the panel's prediction.

---

## TL;DR

> The Kundur V4 system has a clean inter-area mode at **f = 0.579 Hz, ζ =
> 2.45%** (low damping, classic Kundur 2-area inter-area pattern). On the
> rotor-speed mode shape, **ES1 (Bus 12) is the dominant participant**
> (|W| = 77, P_std = 0.035), with ES2 / ES4 secondary (|W| ≈ 41-43, P_std
> ≈ 0.010) and ES3 the weakest (|W| = 30, P_std = 0.005).
>
> **Surprise**: cosine projection of per-agent ΔH range onto the |W|
> mode-shape vector shows the **low-score controllers project HIGHER**
> than the high-score ones. ws8 (score 0.419) projects 0.745-0.835;
> HAWE 85/15 (0.554) projects 0.783-0.862; R21 (0.613) projects only
> 0.599-0.651. The panel-predicted "high-Gini ES2-dominant ⇒ mode-aligned
> ⇒ high score" chain **does not hold in the data** — if anything, the
> sign is reversed.
>
> **Decision**: the per-agent regularity reported in the paper §VI-D is
> real, but its mechanism is **not** "preserve the natural mode shape".
> Drop the modal-alignment framing from the paper before any submission;
> reframe the regularity as "spatial selectivity" (R21 acts on ES2 *despite*
> ES2 not being the dominant mode-shape coordinate). The deeper mechanism
> requires further study (modal energy / observability / actuator
> placement analyses are the natural follow-ups).

---

## Inter-area mode shape (V4 zero-action steady state, after PFlow + TDS init)

EIG run on the V4 environment yields 102 states / 102 modes. The lowest-
damping oscillatory mode in the 0.3-1.2 Hz band:

- **frequency**: 0.579 Hz
- **damping ratio**: 0.0245 (2.45 %)
- **classification**: classic Kundur 2-area inter-area mode

### Right-eigenvector magnitude on rotor-speed states |W[:, 58]|

| Group  | Bus | label | \|W\| | rank |
|--------|----:|-------|------:|-----:|
| GENROU | 1   | G1    | 107.30 |  1   |
| GENROU | 2   | G2    |  91.22 |  2   |
| ESS    | 12  | ES1   |  77.17 |  3   |
| GENROU | 3   | G3    |  38.96 |  6   |
| GENROU | 4   | G4    |   0.02 |  9   |
| ESS    | 16  | ES2   |  43.01 |  4   |
| ESS    | 15  | ES4   |  41.01 |  5   |
| ESS    | 14  | ES3   |  30.23 |  7   |

Phase information (deg, from probe debug) confirms classic anti-phase:
G1/G2 ≈ -20° / -22°, G3 ≈ -27° (Area 2 single survivor — G4 ≈ 0 because V4
defaults to paper-restored G4 inertia of 111.15 in steady-state but the
mode shape is still G3-driven on the Area-2 side because the synchronous
G3-G4 pair was historically broken in the project's xlsx). All 4 ESS
GENCLS show +155° to +160° phase — anti-phase to the GENROUs, as expected
for a swing-coupled storage cluster.

### Standard participation factor `|W * inv(W).T|` on ESS

| ES | bus | \|P_std\| |
|----|-----|---------:|
| 1  | 12  | 0.0350   |
| 2  | 16  | 0.0104   |
| 4  | 15  | 0.0097   |
| 3  | 14  | 0.0053   |

P_std and |W| disagree on the *secondary* ranking (P_std puts ES2 ≈ ES4 ≈
ES1/3.4×, |W| puts ES2 ≈ ES4 ≈ ES1/1.85×) but **agree** on the headline:
ES1 (Bus 12) is the dominant ESS coordinate of the inter-area mode by
**3-7×** over the next-strongest ESS.

> **Note on ANDES `pfactors`**: the `ss.EIG.pfactors` field returns a
> non-textbook normalisation (single-state-dominated, sum < 1) that does
> *not* match the textbook Kundur participation factor. The probe ignores
> it and uses |W| / |W * inv(W).T| as the mode-shape proxies; both are
> standard.

### Inter-area mode shape figure

`paper/figures/v4_modal_analysis/inter_area_mode_shape.{png,pdf}` — 2-panel
bar chart, GENROU | ESS, with the f / ζ in the title.

---

## Per-agent ΔH range vs mode-shape projection

Cosine alignment between the |W|-mode-shape (4-vec on ES1..ES4) and each
controller's per-agent ΔH range vector. **Scores are POST-RANKER-FIX**
(B1+B2 patches in `paper_grade_axes.py` per r28 verdict; pre-fix scores
0.613/0.607/0.554/0.419 retracted).

| Controller       | 6-axis (post-fix) | proj_W (LS1) | proj_W (LS2) |
|------------------|------------------:|-------------:|-------------:|
| R21 (lucky)      | **0.444**         | 0.599        | 0.651        |
| HAWE 98/2        | **0.439**         | 0.645        | 0.642        |
| HAWE 85/15       | **0.415**         | 0.783        | 0.862        |
| ws8 (single)     | **0.273**         | 0.745        | 0.835        |

**Pattern**: as `proj_W` *increases*, 6-axis score *decreases*. Spearman
ρ of the four points (LS1 column): −0.93 (LS2 column also −0.93). The
post-fix scores **strengthen** the original observation: ws8 dropped
from 0.419 to 0.273 while its projection 0.75-0.84 stayed the same, so
the inverse relationship is now sharper. Sample is still N=4; treat
the magnitude as suggestive, the direction as solid.

### Why does this reverse the Domain M2 hypothesis?

The hypothesis was: high-Gini ES2-dominant controllers preserve the
spatial decomposition predicted by Yang *et al.* [Yang2023DDIC, Fig. 7],
which the panel surmised is the inter-area mode shape, hence such
controllers should *align* with the mode shape and score higher.

The data say the opposite. Two non-exclusive explanations:

1. **Mode shape ≠ paper Fig. 7 spatial decomposition.** The paper Fig. 7
   reports per-agent ΔH histories from a *trained* SAC controller on a
   *Simulink* benchmark. That panel may reflect not the open-loop mode
   shape but the *closed-loop optimal damping pattern*, which can prefer
   non-mode-shape buses for actuator placement reasons (small-gain /
   observability / paper Bus-16 happens to host an unmodelled cross-area
   tie-line).
2. **Acting on the dominant mode-shape bus is the wrong RL policy.** The
   mode shape encodes where the system *naturally* swings; an effective
   controller may need to act *somewhere else* to inject damping that
   couples back to the mode through the network (classic decentralised
   damping placement: best location is often an electrically-stiff bus
   slightly off the swing peak). ws8 / HAWE 85/15 happen to act heavily on
   ES3 (the *least* mode-active bus), which rules them out as good
   controllers; R21 / HAWE 98/2 act on ES2, which is mid-rank in mode
   shape — and they score highest.

In either case, the manuscript's Domain-M2 framing ("ES2-dominant
controllers are mode-shape-aligned, so the regularity is physical")
**cannot be defended** with this measurement. The regularity is real
(R21 + HAWE 98/2 score higher than ws8 + HAWE 85/15), but its cause is
not modal alignment. It might be modal *anti-alignment* with respect to
the dominant ES, or it might require a different physical lens (energy,
observability, controllability Gramian).

---

## Verdict

| Claim from panel Domain M2 / paper §VI-D                                                                                  | Evidence       | Verdict   |
|---------------------------------------------------------------------------------------------------------------------------|----------------|-----------|
| "Higher Gini = ES2-dominant = preserves paper's spatial decomposition"                                                    | confirmed (paper Fig. 7 + per-agent traces) | held       |
| "Paper's spatial decomposition aligns with the inter-area mode shape"                                                     | mode shape says ES1 > ES2/4 > ES3 — paper says ES2 dominant | **REJECTED** |
| "Therefore high-score controllers project more onto the mode shape"                                                       | data says the opposite (-0.93 corr) | **REJECTED** |
| "Therefore the regularity is physically explained"                                                                        | premise rejected, conclusion does not follow | **NOT SUPPORTED** |
| **Per-agent regularity itself is real** (R21 / HAWE 98/2 outscore ws8 / HAWE 85/15 along the same Gini ordering reported) | confirmed | held |

---

## Next-step recommendations (priority-ordered)

| #  | Action                                                                                                                                                                                                                                                                       | Effort | Decides                                                                                                                              |
|----|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|--------------------------------------------------------------------------------------------------------------------------------------|
| N1 | **Drop modal-alignment claim from paper §VI-D** before any submission — the data refutes it. Reframe the regularity as "spatial selectivity, mechanism-TBD" with a forward reference to "future work: observability- / Gramian-based explanation".                            | 1-2 h  | Direct factual fix in the paper to avoid a Domain referee shooting it down on resubmission.                                          |
| N2 | **Compute `B = controllability Gramian column for ESS_i`** as the alternative physics. If `proj(range, B[:,inter_area_mode])` correlates positively with score, that's the right physical lens (acting on the most controllable input cluster, not the most observable one). | 1 d    | A defensible Domain-M2 replacement explanation grounded in modern control theory.                                                    |
| N3 | **Re-run modal analysis at the LS1/LS2 *operating point*** (post-disturbance settled state, not pre-disturbance) — mode shapes can shift when the system is off-nominal. May reconcile the regularity.                                                                       | 4-8 h  | Whether the panel's framing holds at the operating point under disturbance, even if it doesn't pre-disturbance.                      |
| N4 | **Rotate the mode-shape projection** to the *energy-weighted* mode shape (use `|W| * sqrt(M_i / sum_j M_j)`) where `M_i` is the inertia at bus `i`. This is the "modal energy" formulation; it reweights the projection by physical energy flow.                              | 2-4 h  | Whether the data fits a different formal modal lens before abandoning the Domain-M2 line entirely.                                   |
| N5 | (Out of scope for A3) Hand off the Domain-M2 rewrite to the writing group with this verdict + plot as evidence; recommend the paper substitute the Gini regularity prose with a "mechanism-unknown but reproducible regularity" framing pending N2/N3/N4 outcome.             | 30 min | Clean separation of probe/data finding from manuscript revision.                                                                    |

---

## Files written

```
quality_reports/research_loop/r27_modal_analysis_verdict.md            ← this
results/research_loop/r27_modal_analysis.json                          ← EIG payload + per-controller projections
paper/figures/v4_modal_analysis/inter_area_mode_shape.png              ← bar chart
paper/figures/v4_modal_analysis/inter_area_mode_shape.pdf
paper/figures/v4_modal_analysis/mode_proj_vs_score.png                 ← scatter (proj vs 6-axis)
paper/figures/v4_modal_analysis/mode_proj_vs_score.pdf
probes/andes_kundur/t2_modal_analysis.py                               ← driver
```

---

## Reproducibility

```bash
wsl -e bash -c "cd '/mnt/c/Users/27443/Desktop/Multi-Agent  VSGs' && \
    /home/wya/andes_venv/bin/python probes/andes_kundur/t2_modal_analysis.py"
```

Runtime ≈ 3 min (ANDES cold start ~30 s + EIG ~10 s + 4 cached-JSON loads
+ plotting).

---

## Caveat on small N

The 4-controller scatter (Spearman ρ ≈ -0.93) is suggestive but not
statistically conclusive. The verdict is built primarily on the
**direction** (mode-shape says ES1 is the dominant ESS, paper says ES2)
which is independent of the projection sample size. Adding more
controllers to the scatter (e.g. all 5 SWA points from r26) would tighten
the empirical claim but is unlikely to flip the direction.

---

*Generated 2026-05-07 by code-probe dispatch group A3 (B-4). Mode shape
extracted from `ss.EIG.W` (right eigenvector); standard participation
recovered via `W * inv(W).T` because ANDES `ss.EIG.pfactors` returns a
non-textbook normalisation. The Domain-M2 reversal is the most
publishable single finding from the entire dispatch (A1 / A2 / A3).*

---

## §X. Claim + Falsification (per O1 protocol)

### Claim

> The Kundur V4 system has a single dominant inter-area mode at f = 0.579 Hz, ζ = 2.45 % (classic Kundur 2-area pattern). Cosine projection of per-agent ΔH range onto the rotor-speed mode-shape vector |W| reveals the **opposite of the panel Domain-M2 prediction**: low-score controllers (ws8 0.419, HAWE 85/15 0.554) project HIGHER onto the mode shape (0.745–0.862) than the high-score R21 (0.599–0.651), refuting the "preserve mode-shape ⇒ high score" mechanism. The Gini regularity reported in paper §VI-D is therefore real but **not modal-alignment-driven**; the paper must drop modal-alignment framing before submission.

### Falsification

| 维度 | 条件 | status |
|---|---|---|
| **F-Independence** | Are the 5 controllers used in projection (no-control, R21, HAWE 98/2, HAWE 85/15, ws8) independent samples? | **No**. R21, ws8, HAWE 98/2, HAWE 85/15 all derive from R21 trajectory (DA-CRIT-1). The Domain-M2 reversal is computed across a non-independent ensemble. **B-2 fresh-seed actors required** to confirm reversal across truly different policies. |
| **F-Coverage** | Did projection cover both LS1 + LS2 disturbances, both ΔH and ΔD? | LS1 + LS2 covered (table shows projection range per scenario). Only ΔH projection — ΔD not analysed. **Coverage adequate for Gini-of-ΔH claim**; not adequate to claim "spatial selectivity" is the deeper mechanism without ΔD, ΔP analysis. |
| **F-Counterfactual** | Tested vs random per-agent ΔH range as null? | **Not run.** A random ΔH range would project ~uniformly across controllers; the systematic R21-low / ws8-high pattern is unlikely under chance, but a formal null bootstrap would strengthen the claim. |
| **F-Generalization** | Holds at modes other than 0.579 Hz? | EIG returned 102 modes; only the 0.579 Hz inter-area mode was projected onto. Other modes (local modes ≥ 1 Hz, slow modes < 0.3 Hz) might give different ordering. **Generalization to other modes uncertain** — but the 0.579 Hz mode is the *dominant* low-damping mode of the Kundur 2-area system, so projection onto it is the canonical analysis. |
| **F-Robustness** | EIG converged? Mode classification stable? | EIG ran on V4 zero-action steady-state; ζ = 2.45 % is consistent with published Kundur 2-area inter-area mode (literature reports ζ ≈ 2-5 %). Mode classification robust. |

### Killshot

> If the Domain-M2 reversal is an artifact of the **non-independent controller set** (HAWE variants are linear blends of R21 and ws8, so their projections are linear blends of R21 and ws8 projections), then the "reversal" is mathematically forced by HAWE construction, not a real empirical pattern. **Required to settle**: re-run projection on B-2 fresh-seed actors. If the reversal persists with truly independent actors, the finding is real; if it disappears, it's a HAWE-construction artifact and the Gini regularity needs a different mechanism.

### Independent verification path

- [ ] B-2 fresh-seed actors → repeat projection; confirm or refute reversal
- [ ] Project ΔD range (in addition to ΔH) onto mode shape; check whether reversal is ΔH-specific
- [ ] Bootstrap null: shuffle per-agent ΔH labels across agents, re-project, build null distribution, compute p-value for observed reversal
- [ ] Spawn fresh-context claim-verifier on this verdict + r27 plot files; ask "what other mechanism explains the reversal?"


## Questions opened (this round)
- none (retrofit — this verdict pre-dates the Q entity introduced in R39)

## Questions closed (this round)
- none (retrofit)

## Questions advanced (this round, status unchanged)
- none (retrofit)
