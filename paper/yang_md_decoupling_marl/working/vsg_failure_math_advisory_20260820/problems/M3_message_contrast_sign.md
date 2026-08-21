# M3 — Why neighbour information can look harmful in one learner and useful in another

**Type label: (M)**

## Headline result

Under exact population optimization, adding neighbour observations cannot reduce optimal value when the message-enabled policy class contains the no-message class. Therefore the negative R410 message contrast is not a theorem about the intrinsic value of the information. It must be attributed to finite-sample estimation, optimization, non-nested implementation, distribution shift, or reward/critic-induced gradient interference. R438 gives bounded evidence that the adapted-SAC differential benefit is observation-channel leaning; it does not resolve the off-diagonal mechanism.

## Hard facts

In R410, the CD-MATD3 message arm has differential/off-diagonal ratios $2.5427448906909156$ and $5.256929868426683$ relative to the deterministic reference [M3-E01–M3-E02], while the no-message arm has $2.006340749241337$ and $2.9462537319949704$ [M3-E03–M3-E04]. The registered message improvements over no-message are negative: $-0.2673544569397846$ for differential energy and $-0.7842760151099087$ for off-diagonal energy [M3-E05–M3-E06].

In R431, the adapted-SAC message arm has ratios $0.6347436524354518$ and $0.5900367008463987$ [M3-E07–M3-E08], compared with $0.8459633377917004$ and $0.8959790096545148$ for no-message [M3-E09–M3-E10]. Its registered improvements over no-message are positive: $0.24967947890935285$ and $0.3414614689758034$ [M3-E11–M3-E12].

R438 records observation-only medians $0.0005160439825440163$ and $0.00006809853001321975$ [M3-E13–M3-E14], reward-only medians $0.0007094475978791034$ and $0.00009068492411745009$ [M3-E15–M3-E16], and sealed message/no-message anchors [M3-E17–M3-E20]. Its registered side classifications are: observation-only is on the message side for the differential endpoint but on the no-message side for off-diagonal response; reward-only is on the no-message side for both [M3-E21–M3-E24]. The registered verdict is `BOUNDED-UNCLASSIFIED` [M3-E25].

## Assumption set

Let $X$ denote own-state information, $N$ neighbour information, $A$ the action, and $R$ the return under a fixed evaluation distribution. Assume:

1. The message-enabled policy class $\Pi_{X,N}$ contains a realization that ignores $N$ and reproduces every policy in $\Pi_X$.
2. The population comparison uses the same dynamics, reward, action constraints, and evaluation distribution.
3. “Value” is maximized; for cost notation, signs are reversed consistently.
4. Any claim about the observed trained policies additionally depends on finite data, the optimizer, critic architecture, regularization, and message-mask implementation.

## Result M3.1 — nonnegative population information value

Define

$$
V_X^*=\sup_{\pi\in\Pi_X}J(\pi),\qquad
V_{X,N}^*=\sup_{\pi\in\Pi_{X,N}}J(\pi).
$$

Under Assumptions 1–3,

$$
V_{X,N}^*-V_X^*\ge 0.
$$

### Proof

By nesting, every $\pi\in\Pi_X$ is feasible in $\Pi_{X,N}$ through the realization that ignores $N$. Taking the supremum over the larger set cannot reduce the optimum.

## Result M3.2 — finite-learner sign decomposition

For a trained estimator, write schematically

$$
J(\widehat\pi_{X,N})-J(\widehat\pi_X)
=
\underbrace{V_{X,N}^*-V_X^*}_{\Delta_{\mathrm{info}}\ge0}
-
\underbrace{\Delta_{\mathrm{estimation}}}_{\text{finite data}}
-
\underbrace{\Delta_{\mathrm{optimization}}}_{\text{training}}
-
\underbrace{\Delta_{\mathrm{implementation}}}_{\text{non-nesting / masking / distribution}}.
$$

This is an accounting identity after defining each excess-value term relative to its population optimum. A negative trained contrast is possible even though $\Delta_{\mathrm{info}}\ge0$.

## Mechanism prediction

Neighbour masking should improve a finite learner when the following two conditions hold together:

1. **Low conditional task value:** neighbour variables are approximately redundant for the relevant action-value gradient, e.g.
   $$
   \operatorname{Var}\!\left(\mathbb E[\nabla_a Q(X,N,A)\mid X,N]\mid X\right)
   $$
   is small on the training/evaluation support.
2. **Positive complexity or interference cost:** adding $N$ increases estimation variance, worsens conditioning, creates spurious correlations, or causes shared-feature gradients from common and differential cost heads to interfere.

Conversely, neighbour access should help when it changes the conditional action-value gradient in a reproducible way and the actor/critic can represent that dependence without destructive sharing. A common-frequency penalty can make neighbour information useful as an estimate of coherent drift, but the current files do not contain learned feature maps, head gradients, or conditional mutual-information estimates. That explanation remains interpretation, not sealed fact.

## Interpretation, kept separate from fact

The R410/R431 sign reversal is consistent with an architecture-dependent finite-learning effect. It is not evidence that “messages are harmful” for CD-MATD3 in principle or “messages are always useful” for SAC. The strongest package-supported statement is narrower: the observation channel carries the R438 differential-side shift, whereas the off-diagonal endpoint does not separate under the registered isolation [M3-E21–M3-E25].

The proposed confusability account—joint/common-differential critics treating neighbour drift as own-state drift—would require direct evidence from channel-specific gradients or representation probes. Nothing in the sealed endpoint tables identifies that internal cause.

## Evidence binding

Every numerical contrast above is a sealed JSON field indexed in `evidence/evidence_register.csv`. No cross-family value is treated as a controlled causal contrast: R410 and R431 differ in learner family and training design. The factorial arm counts and any new sample sizes below are **HYPOTHETICAL DESIGN** quantities until registered.

## Mechanically checkable observable list

| observable | sealed file and field | supports the prediction when | refutes or weakens it when |
|---|---|---|---|
| CD message sign | `results/research_loop/r410_message_repair/endpoint_table.json#/full_method_improvement_vs_comparators/cd_matd3_no_message/*` | both values remain negative under exact recomputation [M3-E05–M3-E06] | either registered contrast changes sign |
| adapted-SAC message sign | `results/research_loop/r431_sac_slew/formal_analysis.json#/b1_table/message_improvement_vs_comparators/cd_matd3_no_message/*` | both values remain positive [M3-E11–M3-E12] | either registered contrast changes sign |
| observation-channel differential attribution | `results/research_loop/r438_sac_message_channels/formal_analysis.json#/classification/channel_sides/sac_obs_only/disturbance` | field is `message` [M3-E21] and paired uncertainty excludes the no-message anchor | field changes to `no_message`, or precision shows no separation |
| reward-channel attribution | same file, `#/classification/channel_sides/sac_rew_only/*` | a reward-only arm moves to the message side | both remain `no_message` [M3-E23–M3-E24], as currently observed |
| off-diagonal observation value | same file, `#/classification/channel_sides/sac_obs_only/off_diagonal` | actor/critic message access moves this field to `message` under a registered repeat | field remains `no_message` [M3-E22] with adequate power |
| finite-learning penalty | new logs: train/validation TD loss, actor-gradient variance, feature condition number, message-shuffle placebo | message access increases variance/conditioning cost while population or oracle value is nonnegative | negative endpoint contrast persists without any measurable estimation/optimization penalty and under verified nested exact optimization |

## Minimal discriminating experiment

Use a **HYPOTHETICAL** complete binary factorial with three controlled factors: neighbour access to the actor, neighbour access to the critic, and neighbour-dependent reward terms. Hold replay generation, seeds, network capacity, optimization budget, masks, and evaluation profiles fixed. The factor effects have distinct interpretations:

- actor-access effect: execution-time coordination value;
- critic-access effect: representation/credit-assignment value;
- reward effect: objective semantics;
- interactions: message value that exists only under a particular reward or critic architecture.

Add a shuffled-neighbour placebo with identical marginal statistics. For the off-diagonal endpoint, support an observation-value mechanism only if true neighbour access beats both no-message and shuffled-message arms with paired uncertainty, while the reward-only contrast remains absent. This extends R438 without re-labelling its current non-separation as a causal result.

## Missing quantity and minimal data addition

Missing quantities are paired uncertainty for the R438 side assignment, actor-versus-critic message access, channel-specific critic gradients, representation conditioning, and a shuffled-message placebo. The minimal data addition is the registered factorial above with per-seed/per-profile endpoint records and gradient diagnostics. Until then, M3 remains a falsifiable mechanism prediction with medium confidence, not a theorem about the two algorithm families.
