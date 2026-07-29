# C2 — Weak-grid validation section skeleton (for PI review, not submission prose)

> Working title: **"Validation Boundary: Allocation Sensitivity Under
> Weakening Grid Strength"**
> Role in the paper chain (REPORT.md §7): link 4 — *give the boundary*, as
> the validation section of the C1 spine (REPORT.md §7 recommends C2 merge
> into C1 as its generalization axis, not a standalone paper).
> Sources: feed `reports/R283.md`; claim CLM-0630; execution amendment
> `memory/rounds/R283/execution_amendment_20260729.md`; honesty boundaries
> DIFFERENTIATION\_MEMO.md §4.
> Conventions as in the C1 skeleton: \[CLM-06xx] = traceability notes,
> \[N] = REPORT.md survey reference number.

## Paragraph plan

### P1 — Motivation and the declared proxy

Drafted sentences:

> Grid-forming resources are increasingly deployed in weak grids, where
> small-signal stability margins shrink and the value of any control
> authority must be re-examined \[10]\[5]. We therefore test how the
> allocation–damping sensitivity of the previous section varies along two
> prospectively frozen strength axes. The first scales the aggregate VSG
> inertia (M0 = 100 to 300, executed M vector multiplied by M0/200). The
> second scales the resistance and reactance of the inter-area tie corridor
> (three 7–8 circuits) by k = 1.0, 1.5, 2.0 — a *declared* proxy for
> short-circuit ratio: we report it as a reactance scaling, not converted
> to SCR units, and both axes and the q subset {0, ±0.25} were frozen
> before the first eigenvalue \[CLM-0630].

Evidence notes: proxy declaration wording is load-bearing — reviewers will
attack "SCR proxy"; the honest-declaration phrasing is the defense.
Sensitivity metric S = |ζ(+0.25) − ζ(−0.25)| / |ζ(0)| defined here or in
C1 (decision: define once in C1 P2, recall here).

### P2 — Electrical axis: a confirmed, monotone strength gradient

Drafted sentences:

> Sensitivity grows monotonically as the tie weakens: S = 0.458 at
> k = 1.0, 1.050 at k = 1.5, and 2.053 at k = 2.0 — a 4.5-fold increase
> across the scanned range, with every point verified on the same mode
> branch. The baseline inter-area mode itself weakens consistently (damping
> ratio 0.0195 to 0.0129, frequency 0.527 to 0.482 Hz), confirming the
> proxy moves the plant in the intended physical direction \[CLM-0630].

Evidence notes: all numbers → CLM-0630 / branch\_analysis.json.

### P3 — Structure change: weak grid removes the upturn, grows the gain

Drafted sentences:

> Weaker ties do not merely amplify the sensitivity; they change the
> mapping's shape. The U-shaped upturn authenticated at k = 1.0 disappears
> at k ≥ 1.5 (ζ at q = +0.25 falls below its q = 0 value: 0.0148 versus
> 0.0161 at k = 1.5; 0.0069 versus 0.0129 at k = 2.0), so the mapping
> becomes monotone over the measured range, and the beneficial-direction
> gain at full amplitude grows from +55% at k = 1.0 to +159% at k = 2.0
> \[CLM-0630]. Within the scanned range, placement matters more — and more
> predictably — in a weaker grid.

Evidence notes: "within the scanned range" is the required bound; do not
drop it. The last sentence is the section's takeaway — bounded form per
R283 feed C1/C2.

### P4 — Inertia axis: partial gradient plus an honest blind spot

Drafted sentences:

> Halving-to-1.5× aggregate VSG inertia moves sensitivity in the same
> direction: on the levels where mode identification is valid, S falls from
> 0.458 at M0 = 200 to 0.199 at M0 = 300 (ratio 2.3), and the valid
> M0 = 100 pair corroborates the trend (+53% at q = +0.25, matching the
> earlier development probe). Below M0 = 200, however, the inter-area
> branch hybridizes with VSG local modes at q = ±0.25 (M0 = 150) and at
> q = -0.25 (M0 = 100); our pre-registered screen flags these points, so
> the low-inertia gradient is unmeasured — not absent \[CLM-0630].

Evidence notes: "unmeasured — not absent" is mandatory phrasing (PI-facing
honesty line from R283 verdict). Flagged points never quoted as results.

### P5 — Identification integrity (short, methods-flavored)

Drafted sentences:

> All 24 points reuse the previous section's in-script identification rule
> unchanged; a branch-validity screen (participation cosine ≥ 0.9 and
> frequency step < 0.05 Hz against each level's q = 0 anchor, whose
> cross-level chain permits physical frequency drift) separates genuine
> branch swaps from real structure. The M0 = 200 and k = 1.0 anchor rows
> reproduce the previous section's values within 10⁻⁶, and every guard
> (contract inertia limits, zero-sum per level, power-flow convergence)
> passes at all 24 points \[CLM-0630].

Evidence notes: screen criteria → execution amendment. This paragraph is
the reproducibility defense; keep it compact.

### P6 — Limits

Drafted sentences:

> The strength axes are declared scalings on a single two-area plant: the
> tie-corridor proxy is not a unit-converted SCR, the hybridization zone
> below M0 = 200 is uncharacterized, transient survival of the
> small-signal ordering is untested, and no topology or cross-simulator
> evidence is claimed \[CLM-0630].

```
Figure / table specs
```

* **Fig W1 (main)**: S vs k (axis B, 3 points, monotone) alongside S vs M0
  (axis A, valid levels only, flagged levels shown as open markers without
  values). Data: `results/r283_strength_sweep/branch_analysis.json`
  (`axis_a.valid_S`, `axis_b.valid_S`).

* **Fig W2 (main)**: ζ vs q at k = 1.0 / 1.5 / 2.0 (three curves) — shows
  the upturn disappearing and the beneficial-side slope steepening. Data:
  `results/r283_strength_sweep/summary.json` (`axis_b[].runs`).

* **Table T2**: per-level ζ(q) for both axes with flagged cells marked
  "identification flag (branch swap)", anchor-check row, guard summary.
  Data: summary.json + branch\_analysis.json.

## Bounded-wording bank (use) and banned list (never)

Use:

* "within the scanned ranges, allocation matters more in weaker grids"
  \[CLM-0630]

* "the mapping becomes monotone over the measured range as the tie
  weakens, and the beneficial-direction gain grows to +159%" \[CLM-0630]

* "the low-inertia gradient is unmeasured, not absent" \[CLM-0630]

* "a declared reactance-scaling proxy, not converted to SCR units"

Never:

* real SCR units or any conversion of k into SCR / penetration percentages

* "allocation creates damping" / global monotone law (P3 says *measured
  range*, always qualified)

* any claim about the hybridization zone's physics (it is flagged, not
  explained)

* any transient, topology, cross-simulator, or HIL claim

* any new number not in CLM-0630

## Citation anchors for this section

\[10] Xin et al. (grid strength vs small-signal stability) — P1 anchor;
\[5] Dörfler & Groß review — P1 context; \[1] Milano et al. — optional P1
framing; \[2]\[4] one tie-back sentence to placement lineage in P3 or the
section's closing. Final numbering at assembly.

## Open drafting decisions for PI

1. Fig W1 + W2 both, or merge into one two-panel figure?
2. P4's blind spot: name Q-0044-style follow-up explicitly as future work,
   or leave it at "unmeasured — not absent"?
3. Does P5 live here, or move to a shared Methods/Reproducibility appendix
   covering both C1 and C2?

