# Math Problem Draft — finite-record TV/RMS mechanism certificate

**Outcome:** `drafted`

## Authority Snapshot

- Project: `andes-rl-kundur`
- Manuscript line: `yang_md_decoupling_marl`
- Fixed paper title: **Decoupling-Oriented Coordination of Paralleled VSGs
  With Multi-Agent Reinforcement Learning**
- Snapshot date: 2026-09-01
- Formal parent: R485 / `CLM-1525` / status `VALID-MIXED`
- Post-hoc derivative: R486 / `CLM-1530` / status
  `VALID-POSTHOC-INTAKE`
- Decision governed here: whether the Discussion may make a compact,
  mathematically precise finite-record mechanism statement. This problem does
  not change the 121/208 or 0/208 headline and does not authorize simulation,
  training, or a controller intervention.

## Research question

For the sealed deterministic actor and componentwise amplitude/slew projector,
can one construct a finite-record, nonsmoothness-safe certificate that
separates what the existing data actually identify about:

1. variation associated with the previous-executed-action actor input;
2. quasi-static actor-output magnitude;
3. attenuation introduced by the production projector; and
4. the non-identifiable remainder due to recorded plant observations and their
   action dependence?

The certificate must determine whether the current phrases “previous-action
feedback amplifies TV” and “a quasi-static actor setpoint retains RMS” are
mathematically justified, require qualification, or fail. It must not convert
recorded-path ablations into closed-loop causal effects.

## Exact implemented objects

There are four row-wise deterministic actors. For agent `i`, time `t`, and one
record,

\[
o_{i,t}\in\mathbb R^7,\qquad p_{i,t-1}\in[-1,1]^2,
\]

\[
r_{i,t}=\pi_{\theta_i}(o_{i,t},p_{i,t-1})
=\tanh\!\left(\mu_{\theta_i}([o_{i,t};p_{i,t-1}])\right)\in[-1,1]^2.
\]

`mu` is a four-hidden-layer, width-128 ReLU network. Evaluation uses the mean
head followed by `tanh`; the stochastic log-standard-deviation head is not used.

The exact normalized executed action is the componentwise map

\[
p_{i,t}=\Pi_\delta(p_{i,t-1},r_{i,t})
=\operatorname{clip}_{[-1,1]}
\left(p_{i,t-1}+
\operatorname{clip}_{[-\delta,\delta]}(r_{i,t}-p_{i,t-1})\right),
\qquad \delta=0.25,
\]

with conservative float32 recording at the slew boundary. Each record resets
`p_{i,-1}=0`.

For a channel `c` in `{M,D}`, six records, 150 steps, and four agents, the
diagnostics use

\[
\operatorname{RMS}_c(a)=
\sqrt{\frac1N\sum_{n,t,i}a_{n,t,i,c}^2},
\]

\[
\operatorname{TV}_c(a)=
\sum_{n,t,i}|a_{n,t,i,c}-a_{n,t-1,i,c}|,
\qquad a_{n,-1,i,c}=0.
\]

The probes construct three non-plant counterfactuals while retaining recorded
observations:

- `fixed-prev raw`: replace the two previous-action input slots at every step
  by their within-record mean, without recursive plant replay;
- `constant-anchor raw`: replace both the seven observation slots and the two
  previous-action slots by their within-record temporal means;
- `recursive fixed-prev projected`: feed the within-record previous-action mean
  into the actor, but recursively propagate the actor output through the exact
  projector; plant observations remain on the sealed path.

## Premises fixed by the package

- All numerical evidence is finite-bank, post-hoc, and conditional on sealed
  observations/checkpoints.
- The 24-policy feedback grid covers eight frozen factorial arms and seeds 501,
  513, and 526 on `canary_eval_a`.
- The 24-policy x four-profile RMS grid covers 96 policy-profile blocks and 192
  M/D ratios.
- The representative full trace/checkpoint data are `an_cn_r0`, seed 501,
  final checkpoint, all four profiles.
- ReLU, `tanh`, box clipping, and slew clipping are piecewise smooth or
  nonsmooth. A theorem may use one-sided derivatives or Clarke generalized
  Jacobians, but it must state the required active-set assumptions.
- No attached datum establishes the action-dependent plant observation path
  under a modified actor. Recorded observations must be treated as frozen
  covariates, not endogenous counterfactual trajectories.

## Load-bearing subgoals

### S1 — metric and projector audit

Re-derive the exact finite-record RMS/TV definitions and prove the strongest
valid non-expansiveness, increment, and total-variation inequalities for
`Pi_delta`. Distinguish a one-step map with fixed previous action from the
recursive stateful map. State what, if anything, follows from the observed
projected/raw TV ratios.

### S2 — identifiable decomposition

Construct a rigorous additive decomposition, inequality-based attribution, or
set-valued certificate for the actual, fixed-prev, constant-anchor, and
projected sequences. If no unique additive decomposition exists, prove the
non-identification and give the narrowest defensible quantities, such as
telescoping contrasts, upper/lower bounds, or a declared Shapley allocation.
Do not silently interpret differences of TV or ratios of RMS as causal shares.

### S3 — actor sensitivity certificate

For the ReLU-`tanh` actor, derive a computable finite-record sensitivity
certificate for the previous-action slots. Prefer exact pathwise Jacobians or
generalized Jacobians over a global product-of-spectral-norm bound if the
latter is too loose. Specify how the attached representative checkpoint and
traces can verify the certificate and what additional arrays would be needed
for all 24 checkpoints.

### S4 — quasi-static RMS audit

Determine exactly what a constant-anchor/actual RMS ratio near one establishes.
Separate temporal mean, temporal variance, actor nonlinearity, and cross-agent
aggregation. Decide whether “quasi-static setpoint retains RMS” is valid and
whether “dominant RMS source” is too strong, particularly because only 73.44%
of the 192 ratios reach 0.90 and the M/D channels differ.

### S5 — inference and claim boundary

Audit whether the 24-policy and 24x4 grids support a descriptive finite-bank
statement only or any uncertainty statement. No superpopulation sampling
assumption is declared. Explicitly separate:

- exact replay statements;
- finite-grid prevalence;
- actor-path intervention statements;
- training-causal and closed-loop claims that remain unidentified.

### S6 — paper-facing result

Return the smallest manuscript-safe proposition or paragraph. It may be a
formal lemma, a qualified finite-record statement, or `NO MATHEMATICAL CLAIM`
if the data do not justify strengthening. The result must fit a five-page IEEE
conference paper and must not become a fourth main contribution.

## Required terminal dispositions

Return one of:

- `CERTIFIED-BOUNDED-MECHANISM`: a replayable certificate supports a strictly
  bounded finite-record claim;
- `QUALIFIED-DESCRIPTIVE-ONLY`: the data support only a sharpened descriptive
  statement and the reasons are proved;
- `DATA-UNDECIDABLE`: essential objects are missing; list the minimal missing
  arrays/maps and why no surrogate is valid;
- `CURRENT-LANGUAGE-FAILS`: one or both current mechanism phrases are
  mathematically misleading and must be replaced.

Mixed subgoal dispositions are allowed, but there must be one overall terminal
disposition.

## Claim ceiling

Even a successful answer is limited to the attached actor architecture,
projector, checkpoints, recorded paths, finite profiles, and stated
interventions. It cannot establish training causality, unique root cause,
closed-loop endpoint preservation, stability, safety, actuator wear/energy,
topology generalisation, convergence, optimality, or benefit from retraining.

`Q-0112` is deliberately excluded. It concerns a successor-line endogenous
non-anticipative information tree and lacks the action-dependent observation
and fleet-common-coordinate ownership maps; it is not a condition for the
current paper.
