# M1 — Why the sign-corrected projected dual stays at its ceiling

**Type label: (M)**

## Headline result

For the registered projected dual-ascent rule, an upper-bound multiplier is an absorbing state exactly while the corresponding constraint residual is nonnegative. The sealed R425 and R427 traces have positive residuals throughout their recorded ranges and all stored multipliers equal the ceiling, so the pinning is mechanically consistent with persistent constraint violation. Fixed-step overshoot can explain arrival at the ceiling but cannot explain remaining there when the residual becomes negative. The pinning is not an infeasibility certificate because the actor problem is nonconvex and the multiplier ceiling truncates the ordinary Lagrange dual.

## Hard facts

R425 seals a multiplier step of $0.05$, ceiling $10.0$, and RMS/TV harm factors $1.1$ [M1-E01–M1-E04]. Across the six R425 CD runs, the RMS residual has minimum/median/maximum $1.1145563318348541$, $3.786856718685509$, and $10.056334414179936$ [M1-D01–M1-D03]; the TV residual has $2.8535241133927607$, $4.313138369072675$, and $6.744472047011522$ [M1-D04–M1-D06]. Every stored RMS and TV multiplier equals the sealed ceiling [M1-D07].

For R427, the RMS residual range summary is $0.9425266037414739$, $3.750649846553069$, and $12.14764007163069$ [M1-D08–M1-D10]; the TV summary is $2.8400944051296677$, $4.292259382470758$, and $6.6992488752983546$ [M1-D11–M1-D13]. Again every stored multiplier equals the ceiling [M1-D14]. These aggregates are exact calculations over the six named `guard_multiplier_readout` run objects listed in `evidence/m1_aggregate_source_roots.json`.

## Assumption set

For one constraint, assume the registered update is

$$
\mu_{k+1}=\Pi_{[0,U]}\bigl(\mu_k+\eta g_k\bigr),
$$

where $\eta>0$, $U>0$, $g_k$ is positive when the constraint is violated, and $\Pi$ denotes Euclidean projection. The actor/primal update may be nonconvex and stochastic. The two registered constraints follow the same rule componentwise.

## Result M1.1 — exact ceiling-persistence condition

If $\mu_k=U$, then

$$
\mu_{k+1}=U\quad\Longleftrightarrow\quad g_k\ge0.
$$

If $g_k<0$, the next multiplier is strictly below $U$.

### Proof

At the ceiling, the unprojected update is $U+\eta g_k$. For $g_k\ge0$ it lies at or above $U$, so projection returns $U$. For $g_k<0$ it lies below $U$; projection can return a point in $[0,U)$ but never $U$.

## Corollary M1.2 — what fixed-step overshoot can and cannot do

A finite step can cause an iterate with $\mu_k<U$ to overshoot and project to $U$. Once at $U$, however, any negative residual must make the multiplier leave the ceiling on the next update. Therefore persistent exact pinning together with persistently positive residuals is the expected projected-ascent behavior, not a numerical paradox.

## Mechanism prediction

The most direct explanation of R425/R427 is **primal non-response**: the learned actor does not move into the guard-feasible set, so positive residuals keep the dual at the cap. Several causes remain possible beneath that label:

- the bounded policy class cannot satisfy the guards on the training distribution;
- a feasible policy exists but the nonconvex actor optimizer cannot find it;
- constraint gradients are weak, noisy, or opposed to endpoint gradients;
- aggregate multipliers hide profile-specific violations;
- projection or action mapping makes the actor insensitive to the penalized direction;
- the cap is too small to materially alter the actor objective.

The sealed data identify the update-level reason for pinning but not which primal cause applies.

## KKT and certificate boundary

For an unconstrained multiplier and a convex problem satisfying a constraint qualification, KKT conditions link primal feasibility, stationarity, and complementary slackness. Those premises are not established here. The imposed ceiling replaces the dual domain $\mu\ge0$ by $0\le\mu\le U$. Saturation at $U$ can simply mean that the best truncated penalty remains insufficient. It does not prove that the physical guard set is empty, that the policy class is infeasible, or that a larger multiplier would fail.

## Interpretation, kept separate from fact

Because every stored residual aggregate is positive and every multiplier is at the cap [M1-D01–M1-D14], the data refute the narrow explanation “the multiplier remains pinned despite a negative signed gap.” They remain compatible with an earlier sign error before R425, but the sign-corrected rounds themselves behave as projected ascent predicts.

The fixed step may affect how quickly the ceiling is reached and may induce oscillation away from it. It is not the primary explanation for exact persistence in the sealed positive-residual regime.

## Evidence binding

All numerical values are sealed fields or aggregate functions over explicitly named JSON arrays. The aggregation roots are provided in `evidence/m1_aggregate_source_roots.json`; the results are indexed in `evidence/evidence_register.csv`. No unlogged update, gradient, or feasibility conclusion is inferred.

## Mechanically checkable observable list

| observable | sealed/new file and field | supports the mechanism | refutes or narrows it |
|---|---|---|---|
| ceiling persistence | R425/R427 `#/guard_multiplier_readout/<run>/mu_rms_trace` and `mu_tv_trace` | values remain at `multiplier_max` while residuals are nonnegative | any negative residual is followed by an unchanged ceiling multiplier under the same update rule |
| signed residual | same run objects, `rms_residual_trace` and `tv_residual_trace` | residuals stay positive, as summarized [M1-D01–M1-D13] | residuals become negative for sustained updates without multiplier release |
| cap insufficiency | new cap sweep with unchanged actor/reward/seeds | larger caps increase multiplier magnitude but guards still fail | a modest cap increase produces guard feasibility |
| step-size effect | new step sweep | arrival time changes while the final positive-residual/cap regime remains | pinning disappears solely by reducing the step at fixed cap and identical gradients |
| primal-gradient conflict | new logs of endpoint gradient, each constraint gradient, and their cosine/Gram matrix | constraint gradients are weak or oppose the endpoint direction | gradients provide a strong feasible descent direction that the actor consistently ignores |
| aggregate-mask effect | new per-profile multipliers/residuals | profile-specific duals reduce violations hidden by aggregation | per-profile duals behave identically and remain infeasible |
| policy-class infeasibility | independent class search/certificate | no feasible policy exists in a precisely bounded class | a feasible controller in the same class is found |

## Minimal discriminating experiment

Run a registered factorial over multiplier ceiling and step while holding replay generation, policy initialization, seeds, reward, and actor optimizer fixed. Log **pre-update** and **post-update** multipliers, signed residuals, actor loss components, action-projection Jacobian, and per-constraint actor gradients at every dual update. Add one per-profile-dual arm. The decisive checks are algebraic: negative $g_k$ must release a capped multiplier; changing $\eta$ should mainly alter transit; changing $U$ tests penalty insufficiency; per-profile duals test aggregation.

## Missing quantity and minimal data addition

Missing quantities are the full time alignment between residual and multiplier updates, actor/constraint gradients, cap/step interventions, per-profile residuals, and an independent feasible-policy witness. The minimal addition is an update-level trace with one cap sweep and one step sweep. Until then, the ceiling mechanism is high-confidence at the update level but the deeper primal cause remains unclassified.
