# M4 — Residual SAC near the verified energy-port anchor

**Type label: (M)**

## Headline result

The sealed experiment establishes practical collapse to the anchor, but the proposed proof “all reward terms are non-positive, therefore zero residual is a local maximum” is not valid without stronger conditions. Zero residual is stationary only when the first variation of the soft action value vanishes on the residual-policy tangent space; local optimality additionally requires nonpositive curvature of return. The current package contains endpoint summaries, not the required local gradients or Hessians, so identity can be described as an observed attractor and tested mechanism, not a derived optimum of the implemented SAC objective.

## Hard facts

R436 is classified `NO-LEARNING-INCREMENT` [M4-E01]. The deterministic bandpass passes all sealed variants [M4-E02], while neither residual arm has any variant listed as beyond the deterministic anchor [M4-E03–M4-E04]. At nominal conditions, the bandpass has $(r_d,r_{\mathrm{cross}})=(0.9389467910702068,0.5397906554502304)$ [M4-E05–M4-E06]. The message residual has nominal medians $(0.9398009144308567,0.5405310760841595)$ [M4-E07–M4-E08], and the no-message residual has $(0.9376199350112616,0.5397064161558028)$ [M4-E09–M4-E10].

Across all sealed variants, the maximum absolute median deviation from the bandpass is $0.0008902254251293984$ in $r_d$ and $0.002347966350935149$ in $r_{\mathrm{cross}}$ for the message residual [M4-D01–M4-D02], and $0.0014429314998225529$ and $0.0011200990341657113$ for the no-message residual [M4-D03–M4-D04]. These are endpoint-proximity facts; they are not policy-gradient measurements.

The package SAC implementation uses twin critics, a minimum target, and the actor loss

$$
\mathcal L_\pi=\mathbb E[\alpha\log\pi(a\mid s)-\min(Q_1(s,a),Q_2(s,a))]
$$

at `src/andes_rl_kundur/agents/sac.py` lines 72–100. This is package-source evidence, not a numerical experiment field.

## Assumption set

Let $a_0(s)$ be the deterministic anchor and let $v$ denote a finite-dimensional residual-policy perturbation, so $a=a_0+v$ locally. Assume:

1. The active projection/actuator mode remains fixed and the expected discounted physical return $J(v)$ is twice differentiable at $v=0$.
2. The residual-policy tangent cone at identity is $\mathcal T$.
3. For the SAC statement, the critic is differentiable in action and the policy reparameterization is differentiable; nondifferentiability of $\min(Q_1,Q_2)$ is handled by a selected active critic or a subgradient.
4. Critic approximation error is distinguished from the true physical return.

## Result M4.1 — exact local-optimality condition

Suppose

$$
J(v)=J(0)+g^\top v+\frac12v^\top H v+o(\lVert v\rVert^2).
$$

A necessary first-order condition for identity to be a local maximum is

$$
g^\top d\le0\quad\text{for every }d\in\mathcal T.
$$

If $\mathcal T$ is a linear space, this reduces to the projected-gradient condition $\Pi_{\mathcal T}g=0$. A sufficient strict condition is

$$
d^\top H d<0\quad\text{for every nonzero }d\in\mathcal T
$$

in addition to stationarity.

### Proof sketch

For any feasible direction $d$, apply the expansion to $v=td$ as $t\downarrow0$. A positive directional derivative contradicts local maximality. If the first variation vanishes and the quadratic form is strictly negative on every feasible nonzero direction, the second-order term dominates the remainder in a sufficiently small neighborhood.

## Result M4.2 — SAC mean-residual stationarity

For a location-type residual policy $a=a_0+m_\theta(s)+L_\theta(s)\varepsilon$, the reparameterized mean-gradient of the actor loss at identity contains

$$
\nabla_\theta\mathcal L_\pi
=
\mathbb E\!\left[
J_{m,\theta}(s)^\top
\left(
\alpha\nabla_a\log\pi(a\mid s)-\nabla_a Q_{\min}(s,a)
\right)
\right]
+\text{direct entropy/covariance terms}.
$$

For a Gaussian location family with fixed covariance, entropy is independent of the mean, so zero mean residual is stationary only if

$$
\mathbb E[J_{m,\theta}^\top\nabla_aQ_{\min}]=0.
$$

A bounded or non-positive reward does not imply this equality.

## Why the non-positive-penalty argument is insufficient

If each reward term has the special form $-q_k(v)$ with $q_k(v)\ge0$, $q_k(0)=0$, and the future state distribution is fixed, then $v=0$ is indeed a pointwise maximizer. The implemented control problem is different: changing $v$ changes the future trajectory and can reduce frequency penalties even if it increases an action-related penalty. Moreover, “all terms are non-positive” provides an upper bound on reward values, not the sign of the derivative at the anchor. The conjecture becomes valid only after verifying zero first variation and negative curvature of the full discounted return, including state-distribution effects.

## Interpretation, kept separate from fact

The endpoint proximity is consistent with at least four mechanisms:

- the anchor is genuinely locally optimal in the residual class;
- the critic learns an approximately flat action-value landscape near the anchor;
- projection or action scaling suppresses the residual;
- finite training and entropy tuning fail to discover a small improvement direction.

The current files do not distinguish these cases. Calling identity a “fixed point” is safe only as an empirical training outcome unless the update vector field at the saved checkpoint is measured.

A reward difference $r(a_0+v)-r(a_0)$ subtracts a state-dependent or constant baseline. When the subtracted term is action-independent, it leaves the exact policy gradient unchanged and cannot create a missing improvement direction. Potential-based shaping can change learning transients while preserving optimal policies, but it does not make a physically dominated identity policy optimal or nonoptimal by itself.

## Evidence binding

All reported endpoint values and maximum deviations are sealed or exact computations from `results/research_loop/r436_energy_residual_sac/formal_analysis.json`, indexed in `evidence/evidence_register.csv`. No gradient, Hessian, entropy coefficient, perturbation amplitude, or confidence threshold is inferred. Such quantities are **HYPOTHETICAL** until measured and sealed.

## Mechanically checkable observable list

| observable | sealed/new file and field | supports identity-local-optimum mechanism | refutes or weakens it |
|---|---|---|---|
| endpoint collapse | R436 `#/classification/beyond_deterministic_variants/*` and `#/variants/*` | lists remain empty and deviations stay near zero [M4-E03–M4-E04, M4-D01–M4-D04] | a residual arm reproducibly exceeds the anchor on a registered variant |
| true return first variation | new symmetric perturbation file: return at $+\epsilon d$, $0$, $-\epsilon d$ | centered slope is statistically zero in every registered tangent direction | any direction has a reproducible positive return slope |
| local curvature | same file, second differences | curvature is negative in every material feasible direction | a positive-curvature or improving direction exists |
| critic action gradient | saved checkpoint diagnostic: `grad_a_q1`, `grad_a_q2`, active-min critic, projection Jacobian | projected expected gradient is near zero and stable across seeds | critic predicts a substantial improving residual that the actor does not follow |
| update fixed point | checkpoint-before/after actor parameters and optimizer state | one update produces no material parameter/action change | update moves away from zero residual |
| projection suppression | raw residual, projected action, active-set log | raw residual is nonzero but projection maps it near the anchor | raw and projected residuals agree, eliminating projection as the cause |

## Minimal discriminating experiment

At each sealed R436 checkpoint, select a registered orthonormal basis of residual-action directions. Evaluate paired trajectories at $\pm\epsilon d$ around the anchor with common random numbers, repeat over a decreasing **HYPOTHETICAL** $\epsilon$ sequence, and store physical return, each reward component, endpoint energies, projection mode, and action stress. In parallel, export the twin-critic action gradients and one actual actor update. This single experiment separates physical local optimality, critic flatness/error, actor optimization failure, and projection suppression.

## Missing quantity and minimal data addition

The missing quantities are the true-return directional derivatives, curvature, critic action gradients, actor update vector, entropy/covariance contribution, and action-projection Jacobian. The minimal addition is the symmetric local perturbation plus checkpoint-gradient audit above. Without it, the exact identity-optimality condition is known mathematically, but its premises are not verified for R436.
