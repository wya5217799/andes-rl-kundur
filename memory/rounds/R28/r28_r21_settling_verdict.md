# r28 — N1 R21 settling diagnosis verdict

**Date**: 2026-05-07
**Probe**: `probes/andes_kundur/t2_r21_settling_diag.py`
**Raw output**: `results/research_loop/r28_r21_settling_diag.json`
**Wall**: ~3 min (2 scenarios × 2 traces × 30 s ANDES + cold start)
**Status**: **COMPLETE**. Verdict = **H2 confirmed: the LS2 settling = ∞
in the ranker is a measurement artifact, not a controller regression**.
R21 *outperforms* the zero-action baseline on every settling convention.

---

## TL;DR

> Run R21 trained actors and zero-action baseline on V4 LS1 + LS2 for 30 s,
> compute settling under five conventions. **Result**: R21 settles **faster
> than baseline at every convention that resolves to a finite number**:
>
> - LS1: baseline 6.00 s vs R21 **4.40 s** (target paper, 30 s window)
> - LS2: baseline 9.80 s vs R21 **7.40 s** (target paper, 30 s window)
> - LS2: baseline 8.40 s vs R21 **6.80 s** (target own-final, 30 s window)
>
> The ranker's `paper_grade_axes._settling_time` reports ∞ for both R21
> LS2 and baseline LS2 because:
> 1. `evaluate_trace` truncates the trace to 6 s before calling
>    `_settling_time` (`mask_6s = t <= t[0] + 6.0`, line 170);
> 2. R21 LS2 does not actually settle until 7.40 s ; baseline LS2 not
>    until 9.80 s.
>
> So ∞ is a **window-truncation artifact**, not "the controller never
> settles". The paper draft Appendix B "LS2 settling: ∞ (>30 s)" is
> wrong on the >30 s factor too — R21 LS2 settles within ~7.4 s under
> the convention the ranker would use if it weren't truncated, and
> within ~6.8 s under the paper-faithful "own-final" convention.

---

## Settling under five conventions (paper anchors: LS1 → 3.0 s, LS2 → 2.5 s)

LS1 (paper target 3.0 s, paper |Δf|_final = 0.08 Hz):

| convention                                                | baseline   | R21         | R21 vs baseline      |
|-----------------------------------------------------------|-----------:|------------:|----------------------|
| C1: target 0 Hz, 30 s window (full nominal recovery)      | ∞          | ∞           | both fail (droop)    |
| C2: target paper 0.08 Hz, 30 s window                     | 6.00       | **4.40**    | -1.60 s (R21 better) |
| **C2'**: target paper 0.08 Hz, 6 s window (ranker actual) | ∞          | **4.40**    | R21 finite, baseline ∞ |
| C3: target own-final, 30 s window (textbook)              | 7.40       | **7.00**    | -0.40 s (R21 better) |
| C4: target own-final, 6 s window                          | ∞          | ∞           | both fail (window)   |

LS2 (paper target 2.5 s, paper |Δf|_final = 0.05 Hz):

| convention                                                | baseline   | R21         | R21 vs baseline      |
|-----------------------------------------------------------|-----------:|------------:|----------------------|
| C1: target 0 Hz, 30 s window                              | ∞          | ∞           | both fail            |
| C2: target paper 0.05 Hz, 30 s window                     | 9.80       | **7.40**    | -2.40 s (R21 better) |
| **C2'**: target paper 0.05 Hz, 6 s window (ranker actual) | ∞          | ∞           | **both ∞ — root cause of paper Appendix B claim** |
| C3: target own-final, 30 s window                         | 8.40       | **6.80**    | -1.60 s (R21 better) |
| C4: target own-final, 6 s window                          | ∞          | ∞           | both fail (window)   |

Trace headlines:

| series          | LS1 final df (Hz) | LS1 max df (Hz) | LS2 final df (Hz) | LS2 max df (Hz) |
|-----------------|------------------:|----------------:|------------------:|----------------:|
| zero-action V4  | 0.0621            | 0.1890          | 0.0579            | 0.1683          |
| R21 trained     | **0.0566**        | **0.1848**      | **0.0526**        | **0.1346**      |

R21 reduces LS1 final by 9 % and max by 2 %; LS2 final by 9 % and max by
20 %. **The trained policy does help on every metric** — there is no
"R21 destabilises LS2" mechanism in the data.

---

## Verdict

### V1 — Hypothesis ranking

| Hypothesis                                                            | Status        | Evidence                                                                                            |
|-----------------------------------------------------------------------|---------------|-----------------------------------------------------------------------------------------------------|
| **H1**: R21 actively destabilises LS2 (settling-axis 0 because controller is bad) | **REJECTED**  | R21 LS2 settles 1.6-2.4 s *faster* than baseline at every finite-window convention.                  |
| **H2**: ranker measurement artifact (6 s truncation + paper target band) | **CONFIRMED** | R21 LS2 takes 7.40 s under C2 / 6.80 s under C3; ranker checks within 6 s window only → returns ∞.   |

### V2 — Two compounding bugs in `paper_grade_axes._settling_time`

| Bug | Where                                                                                              | Effect                                                                                                    |
|-----|-----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| B1  | `mask_6s = t <= t[0] + 6.0` at `evaluate_trace` line 170 truncates the trace before settling check.  | Any controller whose physical settling > 6 s reports ∞ regardless of whether it would settle in a 30 s window. |
| B2  | `_settling_time(..., final_df_Hz=paper.final_abs_df_Hz)` uses the *paper's* final as the band centre, not the project's own residual. | When project's own final ≠ paper's final (here: 0.052 vs 0.050 Hz LS2), the 0.02 Hz band may sit on the wrong side of the trajectory's settled value, costing margin and pushing settling closer to ∞. |

The B1 effect is dominant for our data because R21 / V4 don't settle
within 6 s anyway. Even with B2 fixed alone (paper target 0.05 vs own
final 0.052 Hz, only 0.002 Hz off-centre, well within the 0.02 Hz band)
the result would still be ∞ at C2'. So **fix B1 first**.

### V3 — paper-draft consistency

`毕业论文/plan/2026-05-07_andes_ieee_paper.md` Appendix B states for LS2:
"settling: ∞ (>30 s)". This is wrong on both terms:

- **>30 s** — R21 actually settles in 6.80-7.40 s (well under 30 s).
- **∞**     — only true under the ranker's 6 s-truncation; under the
  paper's own intent (settling to residual within episode horizon = 10 s
  per §IV-A) R21 LS2 settles within the episode.

The paper Appendix B row for LS2 settling should be replaced with **7.4 s
(at paper-target band) / 6.8 s (at own-final band) / 2.5 s paper anchor /
ratio ≈ 2.7-3.0×**.

### V4 — Implications for the 6-axis ranker (UPDATED with measured re-rank)

**Initial estimate (RETRACTED)**: an earlier draft of this verdict
predicted that fixing B1 + B2 would *lift* R21's overall from 0.613 to
~0.71 (≈+16 %). That estimate was **wrong** — it assumed the only effect
of the fix was lifting R21 LS2 settling from the 0.01 floor, while
ignoring that LS1 settling under the new convention also drops.

**Measured outcome (`r29_ranker_postfix.log`)**:

```
old (paper-target band, 6 s window):     R21 = 0.613, settling LS1 = 4.40 s → 0.65 score, settling LS2 = ∞ → 0.01 floor
new (own-final band, full-trace window): R21 = 0.444, settling LS1 = 7.00 s → 0.00 score, settling LS2 = 6.80 s → 0.00 score
```

The fix exposes that **R21 is not a "near-paper" controller on the
settling axis at all** — old ranker's apparent 0.65 LS1-settling score
was a happy artifact of the paper-target band sitting just above R21's
own-final value (R21 LS1 final = 0.057 Hz vs paper 0.080 Hz; the 0.02 Hz
band around 0.080 Hz is centred 0.023 Hz above R21's actual residual,
giving the trajectory ~0.04 Hz of margin to enter, which it does at 4.4 s).
Once the band is centred on R21's own residual, the trajectory has only
0.02 Hz of margin and the swing oscillation (max 0.185 Hz on LS1) takes
~7 s to die down within that band. **7 s vs paper 3 s** at tol 4 s →
score = max(0, 1 - 4/4) = 0. Same story for LS2.

**Net rank changes** (key controllers, post-fix; full ranking in
`/tmp/r29_ranker_postfix.log`):

| Rank | Label                                  | old 6-axis | new 6-axis | Δ        |
|-----:|----------------------------------------|-----------:|-----------:|---------:|
|  1   | ddic_v4_h50_s49 (R21)                  | 0.613      | **0.444**  | -0.169   |
|  2   | ddic_v4_swa_w98 (SWA 98/2)             | 0.610      | **0.442**  | -0.168   |
|  3   | ddic_v4_ens2_R21ws8_w9802 (HAWE 98/2)  | 0.607      | **0.439**  | -0.168   |
|  4   | ddic_v4_swa_w95                        | 0.605      | **0.437**  | -0.168   |
|  5   | ddic_v4_ens2_R21ws8_w9505 (HAWE 95/5)  | 0.602      | **0.433**  | -0.169   |
|  6   | ddic_v4_swa_w90                        | 0.588      | **0.428**  | -0.160   |
| 10   | ddic_v4_ens2_R21ws8_w8515 (HAWE 85/15) | 0.554      | **0.413**  | -0.141   |
| 33   | ddic_v4_ctde_R21_s49 (CTDE)            | 0.423      | **0.292**  | -0.131   |
| 41   | ddic_v4_8_R21_best (ws8 single)        | 0.419      | **0.255**  | -0.164   |
| 46   | ddic_v4_9_phif100_s44 (cross-seed)     | 0.414      | **0.226**  | -0.188   |
| 104  | ddic_v4_paper_s42 (vanilla SAC)        | 0.137      | **0.136**  | -0.001   |
| 121  | no_control                             | 0.110      | **0.104**  | -0.006   |

(Numbers above are post-r30 C1+C2 fixes — geometric mean across scenarios
+ tds_failed / NaN guards. The C1 fix tightens lower-score rows by
≤ 0.04; top-3 R21/SWA/HAWE rows are unchanged because their LS1 and LS2
overall scores were already similar.)

The vanilla-SAC attractor row (no R21 lineage) drops only 0.001 because
its baseline traces are dominated by the LS1/LS2 max_df axis (already
saturated) rather than the settling axis whose pre-fix score the bug
inflated. R21-aligned controllers all drop ~0.15-0.17 because they were
the controllers whose own-final happened to fit inside the paper-target
band and got the artifact lift.

R21 stays #1; HAWE 99 % recovery still holds (0.439 / 0.444 = 98.9 %);
relative ordering is preserved. **But the headline numbers in the paper
draft change non-trivially**:

- "5.57× over no-control" → **4.04×** (= 0.444 / 0.110)
- "61.3 % of paper benchmark" → **44.4 %**
- "0.613 / 1.0 paper-anchor" → **0.444 / 1.0**

These are the corrected numbers for any downstream paper revision.

**Why the corrected ranker is more honest**: the old ranker's settling
axis was masking the cross-platform residual rather than measuring it.
R21 settles in 7 s on LS1 (paper 3 s) and 6.8 s on LS2 (paper 2.5 s) —
this is a real ANDES-vs-Simulink platform gap that the corrected ranker
*actually shows* on the settling axis (score 0, contributing to the drop
from 0.613 to 0.444), rather than hiding behind a band-centring artifact.
The 0.444 number is therefore a more defensible result than the 0.613,
even though it is numerically smaller.

---

## Next-step recommendations (priority-ordered)

| #  | Action                                                                                                                                                     | Effort | Decides                                                                                |
|----|------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------------------------------------------------------------------------------------|
| N1a | **Fix `paper_grade_axes.py` B1** — extend the settling window from 6 s to the trace duration (or at least 10 s = paper episode horizon). One-line change. | 30 min | Eliminates the dominant settling-axis artifact.                                        |
| N1b | **Fix `paper_grade_axes.py` B2** — change `final_df_Hz=paper.final_abs_df_Hz` to `final_df_Hz=df[-1].abs().max()` (own residual). One-line change.        | 15 min | Aligns settling definition with paper convention "settle to residual".                 |
| N1c | **Re-run `paper_grade_axes.py` on `eval_v4_baseline/`** with both fixes, regenerate the ranking JSON, update Table I in the paper draft.                   | 30 min | Updated headline numbers.                                                              |
| N2 | (Out of scope for N1) Update paper draft §VII-B "Cross-Platform Residual" + Appendix B settling rows + abstract "61.3 %" → new value once N1c is done.     | 1-2 h  | Paper-draft consistency with corrected ranker.                                          |
| N3 | Proceed to user-listed N2 (B-2 fresh seed) once N1 fixes land — fresh-seed comparison is more meaningful against the corrected ranking.                    | —      | Method-paper viability decision (TPWRS vs PES Letters), now with reliable settling.    |

**Recommendation**: N1a/N1b/N1c is **45-75 min total** and should be
done before any other downstream action. They directly invalidate one
of the 5-reviewer-panel CRITICAL findings (DA-CRIT-2 — "settling = ∞ for
ALL controllers ... `max(s, 0.01)` floor masks the failure"). The
finding is now: settling is finite, the floor was masking a *ranker
bug*, not a controller failure.

---

## Files written

```
quality_reports/research_loop/r28_r21_settling_verdict.md   ← this
results/research_loop/r28_r21_settling_diag.json            ← raw 30s traces + 5-convention table
probes/andes_kundur/t2_r21_settling_diag.py                 ← driver
```

---

## Reproducibility

```bash
wsl -e bash -c "cd '/mnt/c/Users/27443/Desktop/Multi-Agent  VSGs' && \
    /home/wya/andes_venv/bin/python probes/andes_kundur/t2_r21_settling_diag.py"
```

Runtime ≈ 3 min (2 scenarios × 2 traces × 30 s ANDES + cold start).

---

*Generated 2026-05-07 by code-probe dispatch followup N1 (R21 settling
diagnosis). Cross-references: r25 (baseline 8.4 s LS2 settling finding
that motivated this diagnosis), 5-reviewer panel DA-CRIT-2, paper draft
Appendix B.*

---

## §X. Claim + Falsification (per O1 protocol)

### Claim

> R21 trained policy **outperforms** zero-action baseline on every settling convention that resolves to a finite number (LS1: R21 4.40 s vs baseline 6.00 s under paper-target / 30 s window; LS2: R21 7.40 s vs baseline 9.80 s same convention). The "LS2 settling = ∞" reported by `paper_grade_axes._settling_time` is a **window-truncation artifact** (function uses 6 s window, R21 LS2 settles at 7.40 s — outside the window). Panel DA-CRIT-2 is therefore confirmed as a **ranker bug, not a controller regression**; the fix is to extend the ranker window to 30 s (or use C2/C3 conventions) rather than fix the controller or the env.

### Falsification

| 维度 | 条件 | status |
|---|---|---|
| **F-Independence** | K independent samples for R21 and baseline settling? | **K=1 each** (R21 is single seed by definition; baseline is deterministic V4 zero-action). The R21 vs baseline comparison is a deterministic A/B, not a stochastic test. **Acceptable** — settling is a deterministic ANDES TDS playback. |
| **F-Coverage** | Did the 5 conventions cover ranker behaviour comprehensively? | C1 (target 0 Hz) tests "full nominal recovery", C2 (paper target band, 30 s window) tests "paper-anchor settling", C2' (paper target band, 6 s window) is the actual ranker, C3 (own-final, 30 s) is textbook, C4 (own-final, 6 s) is a control. **Comprehensive** — both axes (target definition, window length) varied. |
| **F-Counterfactual** | Compared R21 to baseline + alternative trained controllers? | Compared to V4 baseline only. **Did NOT compare to ws8 / HAWE 98/2 / HAWE 85/15 settling under same conventions**. So the "R21 outperforms baseline" finding is verified, but "R21 is best among trained controllers on settling" is NOT tested in this probe. |
| **F-Generalization** | Holds beyond LS1 + LS2 at calibrated magnitudes? | LS1 + LS2 only. Generation trip / cascading fault not probed. |
| **F-Robustness** | Settling timestamps reproducible? | ANDES TDS deterministic for fixed seed; R21 actor evaluation deterministic. Estimated reproducibility std ≤ 0.05 s; finding (1.6 s gap LS1, 2.4 s gap LS2) is well above noise. **Robust.** |

### Killshot

> If `_settling_time` extension to 30 s window does **not** restore R21 LS2 settling to <2.5 s (paper target), then "ranker fix is sufficient" is wrong — the ranker fix exposes that R21 LS2 settles at 7.40 s, still **2.96× paper target**. So the claim should be carefully scoped: **the ranker bug papers over a real-but-modest controller regression**. The paper Appendix B should NOT say "LS2 settling = ∞" (false), but ALSO should NOT say "R21 is paper-grade on settling" (false) — it should say "R21 LS2 settles at 7.40 s vs paper 2.5 s, a 2.96× residual that is dominated by the ANDES-vs-Simulink platform gap rather than controller failure."

### Independent verification path

- [x] r25 + r28 together establish: V4 baseline LS2 = 8.40 s, R21 LS2 = 7.40 s (own-final / 30 s window) — both finite, both > paper anchor 2.5 s, R21 better than baseline.
- [ ] Compare ws8, HAWE 98/2, HAWE 85/15 on same 5 conventions — verify R21 is the best trained controller on settling, not just better-than-baseline.
- [ ] Fix `paper_grade_axes._settling_time` to use 30 s window OR remove the 6 s truncation entirely. Re-rank all controllers; check that ranking order preserves R21 > HAWE > attractor.
- [ ] Update paper Appendix B Table B with corrected settling numbers.
