# R485 finite-record mechanism audit — solution

## Terminal disposition

**Overall:** `CERTIFIED-BOUNDED-MECHANISM`

The package supports a strict, replayable finite-record statement about the production rate limiter and a representative-checkpoint sensitivity audit. It also supports exact prevalence statements on the supplied fixed grids. It does **not** identify additive causal mechanism shares, a training cause, or any modified-controller closed-loop plant trajectory.

| Subgoal | Disposition | Result |
|---|---|---|
| S1 | `CERTIFIED` | The componentwise rate limiter is one-step non-expansive and, under the common zero reset used here, recursively total-variation diminishing with a terminal tracking-residual strengthening. |
| S2 | `NONIDENTIFIED-UNIQUE-DECOMPOSITION` | Path-vector identities, norm bounds, and declared order-specific signed contrasts are valid; additive causal shares are not identified. |
| S3 | `CERTIFIED-REPRESENTATIVE-DATA-UNDECIDABLE-FULL-GRID` | Exact active-set Jacobians, certified local regions, and kink-safe finite endpoint secants are available for the included checkpoint and four traces. The other 23 checkpoint certificates are not reconstructible from summaries. |
| S4 | `QUALIFIED-DESCRIPTIVE-ONLY` | A near-unit constant-anchor/actual RMS ratio establishes aggregate norm retention only, not temporal constancy, closeness, or source dominance. |
| S5 | `FINITE-GRID-DESCRIPTIVE-ONLY` | The enumerated banks support exact bank counts, not confidence intervals or superpopulation claims. |
| S6 | `MANUSCRIPT-PATCH-PROVIDED` | A one-equation, sub-150-word replacement is supplied in `manuscript_patch.tex`. |

## Scope, assumptions, approximations, and missing objects

**A1 — actor interpretation.** The mathematical policy is the real-valued ReLU–`tanh` map specified by the exported float32 parameters. Re-evaluation under the present CPU PyTorch runtime reproduced all sealed raw actions with maximum absolute error `7.897615432739258e-07`; the declared actor replay tolerance is `1e-6`.

**A2 — common reset.** Every TV statement below uses the registered convention `p_{n,-1}=r_{n,-1}=0`. If the raw reference begins from another initial value, the recursive TV theorem must include that initial mismatch.

**A3 — frozen observations.** `fixed-prev raw`, `constant-anchor raw`, and `recursive fixed-prev projected` are actor-path interventions conditional on the supplied observations. They are not endogenous plant counterfactuals.

**A4 — ReLU kinks.** Exact-zero tests refer to preactivations produced by the stated float32 replay. Near-zero but nonzero values are differentiable points, although their same-active-set certificate can be extremely small. At an exact kink, the Clarke construction below replaces the ordinary Jacobian.

**A5 — recursive intervention replay boundary.** The promoted recursive-intervention JSON is hash-bound and internally arithmetically consistent, and its actual projected path is independently reconstructed. The archive does not contain its stepwise intervention raw/projected arrays. Because sub-ulp actor differences can feed back recursively and change later inputs, an independent, backend-invariant reconstruction of that exact intervention path is `DATA-UNDECIDABLE` without those arrays or a bitwise-locked runtime record. No surrogate path is used in the paper recommendation.

**A6 — finite bank.** The 24 policies and 96 policy-profile blocks are the complete supplied diagnostic grids, not a random sample.

**Numerical approximation N1.** Stored float32 paths are aggregated in float64. Projector replay is exact on the supplied records; actor quantities use the tolerances recorded in `math_result.json`. The endpoint secant audit uses two evaluations of the same reconstructed actor runtime, avoiding a mixed-backend numerator.

---

## S1 — metric and projector audit

### 1.1 Exact diagnostic metrics

For one channel, flatten the six records, 150 time steps, and four agents into a finite vector. Let `D` be the record-wise first-difference operator that prepends zero to every record. Then

\[
\operatorname{RMS}(a)=N^{-1/2}\lVert a\rVert_2,
\qquad
\operatorname{TV}(a)=\lVert Da\rVert_1,
\qquad N=6\cdot150\cdot4.
\]

RMS is a scaled Euclidean norm of levels. TV is an \(\ell_1\) norm of record-wise increments. Consequently, neither differences nor ratios of these two metrics are automatically additive mechanism shares.

### 1.2 Scalar form and exact increment identities

For scalar `x,r in [-1,1]`, define

\[
P_\delta(x,r)=x+\operatorname{clip}_{[-\delta,\delta]}(r-x).
\]

The outer amplitude clip is redundant in exact arithmetic because the output lies between `x` and `r`. Equivalently,

\[
P_\delta(x,r)=\operatorname{median}(x-\delta,r,x+\delta).
\]

Let `p=P_delta(x,r)`. Then

\[
|p-x|=\min\{\delta,|r-x|\},\qquad
|r-p|=(|r-x|-\delta)_+,
\]

and, because `p` lies on the line segment from `x` to `r`,

\[
|p-x|+|r-p|=|r-x|.
\]

These are exact scalar identities. They apply componentwise to the two action channels.

### 1.3 One-step non-expansiveness

For fixed `x`, clipping is non-expansive in `r`; for fixed `r`, the median representation is a monotone piecewise-affine function of `x` with slopes in `{0,1}`. Hence

\[
|P_\delta(x,r)-P_\delta(x,s)|\le |r-s|,
\qquad
|P_\delta(x,r)-P_\delta(y,r)|\le |x-y|.
\]

The median operator is also 1-Lipschitz under the sup norm of its arguments, giving the joint bound

\[
|P_\delta(x,r)-P_\delta(y,s)|
\le \max\{|x-y|,|r-s|\}.
\]

For the vector projector this yields the corresponding componentwise/`linf` inequalities. In particular, two recursive executions driven by raw paths `r_t,s_t` and the same initial condition satisfy

\[
\lVert p_t-q_t\rVert_\infty
\le \max_{0\le k\le t}\lVert r_k-s_k\rVert_\infty.
\]

This is a path-level sup-norm stability statement. It is not, by itself, a TV or RMS contraction theorem.

### 1.4 Recursive total-variation theorem

**Theorem.** For a scalar raw path `r_t`, define `p_t=P_delta(p_{t-1},r_t)` and assume `p_{-1}=r_{-1}`. For every terminal index `T`,

\[
\sum_{t=0}^{T}|p_t-p_{t-1}|+|r_T-p_T|
\le
\sum_{t=0}^{T}|r_t-r_{t-1}|.
\]

**Proof.** Since `p_t` lies between `p_{t-1}` and `r_t`,

\[
|p_t-p_{t-1}|+|r_t-p_t|=|r_t-p_{t-1}|.
\]

The triangle inequality gives

\[
|r_t-p_{t-1}|\le |r_t-r_{t-1}|+|r_{t-1}-p_{t-1}|.
\]

Add the previously accumulated executed increments and apply induction from `p_{-1}=r_{-1}`. This proves the claim. Summation over records, agents, and either channel preserves the inequality. `QED`

Therefore, for each channel in this package,

\[
\operatorname{TV}(p)+
\sum_{n,i}|r_{n,T,i}-p_{n,T,i}|
\le \operatorname{TV}(r),
\]

so `TV(projected) <= TV(raw)` is a structural property of the exact recursion, not an empirical mechanism discovered from four traces.

The slew bound also gives

\[
\operatorname{TV}_c(p)\le 6\cdot150\cdot4\cdot0.25=900
\]

for each profile and channel.

### 1.5 Finite-record replay

The checker reconstructed all four sealed profiles and found:

- projector replay maximum absolute error: `0.0`;
- stored increment replay maximum absolute error: `0.0`;
- between-previous-and-raw violations: `0`;
- slew-limit violations: `0`.

| Profile | Raw TV M | Projected TV M | Terminal residual M | Raw TV D | Projected TV D | Terminal residual D |
|---|---:|---:|---:|---:|---:|---:|
| a | 2072.494 | 867.902 | 4.052 | 1847.392 | 733.612 | 4.426 |
| b | 1965.268 | 872.922 | 4.029 | 1881.713 | 729.290 | 4.029 |
| c | 2045.918 | 872.169 | 4.132 | 1800.486 | 751.274 | 2.070 |
| d | 2252.003 | 856.542 | 5.520 | 1980.931 | 714.424 | 5.782 |

Every strengthened TV inequality has large positive slack. The observed strict reduction quantifies how much the limiter attenuated these paths; it cannot identify why the actor produced the raw variation. The M-channel projected TV is also numerically close to its hard `900` cap; this still does not mean that the projector generated the variation.

### 1.6 No analogous RMS theorem

The rate limiter is not generally an RMS contraction under the common reset. For `delta=0.25`, the raw path

\[
r=(-0.25,-0.50,0)
\]

produces

\[
p=(-0.25,-0.50,-0.25),
\]

so `sum p_t^2=0.375 > 0.3125=sum r_t^2`. Therefore no sign may be assigned to `RMS(projected)-RMS(raw)` without evaluating the path.

---

## S2 — what can and cannot be decomposed

Let, for one channel,

- `A`: actual raw actor path;
- `F`: fixed-previous-input raw path;
- `C`: constant-anchor raw path;
- `P`: actual projected path.

### 2.1 Exact path-vector identity

The available raw paths satisfy the algebraic identity

\[
A=C+(F-C)+(A-F).
\]

Including the actual projected path gives the equally exact extension

\[
P=C+(F-C)+(A-F)+(P-A).
\]

For TV, applying the first-difference operator gives the corresponding identities for `DA` and `DP`. These are exact additive decompositions of **vectors**, not of their norms. The residual `P-A` is also a stateful transformation of the whole raw path, not an independent causal factor.

### 2.2 Why TV/RMS shares are not identified

For either `m=TV` or `m=RMS`, `m` is a norm after a fixed linear transformation. In general,

\[
m(A)\ne m(C)+m(F-C)+m(A-F)
\]

because the component vectors can align or cancel. The direction information is load-bearing. For example, three scalar component magnitudes all equal to one can sum to magnitude three when aligned or magnitude one when one component is opposed. Thus component norms alone cannot define unique additive shares.

The universal norm-only polygon certificate is

\[
L\le m(A)\le U,
\]

where

\[
U=q_0+q_O+q_P,
\]

\[
L=\max\{0,q_0-q_O-q_P,q_O-q_0-q_P,q_P-q_0-q_O\},
\]

with `q0=m(C)`, `qO=m(F-C)`, and `qP=m(A-F)`. These bounds use all identifiable component magnitudes and no unobserved directional assumption. The checker verifies them for every representative profile/channel pair.

A further exact contrast bound follows from the reverse triangle inequality:

\[
|m(A)-m(F)|\le m(A-F),
\qquad
|m(F)-m(C)|\le m(F-C).
\]

### 2.3 Valid declared allocation

A scalar telescoping allocation can be reported if its order is stated:

\[
m(A)=m(C)+[m(F)-m(C)]+[m(A)-m(F)].
\]

Appending projection gives

\[
m(P)=m(C)+[m(F)-m(C)]+[m(A)-m(F)]+[m(P)-m(A)].
\]

This is an exact bookkeeping identity, but the terms are order-dependent signed contrasts, not causal or nonnegative shares. The representative RMS audit contains `5` negative ordered contrasts among the `16` observation/previous-input terms, directly showing why “percentage contributions” would be misleading. Only the projection TV contrast has a theorem-determined sign: `TV(P)-TV(A) <= 0`.

### 2.4 Missing Shapley cell

For two factors—time-varying observations and time-varying previous-action inputs—a symmetric two-factor Shapley allocation additionally requires

\[
G=\pi(\bar o,p_{\mathrm{recorded}}),
\]

that is, anchored observations with the recorded previous-action path. It is absent. If it were available,

\[
\phi_{\mathrm{prev}}=\tfrac12[(m(G)-m(C))+(m(A)-m(F))],
\]

\[
\phi_{\mathrm{obs}}=\tfrac12[(m(F)-m(C))+(m(A)-m(G))].
\]

Without `G`, even a declared symmetric metric allocation is not numerically identified. For the complete 24-policy grid, the other 23 checkpoints/paths or precomputed missing-cell action paths are also absent. Status: `DATA-UNDECIDABLE` for full-grid Shapley values.

### 2.5 Mechanism conclusion

The strongest defensible statement is conditional and directional:

> On the supplied frozen observation paths, replacing the time-varying previous-executed-action actor input with its within-record mean greatly reduced raw TV on the tested grid.

It is not valid to conclude that previous-action feedback is a unique root cause, that it caused the training outcome, or that removing it in closed loop would preserve plant endpoints.

---

## S3 — ReLU–`tanh` previous-slot sensitivity certificate

### 3.1 Ordinary active-set Jacobian

At an input `x=[o;p]` where no hidden preactivation is zero, let `D_l` be the diagonal `0/1` ReLU activity matrix of hidden layer `l`, let `W_1^(p)` denote the last two columns of the first-layer weight matrix, and let `W_5` be the mean-head weight. With `a=tanh(mu)`, define

\[
T=\operatorname{diag}(1-a_1^2,1-a_2^2).
\]

The exact Jacobian with respect to the two previous-action slots is

\[
J_p(x)=T W_5D_4W_4D_3W_3D_2W_2D_1W_1^{(p)}.
\]

The local induced `linf` gain is `||J_p(x)||_infinity`, the maximum absolute row sum.

### 3.2 Kinks and generalized Jacobians

The policy is locally Lipschitz. At a ReLU kink, its Clarke generalized Jacobian is the convex hull of Jacobian limits from reachable adjacent activation regions. Replacing an ambiguous ReLU derivative by an element of `[0,1]` yields a computable outer generalized-Jacobian certificate; not every independent choice need correspond to a reachable activation pattern, so that interval construction must not be called an exact enumeration unless reachability is checked.

No exact hidden zero occurred at the supplied representative replay points, so ordinary Jacobians were sufficient there. The minimum nonzero absolute preactivation was nevertheless only `1.862645149230957e-08`.

### 3.3 Certified same-active-set radius

Within the saved activation pattern, each hidden preactivation `z_lj` is affine in the two previous-action coordinates. Let `g_lj` be its gradient with respect to those coordinates. A sufficient open `linf` radius preserving every saved ReLU sign is

\[
\rho(x)=\min_{l,j:\lVert g_{lj}\rVert_1>0}
\frac{|z_{lj}(x)|}{\lVert g_{lj}\rVert_1}.
\]

For every perturbation `Delta p` with `||Delta p||_infinity < rho(x)`, the hidden masks remain fixed along the segment. In that region the pre-`tanh` mean is affine in `p`, and the finite output difference can be written exactly using the two scalar `tanh` secant slopes. The corresponding norm is bounded by the effective affine previous-slot matrix because `tanh` is 1-Lipschitz.

### 3.4 Kink-safe finite endpoint certificate

For any supplied pair `p,q` at fixed observation `o`, define

\[
g_\infty(o;p,q)=
\frac{\lVert\pi(o,q)-\pi(o,p)\rVert_\infty}
{\lVert q-p\rVert_\infty},\qquad q\ne p.
\]

This is an exact realized endpoint secant gain. It remains valid if the connecting segment crosses any number of ReLU kinks. It is **not** a uniform Lipschitz upper bound.

More generally, for `gamma(s)=[o;p+s(q-p)]`, absolute continuity gives

\[
\pi(o,q)-\pi(o,p)=
\int_0^1 J_p(\gamma(s))(q-p)\,ds
\]

for almost every `s`; values assigned on the measure-zero nondifferentiability set do not change the integral, and Clarke elements provide the appropriate local set-valued description there. Consequently,

\[
\lVert\pi(o,q)-\pi(o,p)\rVert_\infty
\le
\left(\int_0^1\lVert J_p(\gamma(s))\rVert_\infty ds\right)
\lVert q-p\rVert_\infty.
\]

A validated segment-wide upper bound would require breakpoint enumeration or interval bounds along each segment. The returned checker instead reports the exact endpoint secant plus certified local radii and does not mislabel a local derivative as a finite-perturbation upper bound.

### 3.5 Representative numerical certificate

Scope: one checkpoint (`an_cn_r0`, seed 501), four profiles, six records, 150 steps, four agents; `14,400` actor inputs and `7,372,800` hidden preactivations.

| Quantity | Minimum | Median | 95th percentile | Maximum |
|---|---:|---:|---:|---:|
| Local previous-slot Jacobian `linf` norm | 0.11347 | 2.05957 | 6.62254 | 17.34549 |
| Same-active-set `linf` radius | 1.349e-08 | 8.139e-04 | 3.744e-03 | 1.573e-02 |
| Fixed-mean anchor perturbation `linf` | 4.842e-03 | 1.302e-01 | 1.970e-01 | 1.24128 |
| Fixed-mean endpoint secant gain `linf` | 0.03381 | 2.26007 | 5.86640 | 9.47095 |

None of the `14,400` fixed-mean anchor segments was certified by the isotropic local-radius test to remain in the saved active set. Of `14,400` successive previous-action segments, only the `96` zero-length record-initial segments were certified; none of the `14,304` nonzero segments was certified. Exceeding this sufficient radius does not prove that a particular directional segment crosses a kink, but it does mean that the saved-point Jacobian alone is not a valid finite-perturbation certificate. The endpoint secant is therefore the correct reported finite-pair quantity.

These sensitivities establish that the representative actor output is materially responsive to the previous-action slots on many sealed inputs. They do not establish closed-loop instability, a training cause, or that feedback removal is beneficial.

### 3.6 Full-grid missing data

`DATA-UNDECIDABLE` for checkpoint-level Jacobian/radius/secant distributions over all 24 policies. Minimal missing objects:

1. the other 23 actor `state_dict` exports; and
2. their actor input paths, or equivalent active-set/Jacobian exports.

The aggregate TV/RMS result JSONs cannot reconstruct those local differential objects.

---

## S4 — quasi-static RMS language audit

### 4.1 What the ratio says

Let `q=RMS(C)/RMS(A)=||C||_2/||A||_2`. A value near one says only that the two finite vectors have similar Euclidean norms. Let

\[
\rho=\frac{\langle A,C\rangle}{\lVert A\rVert_2\lVert C\rVert_2}.
\]

Then the exact normalized-error identity is

\[
\frac{\lVert A-C\rVert_2^2}{\lVert A\rVert_2^2}
=1+q^2-2q\rho.
\]

Without alignment `rho`, norm ratio does not determine closeness. Two equal-norm vectors can be identical, orthogonal, or opposite.

### 4.2 Constant anchor is not the temporal mean action

The diagnostic constant path is

\[
C_{n,t,i}=\pi_i(\bar o_{n,i},\bar p_{n,i}),
\]

repeated over time. Because the actor is nonlinear,

\[
\pi_i(\bar o,\bar p)\ne \overline{\pi_i(o_t,p_t)}
\]

in general. Thus the constant-anchor RMS cannot be interpreted as the RMS of the actor's temporal mean output.

For the actual raw action, define the true within-record temporal mean `bar A_{n,i}`. Orthogonality of the residual gives the exact ANOVA-style identity

\[
\operatorname{RMS}(A)^2
=
\operatorname{RMS}(\bar A\text{ repeated})^2
+
\operatorname{RMS}(A-\bar A)^2.
\]

This is the correct decomposition of level energy into temporal mean and within-record temporal variance. It is not a causal decomposition either, but it answers the temporal-static question exactly.

### 4.3 Representative audit

| Profile/channel | Constant/actual RMS | Normalized `l2` error | Temporal-mean squared-RMS share | Temporal-variance share |
|---|---:|---:|---:|---:|
| a / M | 0.9582 | 0.7733 | 0.5473 | 0.4527 |
| a / D | 1.0143 | 0.7658 | 0.5796 | 0.4204 |
| b / M | 0.9468 | 0.7265 | 0.6074 | 0.3926 |
| b / D | 0.9294 | 0.7803 | 0.5469 | 0.4531 |
| c / M | 1.0045 | 0.8001 | 0.5646 | 0.4354 |
| c / D | 1.0620 | 0.7407 | 0.6255 | 0.3745 |
| d / M | 0.9096 | 0.7979 | 0.4877 | 0.5123 |
| d / D | 0.9001 | 0.7154 | 0.5503 | 0.4497 |

Although every representative constant/actual RMS ratio lies between `0.9001` and `1.0620`, the constant path remains `0.7154`–`0.8001` actual-norm units away from the actual path. The true within-record temporal variance accounts for `37.45%`–`51.23%` of squared RMS. Near-unit norm retention therefore does not imply pathwise closeness or temporal-static dominance.

### 4.4 Complete supplied 24x4 grid

| Channel | Ratios | `>= 0.90` | Share | Median | Minimum | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| M | 96 | 54 | 56.25% | 0.9155 | 0.7015 | 1.1952 |
| D | 96 | 87 | 90.63% | 0.9871 | 0.8133 | 1.1523 |
| Combined | 192 | 141 | 73.44% | 0.9588 | 0.7015 | 1.1952 |

There are `57` ratios above `1.0` and `7` at or above `1.10`; none is at or below `0.50`. The M/D prevalence difference is substantial and must be reported rather than hidden behind the combined `141/192` count.

The full-grid true temporal mean/variance and alignment audit is `DATA-UNDECIDABLE` from the compact ratios. Minimal sufficient additions would be, for every record-agent-channel, temporal sums of actual raw action, sums of squares, and actual/constant-anchor inner products, or the complete action paths.

**Language decision:** “a quasi-static actor setpoint retains RMS” is acceptable only after changing it to an explicit threshold count about aggregate norm. “The quasi-static setpoint is the dominant RMS source” is unsupported.

---

## S5 — inference and claim boundary

| Conclusion | Classification | What is established | What is not established |
|---|---|---|---|
| Stored actor outputs for the representative checkpoint | Exact replay within declared numerical tolerance | The supplied checkpoint reproduces the sealed raw actions to `7.90e-07` max error. | Other checkpoints; bitwise identity across runtimes. |
| Production projector on sealed raw paths | Exact replay | Zero replay error; slew/between-ness properties; recursive TV theorem. | Plant benefit, safety, wear, or endpoint preservation. |
| Representative Jacobians, local radii, endpoint secants | Exact representative certificate | Local and finite-pair previous-slot sensitivity for 14,400 supplied inputs. | Uniform closed-loop gain, stability, or 24-policy generalization. |
| Fixed-previous TV grid | Finite-grid descriptive + frozen actor-path intervention | All `48/48` supplied channel-policy ratios are `<=0.205`; range `0.07098`–`0.20462`. | Random-population probability, training causality, or closed-loop controller effect. |
| Constant-anchor RMS grid | Finite-grid descriptive + frozen actor-path intervention | `141/192` ratios are `>=0.90`, with M `54/96` and D `87/96`. | Temporal-static source share, closeness, confidence interval, or causal attribution. |
| Recursive fixed-prev projected aggregate | Hash-bound promoted actor-path result | Manifest integrity, actual-path metrics, and reported ratios are internally verified. | Backend-invariant independent replay of the absent intervention action path; plant counterfactual. |
| Unique/additive mechanism shares | Unidentified | Only ordered signed contrasts and norm bounds are available. | Nonnegative or causal shares; symmetric Shapley allocation without `G`. |
| Modified-controller observations/endpoints | Unidentified | Nothing beyond frozen observations. | Stability, safety, registered guard passage, or endpoint preservation. |
| Training mechanism/retraining benefit | Unidentified | No intervention on the training process. | Why learning converged to these policies or whether retraining would improve them. |

No confidence interval, p-value, or superpopulation uncertainty statement is justified because no sampling design or population model is declared. Counts are exact properties of the enumerated diagnostic bank.

---

## S6 — paper-facing recommendation

### Current phrase 1

`previous-action feedback amplifies TV`

**Disposition:** `CURRENT-LANGUAGE-FAILS-AS-WRITTEN`.

**Replacement:**

> On the frozen observation paths, replacing the time-varying previous-executed-action actor input by its within-record mean reduced raw TV in all tested channel-policy cases.

This states the intervention, conditioning, finite scope, and measured direction. It does not claim training or plant causality.

### Current phrase 2

`a quasi-static actor setpoint retains RMS`

**Disposition:** `QUALIFY`.

**Replacement:**

> Constant-anchor raw RMS was at least 0.90 times actual raw RMS in 141 of 192 tested channel-profile cases (M: 54/96; D: 87/96); this is aggregate norm retention, not temporal-static source dominance.

### Smallest manuscript-safe insertion

Use `manuscript_patch.tex` unchanged. It contains one displayed equation and fewer than 150 words of paper prose. It deliberately omits the promoted recursive-intervention ratios because their exact stepwise intervention path is absent from the portable package and they are unnecessary for the defensible finite-record claim.

---

## Verification

From the returned folder, with the input archive extracted:

```bash
python verify_finite_record_certificate.py \
  --package-root /path/to/gpt_pro_r485_mechanism_math_20260901
```

Expected terminal status: `PASS` with overall disposition `CERTIFIED-BOUNDED-MECHANISM`.

To reconstruct the machine-readable result:

```bash
python verify_finite_record_certificate.py \
  --package-root /path/to/gpt_pro_r485_mechanism_math_20260901 \
  --write-result math_result.rebuilt.json
```

The verifier checks the package manifest, representative checkpoint identity, sealed trace lineage, actor replay, exact projector recursion, TV inequalities, decomposition bounds, representative RMS orthogonality, active-set Jacobians/radii, endpoint secants, and all fixed-grid counts.

## Source locators

- Projector implementation: `source/executed_action_sac.py:29-83`
- Actor implementation: `source/networks.py:28-80`
- Projection data: `posthoc/projection_tv_result.json#/candidate/profiles`
- Previous-input grid: `posthoc/feedback_grid_result.json#/policies`
- Constant-anchor grid: `posthoc/quasistatic_rms_grid_result.json#/rows`
- Recursive intervention: `posthoc/recursive_intervention_result.json#/profiles`
- Representative checkpoint: `checkpoint/an_cn_r0_seed501_final.pt#/members/*/actor`
- Representative traces: `traces/canary_eval_[a-d].json#/records/*/steps`
- Returned exact values and tolerances: `math_result.json`
