# C1 — Mechanism section skeleton (for PI review, not submission prose)

> Working title: **"Small-Signal Mechanism: How Spatial Differential
> Allocation Modulates Inter-Area Mode Damping"**
> Role in the paper chain (REPORT.md §7): link 3 — *explain where the gain
> comes from and what determines it*, after the causal-evaluation section.
> Sources: feeds `reports/R281.md`, `reports/R282.md`; claims CLM-0615,
> CLM-0625; honesty boundaries DIFFERENTIATION_MEMO.md §4.
> Convention below: drafted English sentences are load-bearing candidates;
> [CLM-06xx] tags are traceability margin notes (stripped in final prose);
> [N] = REPORT.md survey reference number.

## Paragraph plan

### P1 — Setup: from time-domain gain to a small-signal question

Drafted sentences:

> The placement literature establishes that the spatial distribution of
> virtual inertia materially shapes frequency performance [2][4][5]. The
> causal evaluation of the preceding section showed that a learned,
> constrained allocator reduces synchronization loss by 24.35% and
> three-second inter-area IAE by 17.04% relative to the zero-allocation
> reference on a sealed disturbance bank [CLM-0610]. What that evaluation
> cannot show is *why* the gain exists. This section asks a narrower
> question: does static differential allocation along the learned spatial
> mode modulate the classical inter-area mode of the plant in a
> small-signal-measurable way, and does the modulation direction coincide
> with the direction the learned controllers actually exploit?

Evidence notes: 24.35%/17.04% → CLM-0610 (only if the causal-eval section
keeps these as headline numbers; otherwise cut). Learned direction b=-1
measured from 144 sealed learned-arm trajectories → CLM-0615.

### P2 — Method in one paragraph (small-signal protocol)

Drafted sentences:

> We freeze the evaluated plant — the modified Kundur two-area system with
> four VSG units — and sweep the static allocation coordinate q over nine
> points in [-0.25, +0.25] along the hard zero-sum mode [1, 1, -1, -1],
> holding total inertia at 1400 (per-machine M_i = 200 + 600·(0.25 +
> q·pattern_i)). At every point we re-solve the power flow, linearize, and
> track the inter-area mode by conjugate-pair-merged per-machine
> participation factors; all contracts (guards, identification rule,
> materiality threshold of 5%) were registered before the first eigenvalue
> [CLM-0615].

Evidence notes: contract hash 11a4800123f48a33 → R281 plan/summary; rule
details → R281 execution amendment. Keep protocol prose here; full contract
goes to an appendix table (T1 below).

### P3 — Headline result: directional, material damping modulation

Drafted sentences:

> The tracked classical inter-area mode (0.52–0.56 Hz, dominated by the
> area-2 synchronous machines) shows a damping ratio of 0.0195 at q = 0,
> rising to 0.0302 at q = -0.25 (+55.3%) but only to 0.0213 at q = +0.25
> (+9.5%) — a span of 45.8%, far above the pre-registered 5% materiality
> threshold [CLM-0615]. The strong-damping side coincides with the
> beneficial direction measured from the learned controllers' executed
> actions [CLM-0615].

Evidence notes: all numbers → CLM-0615. "area-2 synchronous machines" =
genrou3+genrou4 participation ~0.43 each (R282 summary) — participation
~1.7 figure from CLM-0615; pick one phrasing at drafting.

### P4 — Structure: the mapping is not globally monotone (authenticated)

Drafted sentences:

> Monotonicity holds over q in [-0.25, +0.125] but breaks at the +0.25
> extreme, where damping upticks (U-shape). A four-point densification over
> q in [+0.1875, +0.25] confirms the upturn as same-branch behavior — every
> adjacent pair passes pre-registered continuity criteria (participation
> cosine 1.0, frequency step at most 0.0009 Hz against a 0.05 Hz threshold),
> with damping rising smoothly from 0.0194 to 0.0213 [CLM-0625]. We
> therefore report the mechanism as a bounded empirical mapping — material,
> directional, but not globally monotone — and make no monotone-law or
> damping-creation claim.

Evidence notes: numbers → CLM-0625. The last sentence is the §4 boundary
verbalized; keep it almost verbatim in final prose.

### P5 — Trade-off: VSG local modes follow 1/√M physics

Drafted sentences:

> The VSG-pair local modes obey the expected inertia–damping trade-off:
> with damping coefficients fixed, their damping ratio scales as 1/√M
> (0.112 at M = 200 versus 0.080 at M = 500 for the coherent case), and the
> modes split and merge across q, defeating consistent identification — a
> pre-registered failure flag we report rather than resolve [CLM-0615].
> Allocation therefore redistributes, rather than creates, damping
> authority, and the trade-off bounds how much allocation amplitude is
> usable before local modes deteriorate.

Evidence notes: numbers → CLM-0615. "redistributes, rather than creates" —
check against boundary 1: the bounded statement says materially modulates;
"redistributes damping authority" is an interpretation — flag for PI
confirmation; safer alternative: "the local-mode trade-off constrains the
usable allocation amplitude."

### P6 — Discussion hook: small-|q| flatness and the large-signal component

Drafted sentences:

> Over most of the grid the inter-area damping stays near 1.9%; the gains
> concentrate at large |q| on the beneficial side. The learned controllers,
> however, operate habitually at small |q|, where the small-signal damping
> barely changes. The measured time-domain gain therefore plausibly
> contains an additional large-signal transient component — for example,
> pulse-side inertia limiting the initial RoCoF — which the present
> linearized analysis cannot capture; we state this as an open mechanism,
> not a result [CLM-0615, R281 feed O3].

Evidence notes: keep "plausibly/open" phrasing (evidence = absence of
small-signal change at small |q|). This paragraph motivates future work,
not C2.

### P7 — Scope

Drafted sentences:

> The mechanism characterization covers the plant and its ANDES-resident
> dynamics only; the slow common-mode restoration loop is outside the
> linearized model, and nothing here speaks to it. Linearization is at the
> pre-disturbance equilibrium of a single two-area plant; no topology,
> cross-simulator, or stability-certificate claim is made [CLM-0615].

Evidence notes: boundaries 4 and 5 verbatim-safe.

## Figure / table specs

- **Fig M1 (main)**: damping ratio vs q, 9 sweep points + the 4
  densification points visually distinguished; secondary axis: mode
  frequency. Data: `results/r281_eig_mechanism/summary.json`,
  `results/r282_eig_upturn/summary.json` (field `chain`).
- **Fig M2 (support, optional)**: participation-vector composition of the
  tracked mode at q = -0.25, 0, +0.25 (bar chart over the 9 machine keys).
  Data: R281 summary `main_sweep[].modes` (merged per the amendment rule).
- **Table T1 (appendix)**: contract summary — plant build pointer, mapping,
  guard set (G4 M = 0.1/D = 0, zero-sum 1400, PFlow convergence),
  identification rule, materiality threshold, contract hashes
  (11a4800123f48a33, 6d0da4e1da39fc47), runner (ANDES 2.0.0, WSL).

## Bounded-wording bank (use) and banned list (never)

Use (bounded, evidence-matched):
- "differential allocation materially modulates the classical inter-area
  mode damping ratio in the direction the learned controllers exploit
  (+55% at full amplitude, not globally monotone)" [CLM-0615]
- "VSG local modes follow a 1/√M inertia–damping trade-off" [CLM-0615]
- "the U-shaped upturn is confirmed same-branch structure" [CLM-0625]

Never (DIFFERENTIATION_MEMO §4):
- "allocation creates damping" / any monotone law / any global optimality
  claim
- any suggestion the mechanism explains the slow restoration loop
- any topology, cross-simulator, or real-SCR generalization
- any new number not in CLM-0610/0615/0625

## Citation anchors for this section

[2][4][5] placement lineage (P1); [6] inertia heterogeneity (P3/P5);
[10] grid-strength small-signal perspective (bridge sentence into C2);
[15][21] only if a compare-sentence is needed — prefer keeping them in
Introduction/Discussion. Final numbering to be resolved at assembly.

## Open drafting decisions for PI

1. P5 "redistributes, rather than creates" — keep the interpretive sentence
   or the safer alternative?
2. Does P1 quote the causal-eval headline numbers, or only point back?
3. Fig M2 worth the space, or fold participation into Fig M1 caption?
