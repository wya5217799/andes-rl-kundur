# r30 — `paper_grade_axes.py` audit verdict (post-N1c fix)

**Date**: 2026-05-07
**Scope**: full read-through of `evaluation/paper_grade_axes.py` after the
B1 + B2 settling-axis fix in r28 / N1c. Look for additional bugs,
inconsistencies, or design choices that affect any number on the paper
draft.
**Status**: **COMPLETE**. One real inconsistency, two robustness gaps,
several known design choices flagged.

---

## TL;DR

> Three categories of finding:
>
> - **C1 — Real inconsistency** (1): per-controller score is computed by
>   geometric mean over axes (line 220) but per-controller-overall by
>   arithmetic mean over scenarios (line 290). Pick one.
> - **C2 — Robustness gaps** (2): no NaN guard, no `tds_failed` check.
>   These don't fire on current eval data but could on edge cases.
> - **C3 — Known design choices** (3): the action-range axis is structurally
>   1.0 for V4 (DA-CRIT-3), the `max(s, 0.01)` floor lifts 0-axis scores,
>   non-DDIC controllers are scored on only 3 axes vs 7 for DDIC. These
>   are *not* bugs but should be acknowledged in the paper draft.
>
> No additional bugs of the B1/B2 magnitude found. The post-fix ranker is
> trustworthy for downstream paper revisions, modulo C1 (which would
> shift overall scores by ≤ 5 % at the headline weights and would not
> change the relative ranking of R21/SWA/HAWE).

---

## C1 — Aggregation inconsistency: geo (axes) + arith (scenarios)

**File**: `evaluation/paper_grade_axes.py`

```python
# line 220 — within evaluate_trace, axes -> overall:
overall = math.exp(sum(math.log(max(s, 0.01)) for s in scores) / len(scores))   # GEO mean

# line 290 — across scenarios, overall_LS1 + overall_LS2 -> mean overall:
combined = sorted(
    [(l, float(np.mean(s))) for l, s in by_lbl.items() if len(s) == 2],          # ARITH mean
    key=lambda x: -x[1],
)
```

The docstring (line 14) commits to **"any one 0 → overall 0, enforce
holistic pass"**, which only holds for geometric mean. Using arithmetic
mean across scenarios undermines that enforcement: a controller that
achieves 0.5 on LS1 and 0.0 on LS2 reports 0.25 (arith), not 0 (geo).

**Effect on current numbers**:

| Controller | LS1 overall | LS2 overall | arith mean (used) | geo mean (consistent) |
|------------|------------:|------------:|------------------:|----------------------:|
| R21        | ~0.46       | ~0.43       | 0.444 ← reported  | ~0.444 (close)        |
| HAWE 98/2  | ~0.46       | ~0.42       | 0.439 ← reported  | ~0.438                |
| ws8        | ~0.32       | ~0.23       | 0.273 ← reported  | ~0.272                |

The two means agree to 3 decimals because LS1/LS2 scores are similar.
Effect on relative ranking: zero. **Not load-bearing for current
results, but worth fixing for consistency**.

**Recommended fix** (one line):
```python
combined = sorted(
    [(l, float(math.exp(sum(math.log(max(x, 0.01)) for x in s) / len(s))))
     for l, s in by_lbl.items() if len(s) == 2],
    key=lambda x: -x[1],
)
```

---

## C2 — Robustness gaps

### C2.1 — No NaN guard

`evaluate_trace` reads `df_full = np.array([s["delta_f_es"] for s in tr])`.
If any trace step contains NaN (which can happen if ANDES TDS partially
crashes mid-episode), `np.max(np.abs(df))` returns NaN, every axis
becomes NaN, and `math.log(max(NaN, 0.01))` raises. The ranker would
silently skip that controller in `rank_models` (the
`if scores:` guard catches it) but the eval-driver loop does not log
the NaN.

**Risk level**: low (current eval JSONs do not contain NaN). Add a
defensive `if np.isnan(df_full).any():` early return with a flag.

### C2.2 — No `tds_failed` check

`run_zero_action_trace` and `run_trained_policy_trace` set
`tds_failed=True` if ANDES `TDS.busted` fires mid-episode. The eval
JSONs do contain a `tds_failed` field (see
`scripts/research_loop/eval_v4_ddic.py`). `evaluate_trace` does not
check it; partial-trace evaluations get scored as if successful.

**Risk level**: medium for V5 / future-env evals where TDS instability
is more frequent (we saw seed 51 with 30 % TDS-fail rate during
training). For current Table-I controllers all evals completed cleanly.

**Recommended fix**: add `if j.get("tds_failed"): return TraceScore(label, ..., overall=0.0)`.

---

## C3 — Known design choices (acknowledge in paper)

### C3.1 — Action-range axis trivially 1.0 (DA-CRIT-3)

Line 148-150 (within `_box_containment` docstring):

> Caveat: project DM_MIN/MAX = [-10, 30] → ΔH ∈ [-5, +15], 远小于 box
> [-100, +300]. A2 给"平凡满分", 不区分 "agent 守恒" vs "action bound 限制".

Note: the comment refers to the **V2-era** action range
`DM_MIN/MAX = [-10, 30]`. V4 has `DM_MIN/MAX = [-200, 600]` per
`env_v4.py:60-63`, which is paper-faithful. So the V4 action range
**does** match the paper Eq.12 box, and the axis *should* discriminate.
But empirically R21 controllers stay deep inside the box (max ΔH ~15
vs box [-100, +300]), so they still all score 1.0 on this axis. **Same
DA-CRIT-3 outcome**, different cause: not "box too wide for project
range" but "trained agents under-use the available action bandwidth".

This is information about controller behaviour, not a ranker bug. The
paper §VI-D ablation can flag this as the reason for the action-range
axis being uninformative.

### C3.2 — `max(s, 0.01)` floor (DA-CRIT-2 also flagged this)

Line 220: `math.log(max(s, 0.01))`. This prevents one 0-axis from
collapsing the geometric mean to 0. The docstring says "any 0 → 0",
which the floor weakens to "any 0 → overall ≈ 0.01^(1/N)".

For N=7 axes: `0.01^(1/7) = 0.518`. So even a controller with one true
0-axis score gets a multiplicative cap of 0.518× on the geo-mean of the
other axes, not a hard 0.

**Verdict**: docstring is misleading; rephrase to "any one 0 caps overall
by 0.518×" or remove the "holistic pass" framing. The floor itself is a
defensible choice (avoids inf/log issues), just don't oversell it.

### C3.3 — DDIC vs non-DDIC use different axis counts

Line 198: `if is_ddic:` adds the dH_smooth, dD_smooth, dH_range, dD_range
axes. Non-DDIC controllers (only `no_control` in current setup) use
3 axes total; DDIC controllers use 7 axes total.

Cross-class score comparisons are not strictly apples-to-apples. But
since the only non-DDIC entry is no_control and the comparison is
ddic-vs-no-control = "did the controller help at all", this is
acceptable.

---

## Recommendations

| #   | Action                                                                                                                                       | Effort | Priority |
|-----|----------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|
| A1  | Fix C1 — change line 290 to geo mean across scenarios. One-line patch.                                                                       | 5 min  | low (numbers don't move much) |
| A2  | Fix C2.2 — early return on `tds_failed`.                                                                                                     | 10 min | medium (relevant for future evals) |
| A3  | Fix C2.1 — NaN guard on the trace array.                                                                                                     | 5 min  | low (defensive)                |
| A4  | Update docstring (line 14) to acknowledge `max(s, 0.01)` floor, drop "holistic pass" claim.                                                 | 5 min  | low                            |
| A5  | (Paper-side) Acknowledge in §VI-A or footnote that the action-range axis is uninformative on V4 because trained agents under-use the box. | 10 min | medium (Domain referee will ask) |

**No critical fixes**. The B1+B2 patch in r28/N1c was the only major
ranker bug; the rest is polish.

---

## Files referenced

- `evaluation/paper_grade_axes.py` (the audited file; B1+B2 fix already
  applied per r28 verdict)
- `r28_r21_settling_verdict.md` (the upstream B1+B2 fix)
- 5-reviewer panel `06_editorial_decision.md` DA-CRIT-2 (the original
  external flag for `max(s, 0.01)` floor)

---

*Generated 2026-05-07 by code-probe dispatch followup F7. The post-N1c
ranker is trustworthy for paper revision; the C1-C3 findings are minor
and do not require re-running the rank.*


## Questions opened (this round)
- none (retrofit — this verdict pre-dates the Q entity introduced in R39)

## Questions closed (this round)
- none (retrofit)

## Questions advanced (this round, status unchanged)
- none (retrofit)
