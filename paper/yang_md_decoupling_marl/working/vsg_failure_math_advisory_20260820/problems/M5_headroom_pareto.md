# M5 — Headroom reinterpretation and endpoint/action-stress Pareto problem

**Type label: (M)**

## Headline result

R439/R441 do not demonstrate value from time variation. Every selected schedule repeats the same gain pair in every segment, so the measured improvement is attributable to admitting the constant point $(3.0,3.0)$, not to switching gains over time. The four measured winners improve both registered endpoints but violate both action-stress guards while retaining the common-mode guards. This establishes four trade-off anchors, not a theorem that endpoint improvement must always cost excessive action stress and not the minimum action cost of meeting an endpoint target.

## Hard facts

R416 is classified `STOP-NO-JOINT-HEADROOM` and selects `local_neighbour_md_km3_kd2` as the deterministic arm [M5-E01–M5-E02]. R439 labels its result `TIMEVARYING-HEADROOM` [M5-E03], while the guard-completed R441 verdict is `GUARD-VIOLATED` [M5-E04].

| profile | selected schedule | differential improvement | off-diagonal improvement | action-RMS increase | action-TV increase | action guards | common guards |
|---|---|---:|---:|---:|---:|---|---|
| eval_a | repeated $(3.0,3.0)$ over the sealed winner segments [M5-E05–M5-E06] | 0.13719266027037047 [M5-E11] | 0.09281086358168435 [M5-E12] | 0.3394156825203998 [M5-D01] | 0.16899847661301637 [M5-D02] | both fail [M5-E17–M5-E18] | all pass [M5-E19] |
| eval_b | repeated $(3.0,3.0)$ [M5-E20–M5-E21] | 0.09311866561826639 [M5-E26] | 0.0966897230065917 [M5-E27] | 0.3054177484189673 [M5-D03] | 0.11398274673152176 [M5-D04] | both fail [M5-E32–M5-E33] | all pass [M5-E34] |
| eval_c | repeated $(3.0,3.0)$ [M5-E35–M5-E36] | 0.143736943334306 [M5-E41] | 0.07575578747671269 [M5-E42] | 0.31924940821117165 [M5-D05] | 0.10490567603259549 [M5-D06] | both fail [M5-E47–M5-E48] | all pass [M5-E49] |
| eval_d | repeated $(3.0,3.0)$ [M5-E50–M5-E51] | 0.05973305995977649 [M5-E56] | 0.11929675168582977 [M5-E57] | 0.2838636502124663 [M5-D07] | 0.14318746310705066 [M5-D08] | both fail [M5-E62–M5-E63] | all pass [M5-E64] |

R439 reports `candidates_tested = 350` for each profile [M5-E65–M5-E68], but its profile files retain only the static point and the selected winner, not the action-stress records for all tested candidates. R441 re-runs only those winners. Therefore the existence of a lower-stress endpoint-improving schedule is untested.

## Assumption set

1. A schedule is a sequence of piecewise-constant gain pairs applied to one fixed plant/profile with no hidden state reset at segment boundaries.
2. Two schedules that apply the same gain pair at every segment are dynamically equivalent to the corresponding constant-gain law, apart from implementation artifacts that must be separately logged.
3. Endpoint and action metrics are evaluated on the same trajectory, horizon, profile, actuator map, and guard definitions.
4. The linear lower bound below is local and **HYPOTHETICAL** until the relevant response operator is identified.

## Result M5.1 — constant-schedule equivalence

Let a segmented controller apply gains $g_1,\ldots,g_K$. If $g_k=g_\star$ for every segment and the controller has no segment-boundary reset, then its closed-loop input and state trajectory are identical to those of the constant controller $g(t)\equiv g_\star$ for the same initial condition and disturbance.

### Proof

At every time, both implementations evaluate the same control law with the same gain and the same state. Uniqueness of the closed-loop trajectory gives equality. Segment labels do not alter the dynamics under Assumptions 1–2.

### Corrected theorem-level phrasing for RQ2

> On the four sealed R439/R441 evaluation profiles, expanding the candidate class to include the constant gain pair $(3.0,3.0)$ yields lower differential and off-diagonal endpoint energies than the R416 static reference, but the selected point violates the registered action-RMS and action-variation no-harm guards. The experiment provides no evidence that temporal gain variation is beneficial, because every selected segmented schedule is constant across segments.

This statement is limited to the sealed profiles, candidate generator, and guard implementation.

## Result M5.2 — conditional minimum-action lower bound

Consider a local linear response model

$$
z=z_0+G_{zu}u,
$$

where $z_0$ is the uncontrolled or reference residual, $u$ is the incremental action sequence, and $G_{zu}$ is the finite-horizon action-to-residual operator. If a target requires

$$
\lVert z\rVert_2^2\le \gamma\lVert z_0\rVert_2^2,
\qquad 0\le\gamma<1,
$$

then every feasible action satisfies

$$
\lVert u\rVert_2
\ge
\frac{(1-\sqrt\gamma)\lVert z_0\rVert_2}{\lVert G_{zu}\rVert_2}.
$$

### Proof

The reverse triangle inequality gives

$$
\lVert G_{zu}u\rVert_2
=\lVert z-z_0\rVert_2
\ge \lVert z_0\rVert_2-\lVert z\rVert_2
\ge(1-\sqrt\gamma)\lVert z_0\rVert_2.
$$

Since $\lVert G_{zu}u\rVert_2\le\lVert G_{zu}\rVert_2\lVert u\rVert_2$, the result follows.

This proves only that a strict cancellation target requires nonzero action when the response operator is bounded. It does **not** prove that the registered action guard must be violated, that the measured $(3.0,3.0)$ point is action-minimal, or that all nonlinear controllers share the same trade-off. No sealed $G_{zu}$ norm is available, so no numerical lower bound can be evaluated.

## Pareto formulation

For profile $p$, let $E_d(u,p)$ and $E_x(u,p)$ denote the differential and off-diagonal energies, and let $A_{\mathrm{rms}}(u,p)$ and $A_{\mathrm{tv}}(u,p)$ denote action stress. Define the feasible set

$$
\mathcal F_p(\bar E_d,\bar E_x)=
\left\{
 u\in\mathcal U:
 E_d(u,p)\le\bar E_d,
 E_x(u,p)\le\bar E_x,
 \text{all common, validity, and actuator guards pass}
\right\}.
$$

The minimum stress at the target is

$$
A_{\min,p}(\bar E_d,\bar E_x)
=
\inf_{u\in\mathcal F_p(\bar E_d,\bar E_x)}
\bigl(A_{\mathrm{rms}}(u,p),A_{\mathrm{tv}}(u,p)\bigr),
$$

interpreted as a two-objective Pareto minimum or scalarized with preregistered weights. The four R441 winners are feasible for endpoint improvement and common-mode guards but infeasible for the action no-harm constraints [M5-E17–M5-E19, M5-E32–M5-E34, M5-E47–M5-E49, M5-E62–M5-E64]. They are anchor points only.

## Interpretation, kept separate from fact

Larger gains plausibly produce larger parameter excursions and stronger differential-response shaping, so a positive endpoint/action correlation is physically reasonable. The present data cannot separate gain magnitude from schedule structure, nor can they establish monotonicity or a lower frontier. In particular, all winners use the largest sealed selected gain pair and all violate action stress; this pattern motivates a trade-off hypothesis but does not prove structural necessity.

## Evidence binding

All endpoint, schedule, action, and guard values are sealed or exact ratios of sealed fields in `evidence/evidence_register.csv`. The proposed response operator, target parameter $\gamma$, scalarization weights, and any exhaustive grid cardinality are **HYPOTHETICAL**. The brief’s grid description is recorded as design context, but the numerical search-space formula is not treated as a sealed JSON fact [M5-H01].

## Mechanically checkable observable list

| observable | sealed file and field | supports the stated mechanism | refutes or narrows it |
|---|---|---|---|
| temporal variation actually selected | `results/research_loop/r441_timevarying_guard/profiles/eval_*.json#/winner_candidate` | at least one adjacent segment differs | every segment is identical, as currently sealed [M5-E06, M5-E21, M5-E36, M5-E51] |
| endpoint headroom | same files, `#/guards/r_d_improvement` and `#/guards/r_cross_improvement` | both are positive | either is nonpositive |
| measured action trade-off | same files, `#/static/action_*`, `#/winner/action_*`, and `#/guards/action_stress_no_harm/*` | winner stress rises and guards fail | a winner improves endpoints while both action guards pass |
| common-mode separation | same files, `#/guards/common_no_harm/*` | all common guards pass while action guards fail | common guards fail in the same winner, confounding the interpretation |
| structural lower bound | new identified $G_{zu}$ and trajectory residuals | observed minimum action approaches or exceeds the bound over a registered local region | a feasible action violates the bound, indicating model/normalization error |
| lower-stress winner existence | fresh all-candidate guard table | at least one endpoint-eligible candidate dominates the winner in stress and passes guards | exhaustive registered evaluation finds none in the bounded class |

## Minimal follow-up experiment

Reconstruct the exact R439 candidate generator, then evaluate **every generated candidate** on every profile with the complete R441 record schema: endpoint energies, common-frequency IAE, worst peak, RoCoF, action RMS, action total variation, saturation, slew, validity, and active projection status. The sealed generator reports 350 tested candidates per profile [M5-E65–M5-E68], but candidate-level action records are absent, so fresh simulations are required.

The primary output should be a nondominated table, not a single winner. Register two queries before execution:

1. Does any candidate meet the endpoint targets and all no-harm guards?
2. Conditional on meeting the endpoint targets, what are the minimum action RMS and minimum action variation, and are they attained by a constant or genuinely varying schedule?

## Missing quantity and minimal data addition

Missing quantities are action stress for non-winning schedules, candidate-level guard results, an identified local $G_{zu}$, and uncertainty/repeatability. The minimal data addition is the complete all-candidate R441-style table. Until that table exists, “no lower-stress winner exists” and “endpoint improvement necessarily costs the observed action increase” are unsupported.
