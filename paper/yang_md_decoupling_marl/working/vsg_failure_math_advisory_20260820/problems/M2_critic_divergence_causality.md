# M2 — Critic divergence and the common-frequency gap

**Type label: (M)**

## Headline result

Twin-critic minimization does not formally create optimistic return bias: with zero-mean critic errors, the minimum is nonpositively biased in return space. For negative cost-based rewards this is pessimism, equivalently overprediction of cost. Unbounded or rapidly growing targets can still arise from off-policy bootstrapping with nonlinear function approximation, moving actors/targets, reward-scale imbalance, and shared-feature coupling; the minimum operator does not make that learning system a contraction. There is no formal reason that such divergence must corrupt the common-frequency channel specifically. A common-specific causal claim requires head-specific action-gradient evidence or an intervention that stabilizes the critic and selectively closes the common gap.

## Hard facts

The R421 diagnostic readout has critic-loss fourth-quartile/first-quartile ratios between $24.384446294632866$ and $126.35909120645123$ across the six CD runs [M2-D01–M2-D02]. The R432 diagnostics have corresponding ratios between $6.240889333128229$ and $30.475773683344492$ [M2-D03–M2-D04]. In R427, the sealed original-scale readout after differential-target normalization has ratios between $0.3164662177836716$ and $1.7478648656959799$ [M2-D05–M2-D06].

R435 reports `mechanical_ok = true`, one primary pair hit, a primary threshold of four pairs, and verdict `REFUTED` for the multiplier-floor hypothesis [M2-E01–M2-E04]. In R427’s CD-arm guard-failure table, the derived counts are zero for action RMS, zero for action variation, 24 for common frequency, 24 for worst peak, and six for RoCoF [M2-D07–M2-D11]. Thus normalization materially changes the critic-loss-growth diagnostic without eliminating the common/peak guard gap in that round. This is evidence against critic divergence being a sufficient cause; it is not proof that divergence has no causal contribution.

## Assumption set

For channel $c$, let the two target critics estimate the return $Q_c^\pi$ as

$$
\widehat Q_{c,i}=Q_c^\pi+\varepsilon_{c,i},\qquad i\in\{1,2\}.
$$

Assume, for the bias proposition only, that $\mathbb E[\varepsilon_{c,i}\mid s,a]=0$. Independence and identical distributions are not required. Let the TD target be

$$
y_c=r_c+\gamma\min_i\widehat Q^-_{c,i}(s',\pi^-(s')).
$$

For actor-bound statements, assume differentiable actors and critic action gradients on the visited state-action set.

## Result M2.1 — signed bias of the twin minimum

Conditioned on $(s,a)$,

$$
\mathbb E\!\left[\min_i\widehat Q_{c,i}\right]-Q_c^\pi
=\mathbb E[\min(\varepsilon_{c,1},\varepsilon_{c,2})]\le0.
$$

### Proof

For any real $a,b$, $\min(a,b)\le(a+b)/2$. Taking expectations and using the zero-mean assumption gives the result.

If $Q$ is a return to be maximized, this is pessimistic return bias. If the return is the negative of a nonnegative physical cost, a more negative value corresponds to overestimating cost, not overestimating return. Therefore the specific chain “twin minimum causes optimistic common-return estimates” has the wrong generic sign under the stated assumptions.

## Result M2.2 — why bootstrapped growth remains possible

For a fixed policy and exact tabular Bellman operator, the discounted evaluation map is a $\gamma$-contraction in the sup norm. The implemented learning map is not that operator: it combines off-policy sampling, nonlinear approximation, stochastic gradient steps, moving target networks, actor changes, and a minimum of approximate critics. None of these facts yields a global contraction of parameter updates. Target normalization can improve scale and conditioning, but it does not by itself prove stability of the coupled actor-critic recursion.

A local error schematic is

$$
e_{c,k+1}\approx \gamma\mathcal P_{\pi_k}e^-_{c,k}+b_{\min,c}+b_{\mathrm{proj,c}}+\xi_{c,k},
$$

where $b_{\min,c}\le0$ only under the zero-mean value-error model, while projection error, function-approximation error, distribution shift, and optimizer noise have no fixed sign. Growth occurs when the effective fitted-update operator has gain at or above unity on visited features, or when moving targets inject error faster than target averaging removes it.

## Result M2.3 — sufficient conditions for a bounded actor update

For a deterministic two-channel actor objective

$$
J_\pi(\theta)=
\mathbb E\left[Q_d(s,\pi_\theta(s))+\
\lambda Q_c(s,\pi_\theta(s))\right],
$$

suppose on the visited set

$$
\lVert J_{\pi,\theta}\rVert\le L_\pi,
\quad
\lVert\nabla_a Q_d\rVert\le L_d,
\quad
\lVert\nabla_a Q_c\rVert\le L_c,
\quad 0\le\lambda\le\Lambda.
$$

Then

$$
\lVert\nabla_\theta J_\pi\rVert
\le L_\pi(L_d+\Lambda L_c).
$$

An explicit actor-gradient clip further bounds the applied update. Bounded critic **values** alone do not imply bounded $\nabla_aQ$; value clipping must be paired with action-Lipschitz control, spectral/gradient constraints, or direct actor-gradient clipping.

### Proof

Apply the chain rule and submultiplicativity of induced norms, then use the triangle inequality and the multiplier bound.

## Why common-specific corruption is not automatic

A shared actor receives the sum of channel action gradients. Divergence becomes common-specific only if at least one channel asymmetry is present, for example:

- the common critic has larger action-gradient error or scale;
- common features dominate a shared encoder;
- the multiplier or reward weight amplifies the common head;
- action directions that reduce the estimated common cost increase the true worst-peak metric;
- target normalization differs by channel in a way that changes effective step size.

Critic-loss growth, by itself, is a scalar training diagnostic and does not identify which action-gradient component drives the policy. R427’s reduced original-scale growth together with persistent common/peak failures [M2-D05–M2-D11] weakens a simple “loss divergence alone causes the gap” model.

## Interpretation, kept separate from fact

The surviving hypothesis should be narrowed to: **unstable or inaccurate critic learning may contribute to the common-frequency gap through channel-specific action-gradient error**. The package does not support the stronger statement that divergence is the cause, that the bias is optimistic, or that common-mode corruption is mathematically necessary.

R435 removes the registered multiplier-floor explanation [M2-E04]. It does not elevate the remaining critic hypothesis from correlation to causation; elimination of one alternative is not an intervention on the critic mechanism.

## Evidence binding

The ratio ranges and guard counts are exact aggregations over named JSON fields, with all source roots listed in `evidence/m2_ratio_sources.json` and indexed in `evidence/evidence_register.csv`. No discount factor, reward normalization constant, gradient clip, or channel weight is numerically inserted here unless sealed in the cited JSON. Symbolic constants in the propositions are not fitted values.

## Mechanically checkable observable list

| observable | sealed/new file and field | supports “critic error causes common gap” | refutes or weakens it |
|---|---|---|---|
| critic growth | R421/R432 critic Q4/Q1 fields listed in `evidence/m2_ratio_sources.json` | large growth is reproduced before common degradation | common degradation precedes growth or occurs without it |
| normalization intervention | R427 `#/critic_loss_original_readout/*/ratio` plus `#/classification/guard_failures` | reducing critic growth also reduces common/peak failures within matched pairs | growth falls to the sealed R427 range [M2-D05–M2-D06] while common/peak failures persist [M2-D09–M2-D10] |
| multiplier alternative | R435 `/mechanical_ok`, `/primary_pairs_hit`, `/primary_threshold`, `/verdict` | floor intervention improves the registered number of pairs | current one-versus-four result and `REFUTED` verdict remain [M2-E01–M2-E04] |
| head-specific gradient error | new files: true/critic $\nabla_a Q_d$, $\nabla_a Q_c$, cosine with realized physical changes | common-head gradient error grows first and predicts harmful actions | differential and common errors are similar, or common gradient is accurate |
| head-specific stabilization | new factorial: stabilize common head only, differential head only, both, neither | common-only stabilization selectively improves common/peak guards | only differential stabilization helps, or neither affects guards |
| frozen-replay causality | new frozen replay/checkpoint intervention | replacing a divergent critic with a stable matched critic changes actor updates and common outcomes | actor/common outcomes remain unchanged despite corrected critics |
| temporal precedence | update-aligned logs | critic error crosses a preregistered threshold before common cost/peak degradation | no consistent precedence across seeds |

## Minimal discriminating experiment

Use matched seeds and a fixed replay stream in a head-specific stabilization factorial. Apply the same target-clipping/normalization or Lipschitz control to: common head only, differential head only, both heads, and neither (**HYPOTHETICAL DESIGN**). Save critic values, action gradients, actor updates, target statistics, and physical common/differential metrics at aligned updates. Add a frozen-actor phase to test whether critic targets stabilize independently, followed by a frozen-replay actor-update phase to isolate how each critic changes the action direction.

The causal prediction is selective: common-head stabilization should reduce common-frequency and worst-peak failures more than differential-head stabilization, and the change should be mediated by corrected common-head action gradients. Failure of this pattern refutes the proposed common-specific mechanism even if aggregate critic losses still grow.

## Missing quantity and minimal data addition

Missing quantities are per-channel critic outputs and action gradients, aligned target statistics, true local return gradients, intervention-matched common outcomes, and temporal precedence. The minimal addition is the head-specific stabilization/frozen-replay audit. Until then, critic divergence is a plausible co-factor with medium-to-low causal confidence, not an identified driver.
